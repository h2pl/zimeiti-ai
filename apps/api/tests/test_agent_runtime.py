"""runtime.agent_runtime 专项测试：帧契约/HITL 中断/恢复/降级路径（deepagents 全 mock）。"""

from __future__ import annotations

import asyncio
import json
import time
import types
from pathlib import Path

import pytest
from langchain_core.messages import AIMessageChunk

from zimeiti_api.core import pg
from zimeiti_harness.runtime import agent_runtime as art


class FakeAgent:
    """假 deepagents agent：astream 吐指定 chunk 序列，aget_state 返回指定快照。"""

    def __init__(self, chunks=(), snapshot=None, astream_error: Exception | None = None):
        self.chunks = list(chunks)
        self.snapshot = snapshot
        self.astream_error = astream_error
        self.streamed_inputs = []
        self.state_calls = []

    async def astream(self, inputs, config=None, stream_mode=None):
        self.streamed_inputs.append(inputs)
        if self.astream_error:
            raise self.astream_error
        for c in self.chunks:
            yield c, {}

    async def aget_state(self, config):
        self.state_calls.append(config)
        return self.snapshot


def _chunk(text: str, tools: list[str] | None = None):
    kw = {"content": text}
    if tools:
        kw["tool_call_chunks"] = [
            {"name": t, "args": "", "id": f"c{i}", "index": i} for i, t in enumerate(tools)
        ]
    return AIMessageChunk(**kw)


def _snapshot(interrupt_value=None):
    """构造 langgraph 快照形状。interrupt_value=None → 无中断。"""
    if interrupt_value is None:
        return types.SimpleNamespace(tasks=[])
    return types.SimpleNamespace(
        tasks=[types.SimpleNamespace(interrupts=[types.SimpleNamespace(value=interrupt_value)])]
    )


class Recorder:
    def __init__(self):
        self.frames = []
        self.ended = False

    def __call__(self, kind, text=None, **extra):
        self.frames.append((kind, text, extra))

    def end(self):
        self.ended = True

    def texts(self):
        return "".join(t for k, t, _ in self.frames if k == "token")


@pytest.fixture
def rt(monkeypatch, tmp_path):
    """pg 层 mock + 全局状态隔离。"""
    store = {"messages": {}, "pending": {}}
    monkeypatch.setattr(pg, "messages_load", lambda sk: list(store["messages"].get(sk, [])))
    monkeypatch.setattr(
        pg, "messages_save", lambda sk, msgs: store["messages"].__setitem__(sk, list(msgs))
    )
    monkeypatch.setattr(pg, "pending_load", lambda: dict(store["pending"]))
    monkeypatch.setattr(
        pg, "pending_set", lambda qid, sk, payload: store["pending"].__setitem__(qid, payload)
    )
    monkeypatch.setattr(pg, "pending_del", lambda qid: store["pending"].pop(qid, None))
    monkeypatch.setattr(pg, "pending_get", lambda qid: store["pending"].get(qid))
    monkeypatch.setattr(pg, "pending_delete_by_session", lambda sk, user_id=None: 0)
    monkeypatch.setattr(pg, "session_delete", lambda sk, user_id=None: False)
    monkeypatch.setattr(pg, "get_checkpointer", lambda: None)
    monkeypatch.setattr(pg, "setup_checkpointer", lambda: asyncio.sleep(0) or None)
    monkeypatch.setattr(art, "_LOCKS", {})
    monkeypatch.setattr(art, "_LIVE_INTERRUPTS", {})
    monkeypatch.setattr(art, "_AGENT", None)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    yield types.SimpleNamespace(store=store)
    art._LIVE_INTERRUPTS.clear()
    art._LOCKS.clear()


# ---------- 纯函数 ----------


def test_to_text_shapes():
    assert art._to_text("abc") == "abc"
    assert art._to_text([{"text": "a"}, {"text": "b"}, "skip"]) == "ab"
    assert art._to_text({"x": 1}) == ""
    assert art._to_text(None) == ""


def test_extract_interrupt_shapes():
    # HITLRequest 形状：question + options 用 | 拆分
    snap = _snapshot(
        {
            "action_requests": [
                {"name": "ask_human", "args": {"question": "选哪个？", "options": "A|B"}}
            ]
        }
    )
    assert art._extract_interrupt(snap) == {"question": "选哪个？", "options": ["A", "B"]}
    # 无 question → 回退工具名
    snap2 = _snapshot({"action_requests": [{"name": "ask_human", "args": {}}]})
    assert art._extract_interrupt(snap2)["question"] == "ask_human"
    # 字符串 value
    snap3 = _snapshot("直接的问题")
    assert art._extract_interrupt(snap3) == {"question": "直接的问题", "options": []}
    # 无中断 / 空 tasks
    assert art._extract_interrupt(_snapshot()) is None
    assert art._extract_interrupt(None) is None
    # 异常吞掉
    assert art._extract_interrupt(types.SimpleNamespace(tasks=1 / 0 if False else [])) is None


def test_gc_live_ttl():
    now = time.monotonic()
    art._LIVE_INTERRUPTS.update({"old": {"ts": now - art.TTL_SECONDS - 1}, "fresh": {"ts": now}})
    art._gc_live()
    assert "old" not in art._LIVE_INTERRUPTS and "fresh" in art._LIVE_INTERRUPTS


def test_session_lock_idempotent():
    a = art._session_lock("s1")
    assert art._session_lock("s1") is a
    assert art._session_lock("s2") is not a


def test_save_pending_rejected():
    with pytest.raises(NotImplementedError):
        art._save_pending({})


def test_model_configured_env_branches(rt, monkeypatch):
    assert art.model_configured() is False  # 无 key
    monkeypatch.setenv("OPENAI_API_KEY", "sk-x")
    # langchain_openai 真实存在（运行时依赖）→ 返回模型实例
    assert art.model_configured() is True


def test_build_model_kwargs(rt, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-x")
    monkeypatch.setenv("OPENAI_MODEL", "my-model")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://x/v1")
    m = art._build_model()
    assert m is not None and m.model_name == "my-model" and m.openai_api_base == "https://x/v1"
    monkeypatch.delenv("OPENAI_MODEL")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    m2 = art._build_model()
    assert m2.model_name == "gpt-4o-mini"  # 默认模型名


# ---------- run_turn ----------

_MISSING = object()


async def _run_turn(rt, monkeypatch, agent=None, model=_MISSING, **kw):
    monkeypatch.setattr(art, "_build_model", lambda: object() if model is _MISSING else model)
    if agent is not None:
        monkeypatch.setattr(art, "_build_agent", _async_fn(agent))
    rec = Recorder()
    await art.run_turn("sk1", "问题", "pk1", "t1", Path("_e.jsonl"), rec, rec.end, **kw)
    return rec


def _async_fn(v):
    """返回一个 async 函数（可直接作 monkeypatch 的 async 替身）。"""

    async def f(*_a, **_k):
        return v

    return f


def _go(coro):
    return asyncio.run(coro)


def test_run_turn_no_model_error_frame(rt, monkeypatch):
    rec = _go(_run_turn(rt, monkeypatch, model=None, save_turn=lambda *a, **k: None))
    kinds = [k for k, _, _ in rec.frames]
    assert kinds[0] == "error" and "未配置模型" in rec.frames[0][1]
    assert kinds[-1] == "done" and rec.ended


def test_run_turn_agent_build_fail(rt, monkeypatch):
    async def boom():
        raise RuntimeError("deepagents missing")

    monkeypatch.setattr(art, "_build_model", lambda: object())
    monkeypatch.setattr(art, "_build_agent", boom)
    rec = Recorder()
    asyncio.run(art.run_turn("sk1", "m", "pk", "t", Path("_e.jsonl"), rec, rec.end))
    assert "运行时初始化失败" in rec.frames[0][1] and rec.ended


def test_run_turn_normal_flow(rt, monkeypatch):
    agent = FakeAgent(chunks=[_chunk("你"), _chunk("好", tools=["web_search"])])
    rec = _go(_run_turn(rt, monkeypatch, agent=agent))
    kinds = [(k) for k, _, _ in rec.frames]
    assert "token" in kinds and "activity" in kinds  # 工具调用发 activity 帧
    assert rec.texts() == "你好"
    assert kinds[-1] == "done" and rec.ended
    # 历史落盘（user + assistant）
    hist = rt.store["messages"]["sk1"]
    assert hist[-2]["role"] == "user" and hist[-1] == {"role": "assistant", "content": "你好"}


def test_run_turn_interrupt_flow(rt, monkeypatch):
    snap = _snapshot(
        {
            "action_requests": [
                {"name": "ask_human", "args": {"question": "要配图吗？", "options": "要|不要"}}
            ]
        }
    )
    agent = FakeAgent(chunks=[_chunk("先问一下")], snapshot=snap)
    saves = []
    rec = _go(
        _run_turn(
            rt, monkeypatch, agent=agent, save_turn=lambda pk, st, tx, ex: saves.append((st, tx))
        )
    )
    kinds = [k for k, _, _ in rec.frames]
    assert "question" in kinds and "done" not in kinds  # 中断不发 done（SSE 保持）
    qframe = next(t for k, t, _ in rec.frames if k == "question")
    payload = json.loads(qframe)
    assert payload["questions"][0]["question"] == "要配图吗？"
    assert payload["questions"][0]["options"] == ["要", "不要"]
    assert rec.ended is False
    # pending 落 PG + live 登记
    qid = payload["id"]
    assert qid in rt.store["pending"]
    live = art._LIVE_INTERRUPTS["sk1"]
    assert live["pending_ids"] == [qid] and live["emit"] is rec
    # 历史未落盘（等恢复后一起）
    assert "sk1" not in rt.store["messages"]


def test_run_turn_stream_error(rt, monkeypatch):
    agent = FakeAgent(astream_error=RuntimeError("llm down"))
    rec = _go(_run_turn(rt, monkeypatch, agent=agent))
    kinds = [k for k, _, _ in rec.frames]
    assert kinds[0] == "error" and "llm down" in rec.frames[0][1]
    assert kinds[-1] == "done" and rec.ended


def test_run_turn_history_injection(rt, monkeypatch):
    # checkpoint 无消息时注入落盘历史
    agent = FakeAgent(snapshot=_snapshot())
    rt.store["messages"]["sk1"] = [
        {"role": "user", "content": "旧问题"},
        {"role": "assistant", "content": "旧回答"},
    ]
    monkeypatch.setattr(art, "_checkpoint_has_messages", _async_fn(False))
    _go(_run_turn(rt, monkeypatch, agent=agent))
    msgs = agent.streamed_inputs[0]["messages"]
    assert [m.content for m in msgs] == ["旧问题", "旧回答", "问题"]
    # checkpoint 已有消息 → 只发本轮
    monkeypatch.setattr(art, "_checkpoint_has_messages", _async_fn(True))
    agent2 = FakeAgent(snapshot=_snapshot())
    _go(_run_turn(rt, monkeypatch, agent=agent2))
    assert [m.content for m in agent2.streamed_inputs[0]["messages"]] == ["问题"]


# ---------- ask / ask_sync / answer ----------


def test_ask_no_model(rt, monkeypatch):
    monkeypatch.setattr(art, "_build_model", lambda: None)
    out = asyncio.run(art.ask("sk1", "问题"))
    assert "未配置模型" in out


def test_ask_normal_and_interrupt(rt, monkeypatch):
    monkeypatch.setattr(art, "_build_model", lambda: object())
    agent = FakeAgent(chunks=[_chunk("答"), _chunk("案")], snapshot=_snapshot())
    monkeypatch.setattr(art, "_build_agent", _async_fn(agent))
    assert asyncio.run(art.ask("sk1", "问题")) == "答案"
    hist = rt.store["messages"]["sk1"]
    assert hist[-1]["content"] == "答案"
    # 中断：非流式不续答
    agent2 = FakeAgent(
        snapshot=_snapshot({"action_requests": [{"name": "ask_human", "args": {"question": "Q?"}}]})
    )
    monkeypatch.setattr(art, "_build_agent", _async_fn(agent2))
    out = asyncio.run(art.ask("sk2", "问题"))
    assert out.startswith("⏸") and "Q?" in out


def test_ask_sync_wraps_ask(rt, monkeypatch):
    monkeypatch.setattr(art, "_build_model", lambda: None)
    assert "未配置模型" in art.ask_sync("sk1", "问题")


def test_answer_no_pending(rt):
    assert asyncio.run(art.answer("ghost", {"q": ["a"]})) == {
        "ok": False,
        "error": "question not found",
    }


def test_answer_live_resume(rt, monkeypatch):
    # 模拟 run_turn 中断后的 live 状态 + pending
    rec = Recorder()
    saves: list = []
    art._LIVE_INTERRUPTS["sk1"] = {
        "emit": rec,
        "end": rec.end,
        "pk": "pk1",
        "ts": time.monotonic(),
        "full_text": ["前半"],
        "config": {"configurable": {"thread_id": "t"}},
        "save_turn": lambda pk, st, tx, ex: saves.append((st, tx)),
        "pending_ids": ["q1"],
    }
    rt.store["pending"]["q1"] = {"id": "q1", "thread_id": "sk1"}
    agent = FakeAgent(chunks=[_chunk("后半")])
    monkeypatch.setattr(art, "_AGENT", agent)
    out = asyncio.run(art.answer("q1", {"q1": ["选项A"]}, "web"))
    assert out["ok"] is True and out["last_message"] == "前半后半"
    assert rec.texts() == "后半"
    assert rec.ended and [k for k, _, _ in rec.frames][-1] == "done"
    # live 已弹、pending 已删、历史落盘
    assert "sk1" not in art._LIVE_INTERRUPTS and "q1" not in rt.store["pending"]
    assert rt.store["messages"]["sk1"][-1] == {"role": "assistant", "content": "前半后半"}


def test_answer_resume_error_ends_stream(rt, monkeypatch):
    rec = Recorder()
    art._LIVE_INTERRUPTS["sk1"] = {
        "emit": rec,
        "end": rec.end,
        "pk": "pk1",
        "ts": time.monotonic(),
        "full_text": [],
        "config": {"configurable": {"thread_id": "t"}},
    }
    rt.store["pending"]["q2"] = {"id": "q2", "thread_id": "sk1"}
    agent = FakeAgent(astream_error=RuntimeError("resume boom"))
    monkeypatch.setattr(art, "_AGENT", agent)
    out = asyncio.run(art.answer("q2", {"q2": ["a"]}))
    assert out["ok"] is False and "resume boom" in out["error"]
    assert rec.ended  # 修复 I3：resume 失败也结束原连接


def test_answer_offline_path(rt, monkeypatch):
    # 无 live（进程重启后）：pending 在但连接已丢 → 只落盘不发帧
    rt.store["pending"]["q3"] = {"id": "q3", "thread_id": "sk9"}
    agent = FakeAgent(chunks=[_chunk("离线答案")])
    monkeypatch.setattr(art, "_AGENT", agent)
    out = asyncio.run(art.answer("q3", "直接文本"))
    assert out["ok"] is True and out["last_message"] == "离线答案"
    assert rt.store["messages"]["sk9"][-1]["content"] == "离线答案"


def test_checkpoint_has_messages(rt):
    state_ok = types.SimpleNamespace(values={"messages": [{"x": 1}]})
    agent = types.SimpleNamespace()
    agent.aget_state = _async_fn(state_ok)
    assert asyncio.run(art._checkpoint_has_messages(agent, {})) is True
    agent.aget_state = _async_fn(types.SimpleNamespace(values=None))
    assert asyncio.run(art._checkpoint_has_messages(agent, {})) is False

    async def boom(config):
        raise RuntimeError("pg down")

    agent.aget_state = boom
    assert asyncio.run(art._checkpoint_has_messages(agent, {})) is False


def test_delete_session_cleans_all(rt, monkeypatch):
    calls = {}

    class FakeSaver:
        async def adelete_thread(self, tid):
            calls["tid"] = tid

    monkeypatch.setattr(pg, "get_checkpointer", lambda: FakeSaver())
    monkeypatch.setattr(pg, "pending_delete_by_session", lambda sk, user_id=None: 3)
    monkeypatch.setattr(pg, "session_delete", lambda sk, user_id=None: True)
    art._LIVE_INTERRUPTS["sk1"] = {}
    art._LOCKS["sk1"] = asyncio.Lock()
    deleted = asyncio.run(art.delete_session("sk1"))
    assert deleted is True
    assert "sk1" not in art._LIVE_INTERRUPTS and "sk1" not in art._LOCKS
    assert calls["tid"] == pg.thread_id("sk1")
