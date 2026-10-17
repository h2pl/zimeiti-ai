"""runtime 域测试：chat 路由契约 / 附件清单安全 / SSE 流 / 会话管理（agent_runtime 全 mock）。"""

from __future__ import annotations

import json
import uuid

import pytest
from fastapi import HTTPException

from zimeiti_api import chat_router as chat_mod
from zimeiti_api.core import paths as paths_mod
from zimeiti_harness.runtime import agent_runtime as agent_rt


@pytest.fixture
def rt_env(tmp_path, monkeypatch):
    sessions = tmp_path / "_sessions"
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    monkeypatch.setattr(chat_mod, "SESSIONS_DIR", sessions)
    monkeypatch.setattr(paths_mod, "OUTPUTS_DIR", outputs)
    yield types.SimpleNamespace(sessions=sessions, outputs=outputs)


import types  # noqa: E402

# ---------- 附件清单安全 ----------


def test_attachment_context_branches(rt_env):
    req = chat_mod.ChatRequest(message="hi")
    assert chat_mod._attachment_context(req) == ""
    req2 = chat_mod.ChatRequest(
        message="hi",
        attachments=[chat_mod.AttachmentRef(id="x", name="a", path="_inbox/s/b/c.txt")],
    )
    with pytest.raises(HTTPException) as ei:
        chat_mod._attachment_context(req2)
    assert ei.value.status_code == 400  # 无 sessionId
    for bad in ["../x/y/z.txt", "C:/abs/path.txt", "_inbox/a/b.txt"]:  # 穿越/绝对/段数不对
        req3 = chat_mod.ChatRequest(
            message="hi",
            sessionId="s1",
            attachments=[chat_mod.AttachmentRef(id="x", name="a", path=bad)],
        )
        with pytest.raises(HTTPException) as ei2:
            chat_mod._attachment_context(req3)
        assert ei2.value.status_code == 400


def test_attachment_context_full(rt_env):
    scope = chat_mod._attachment_scope("sess-A")
    rel = f"_inbox/{scope}/batch1/a.txt"
    f = rt_env.outputs / rel
    f.parent.mkdir(parents=True)
    f.write_text("data", encoding="utf-8")
    aid = chat_mod._attachment_id(scope, rel)
    req = chat_mod.ChatRequest(
        message="hi",
        sessionId="sess-A",
        attachments=[chat_mod.AttachmentRef(id=aid, name="a.txt", path=rel)],
    )
    ctx = chat_mod._attachment_context(req)
    assert "系统附件清单" in ctx and f"outputs/{rel}" in ctx
    # scope 不匹配 → 403
    req2 = chat_mod.ChatRequest(
        message="hi",
        sessionId="sess-OTHER",
        attachments=[chat_mod.AttachmentRef(id=aid, name="a.txt", path=rel)],
    )
    with pytest.raises(HTTPException) as ei:
        chat_mod._attachment_context(req2)
    assert ei.value.status_code == 403
    # id 校验失败 → 403
    req3 = chat_mod.ChatRequest(
        message="hi",
        sessionId="sess-A",
        attachments=[chat_mod.AttachmentRef(id="bad", name="a.txt", path=rel)],
    )
    with pytest.raises(HTTPException) as ei3:
        chat_mod._attachment_context(req3)
    assert ei3.value.status_code == 403
    # 文件缺失 → 404
    f.unlink()
    with pytest.raises(HTTPException) as ei4:
        chat_mod._attachment_context(req)
    assert ei4.value.status_code == 404


def test_chat_message_rules(rt_env):
    with pytest.raises(HTTPException):
        chat_mod._chat_message(chat_mod.ChatRequest(message="   "))
    msg = chat_mod._chat_message(chat_mod.ChatRequest(message="你好"))
    assert msg.startswith("你好") and msg.endswith("别随手自曝「由 AI 生成/某工具做的」。")
    # 画像前缀注入走 persona_core（已在 content 域测过）；此处画像不存在 → 无前缀
    assert "我当前使用的画像" not in msg


# ---------- 落盘与事件 ----------


def test_turn_and_job_file_names(rt_env):
    f = chat_mod._turn_file("web:abc/def")
    assert "/" not in f.name and "\\" not in f.name
    j = chat_mod._job_event_file("tid/../x")
    assert j.parent.name == "jobs"


def test_read_job_events_and_raw(rt_env):
    assert chat_mod._read_job_events("ghost") == []
    p = chat_mod._job_event_file("t1")
    p.parent.mkdir(parents=True)
    p.write_text(
        json.dumps({"id": 1, "event": "token", "data": "a"})
        + "\n"
        + json.dumps({"id": 2, "event": "done", "data": None})
        + "\n",
        encoding="utf-8",
    )
    evs = chat_mod._read_job_events("t1", after=0)
    assert [e["id"] for e in evs] == [1, 2]
    assert [e["id"] for e in chat_mod._read_job_events("t1", after=1)] == [2]
    # 任一坏行 → 整批丢弃（try 包裹整个循环的真实行为）
    p.write_text("garbage\n", encoding="utf-8")
    assert chat_mod._read_job_events("t1") == []
    # raw 事件解析
    assert chat_mod._raw_event_for_run("", None) is None
    assert chat_mod._raw_event_for_run("{bad", None) is None
    assert chat_mod._raw_event_for_run("[1,2]", None) is None
    ev = chat_mod._raw_event_for_run(json.dumps({"runId": "r1", "x": 1}), None)
    assert ev["runId"] == "r1"  # 未锁定 → 接受
    assert chat_mod._raw_event_for_run(json.dumps({"runId": "r2"}), "r1") is None  # 他 run
    assert chat_mod._raw_event_for_run(json.dumps({"x": 1}), "r1") is not None  # 无 runId 不拒


def test_save_turn_and_chat_last(rt_env, client):
    sk = f"web:s-{uuid.uuid4().hex[:6]}"
    assert client.get(f"/api/chat/last/{sk.split(':', 1)[1]}").json() == {
        "status": "none",
        "text": "",
    }
    chat_mod._save_turn(sk, "done", "完整回答", {"turn_id": "t-9"})
    body = client.get(f"/api/chat/last/{sk.split(':', 1)[1]}").json()
    assert body["status"] == "done" and body["text"] == "完整回答" and body["turn_id"] == "t-9"
    # turn_id 不匹配 → stale
    stale = client.get(f"/api/chat/last/{sk.split(':', 1)[1]}", params={"turn_id": "old"}).json()
    assert stale["status"] == "stale"
    # 落盘损坏 → none
    f = chat_mod._turn_file(sk)
    f.write_text("{broken", encoding="utf-8")
    assert client.get(f"/api/chat/last/{sk.split(':', 1)[1]}").json()["status"] == "none"


def test_chat_job_stream_replay(rt_env, client):
    p = chat_mod._job_event_file("t-replay")
    p.parent.mkdir(parents=True)
    p.write_text(
        json.dumps({"id": 1, "event": "token", "data": "片段"})
        + "\n"
        + json.dumps({"id": 2, "event": "done", "data": {"sessionKey": "s"}})
        + "\n",
        encoding="utf-8",
    )
    assert client.get("/api/chat/jobs/ghost/stream").status_code == 404
    with client.stream("GET", "/api/chat/jobs/t-replay/stream", params={"after": 0}) as r:
        lines = [ln for ln in r.iter_lines() if ln.strip()]
    text = "\n".join(lines)
    assert "token" in text and "done" in text and "片段" in text
    # after=1 只回放 done
    with client.stream("GET", "/api/chat/jobs/t-replay/stream", params={"after": 1}) as r:
        lines2 = [ln for ln in r.iter_lines() if ln.strip()]
    text2 = "\n".join(lines2)
    assert "片段" not in text2 and "done" in text2


# ---------- 对话路由（agent_runtime 全 mock） ----------


def test_chat_non_stream(rt_env, monkeypatch, client):
    seen = {}

    async def fake_ask(sk, message):
        seen.update(sk=sk, message=message)
        return "回复内容"

    monkeypatch.setattr(agent_rt, "ask", fake_ask)
    r = client.post("/api/chat", json={"message": "问题", "sessionId": "sess-x", "persona": "eve"})
    assert r.json() == {"response": "回复内容"}
    assert seen["sk"] == "sess-x"
    assert "问题" in seen["message"]
    assert "先查技能库" in seen["message"]  # 每轮提醒（画像不存在故无前缀）


def test_chat_empty_message(rt_env, client):
    assert client.post("/api/chat", json={"message": "  "}).status_code == 400


def test_skill_route(rt_env, monkeypatch, client, tmp_path):
    assert client.post("/api/skill", json={"skill": "ghost-skill", "input": "x"}).status_code == 404
    # 造一个假 skill 目录
    sd = tmp_path / "skills" / "builtin" / "skill-demo"
    sd.mkdir(parents=True)
    (sd / "SKILL.md").write_text("---\nlayer: direct\n---\n正文", encoding="utf-8")
    import zimeiti_api.content.skills as skills_mod

    monkeypatch.setattr(skills_mod, "SKILLS_DIR", tmp_path / "skills")

    async def fake_ask(sk, message):
        assert "/skill-demo" in message
        return "skill done"

    monkeypatch.setattr(agent_rt, "ask", fake_ask)
    r = client.post("/api/skill", json={"skill": "demo", "input": "做图", "sessionId": "sess-s"})
    assert r.json() == {"response": "skill done"}


def test_question_routes(rt_env, monkeypatch, client):
    monkeypatch.setattr(agent_rt, "pending_status", lambda ids: {i: "pending" for i in ids})
    r = client.post("/api/chat/question/status", json={"questionIds": ["q1", "q2"]})
    assert r.json() == {"ok": True, "questions": {"q1": "pending", "q2": "pending"}}

    async def fake_answer(qid, answers, resolved_by):
        return {"answered": qid}

    monkeypatch.setattr(agent_rt, "answer", fake_answer)
    r2 = client.post(
        "/api/chat/question/answer", json={"questionId": "q1", "answers": {"q1": ["a"]}}
    )
    assert r2.json() == {"answered": "q1"}


def test_status_route(rt_env, monkeypatch, client):
    monkeypatch.setattr(agent_rt, "model_configured", lambda: True)
    r = client.get("/api/status").json()
    assert (
        r["gateway"] is True and isinstance(r["skills"], list) and isinstance(r["personas"], list)
    )


def test_delete_session(rt_env, monkeypatch, client):
    sk = f"web:del-{uuid.uuid4().hex[:6]}"
    chat_mod._save_turn(sk, "done", "x", {"turn_id": "t"})
    called = {}

    async def fake_delete(key):
        called["key"] = key
        return True

    monkeypatch.setattr(agent_rt, "delete_session", fake_delete)
    r = client.request("DELETE", f"/api/session/{sk}").json()
    assert r["deleted"] is True and called["key"] == sk
    assert not chat_mod._turn_file(sk).is_file()  # 轮次结果一并清理


def test_chat_stream_full_flow(rt_env, monkeypatch, client):
    """SSE 全流程：fake run_turn 发 token/done → 前向转发 → 落盘 → /api/chat/last 取回。"""

    def fake_run_turn(
        sk, message, pk, turn_id, event_path, to_client, on_client_done, save_turn=None
    ):
        to_client("activity", "唤醒")
        to_client("token", "你")
        to_client("token", "好")
        save_turn(pk, "done", "你好", {"turn_id": turn_id})
        to_client("done", None, sessionKey=sk)
        on_client_done()

    monkeypatch.setattr(agent_rt, "run_turn", fake_run_turn)
    events = []
    with client.stream(
        "POST",
        "/api/chat/stream",
        json={"message": "打个招呼", "sessionId": "sess-stream", "turnId": "tid-1"},
    ) as r:
        for line in r.iter_lines():
            if line.strip():
                events.append(line)
    text = "\n".join(events)
    assert "event: activity" in text and "唤醒" in text
    assert "event: token" in text and 'data: "你"' in text and 'data: "好"' in text
    assert "event: done" in text and "sess-stream" in text
    # 落盘可取回
    last = client.get("/api/chat/last/sess-stream", params={"turn_id": "tid-1"}).json()
    assert last["status"] == "done" and last["text"] == "你好"
    # 事件文件留档（断线重放依据）
    evf = chat_mod._job_event_file("tid-1")
    assert evf.is_file() and "token" in evf.read_text(encoding="utf-8")

    assert "sess-stream" not in chat_mod._RUNNING_CHAT  # 结束后清理


def test_chat_stream_agent_crash(rt_env, monkeypatch, client):
    """supervisor 崩溃：forward 解锁收尾，不挂死。"""

    async def boom(*a, **kw):
        raise RuntimeError("agent exploded")

    monkeypatch.setattr(agent_rt, "run_turn", boom)
    events = []
    with client.stream(
        "POST",
        "/api/chat/stream",
        json={"message": "x", "sessionId": "sess-crash", "turnId": "tid-c"},
    ) as r:
        for line in r.iter_lines():
            if line.strip():
                events.append(line)
    assert any("activity" in ln for ln in events)  # 至少收到「已收到」帧后正常收尾


def test_chat_stop(rt_env, monkeypatch, client):
    # 无在跑任务
    assert client.post("/api/chat/stop", json={"sessionId": "nobody"}).json() == {"stopped": False}
    assert client.post("/api/chat/stop", json={"sessionId": "  "}).json() == {"stopped": False}
    # 有在跑任务：先起一个阻塞的 stream，再 stop

    async def blocking_run(*a, **kw):
        ev = asyncio.Event()
        await ev.wait()  # 永久挂起直到被取消

    import asyncio

    monkeypatch.setattr(agent_rt, "run_turn", blocking_run)
    import threading

    got = {}

    def consume():
        with client.stream(
            "POST",
            "/api/chat/stream",
            json={"message": "x", "sessionId": "sess-stop", "turnId": "tid-s"},
        ) as r:
            for line in r.iter_lines():
                if line.strip() and "已收到" in line:
                    got["ready"] = True
                    break

    th = threading.Thread(target=consume, daemon=True)
    th.start()
    for _ in range(100):
        if "sess-stop" in chat_mod._RUNNING_CHAT and got.get("ready"):
            break
        time.sleep(0.05)
    r = client.post("/api/chat/stop", json={"sessionId": "sess-stop"})
    assert r.json()["stopped"] is True
    th.join(timeout=5)
    # supervisor 收尾落盘 stopped
    last = client.get("/api/chat/last/sess-stop", params={"turn_id": "tid-s"}).json()
    assert last["status"] == "stopped"
    assert "sess-stop" not in chat_mod._RUNNING_CHAT


import time  # noqa: E402
