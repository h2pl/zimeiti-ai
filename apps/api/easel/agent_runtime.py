"""deepagents 运行时（phase1-deepagents-runtime）。

用 deepagents（LangGraph）替代 OpenClaw 网关承载对话链路：
- 会话历史与 HITL pending 存 PostgreSQL（easel/pg.py，pg-data-layer 变更）；
  checkpoint 经 AsyncPostgresSaver 持久化，重启后从 PG 恢复（thread_id 带
  租户命名空间，本地版为 '<local>:<session_key>'）
- `create_deep_agent` 构建 agent，`ask_human` 工具触发 HITL 中断（问题卡内联，
  SSE 连接保持打开，答案经 Command(resume) 注入后同连接续流）
- 流式输出按 Easel 前端 SSE 契约发帧：token / activity / question / error / done
- 模型经环境变量配置：ZIMEITI_MODEL / OPENAI_API_KEY / OPENAI_BASE_URL；
  未配置时返回明确错误帧（服务本身正常）

评审修复记录（2026-10-13 独立评审 C1-C4/I1-I5/W1-W6）：
- resume 决策格式 `{"type":"respond","message":<str>}`（RespondDecision）
- interrupt 载荷从 `action_requests[0].args` 取 question/options；options 按「|」拆分
- question 帧载荷形状对齐前端 ChatQuestion：{"id","questions":[{questionId,question,options}]}
- answer() 把前端 `{questionId:[label]}` 格式化为「问题 → 选项」文本注入
- token 流按 AIMessageChunk 过滤（排除 ToolMessage/合成消息）
- checkpoint 已有消息时不重复注入落盘历史（防上下文成倍膨胀）
- resume 失败补 done 帧 + end()（原连接不再悬挂）
- pending_status 返回 {qid:{"status":...}}（对齐前端）
- session 级 asyncio.Lock 串行化；_LIVE_INTERRUPTS/pending 条目 30 分钟 TTL 惰性清理
- 死代码清理（_LOOP/_ensure_loop/threading/无效 info 查询）；删除与 to_client 双写的 _append_event
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from langchain_core.messages import AIMessageChunk
from pathlib import Path
from typing import Any, Callable

from . import pg

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
TTL_SECONDS = 30 * 60

SYSTEM_PROMPT = (
    "你是 Zimeiti AI 自媒体运营 agent。"
    "与用户协作完成选题、创作与发布；需要用户决策时用 ask_human 提问（可给选项）。"
    "\n\n"
    "【语言硬约束】无论用户使用什么语言提问，你的全部回复必须使用简体中文；"
    "仅以下内容保留原文：专有名词、平台名、工具/命令/代码、文件路径、以及用户"
    "明确要求保留原文的内容。不要用英文回答中文问题。"
)


# ---------- 会话历史 / HITL pending（PostgreSQL，见 easel/pg.py） ----------

def _load_messages(session_key: str) -> list[dict]:
    return pg.messages_load(session_key)


def _save_messages(session_key: str, messages: list[dict]) -> None:
    pg.messages_save(session_key, messages)


def _load_pending() -> dict:
    return pg.pending_load()


def _save_pending(data: dict) -> None:
    raise NotImplementedError("pending 已改 PG 粒度操作，请用 pg.pending_set/pending_del")


async def delete_session(session_key: str, user_id: str = pg.DEFAULT_USER) -> bool:
    """删除会话的全部状态：PG 消息/会话行 + PG checkpoint + HITL pending + 活跃中断登记。

    供 web 端 DELETE /api/session/{key} 调用。四类状态都删净，同 key 再聊
    才不会「复活」旧上下文。返回是否有任何状态被删除。
    """
    deleted = pg.session_delete(session_key, user_id=user_id)
    deleted = bool(pg.pending_delete_by_session(session_key, user_id=user_id)) or deleted
    try:
        saver = pg.get_checkpointer()
        if saver is not None:
            await saver.adelete_thread(pg.thread_id(session_key, user_id))
            deleted = True
    except Exception:  # noqa: BLE001   checkpoint 清理失败不阻断消息删除
        pass
    _LIVE_INTERRUPTS.pop(session_key, None)
    _LOCKS.pop(session_key, None)
    return deleted


# ---------- HITL pending TTL 常量（与 pg.PENDING_TTL_SECONDS 同源） ----------

_LOCKS: dict[str, asyncio.Lock] = {}


def _session_lock(session_key: str) -> asyncio.Lock:
    if session_key not in _LOCKS:
        _LOCKS[session_key] = asyncio.Lock()
    return _LOCKS[session_key]


def get_pending(question_id: str) -> dict | None:
    return _load_pending().get(question_id)


def pending_status(question_ids: list[str]) -> dict[str, dict]:
    pend = _load_pending()
    return {qid: {"status": "pending" if qid in pend else "not_found"} for qid in question_ids}


# ---------- 模型与 agent ----------

def _build_model():
    from langchain_openai import ChatOpenAI

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    kwargs: dict[str, Any] = {
        "model": os.environ.get("OPENAI_MODEL") or os.environ.get("ZIMEITI_MODEL", "gpt-4o-mini"),
        "api_key": api_key,
        "streaming": True,
    }
    base_url = os.environ.get("OPENAI_BASE_URL")
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOpenAI(**kwargs)


_AGENT = None


async def _build_agent():
    """构建 deepagents agent（进程内缓存；ask_human 触发 HITL 中断）。

    checkpointer 用 PG（AsyncPostgresSaver，见 easel/pg.py）：异步图必须配
    异步 saver；实例由 lifespan 经 pg.setup_checkpointer() 预先建好，此处取
    缓存；若未初始化（如测试直连）则当场建。
    """
    global _AGENT
    if _AGENT is not None:
        return _AGENT
    from deepagents import create_deep_agent
    from langchain_core.tools import tool

    @tool
    def ask_human(question: str, options: str = "") -> str:
        """向用户提问并等待回答。question 为问题文本；options 用「|」分隔候选答案（可留空）。"""
        return "已提交问题，等待人工回答。"

    checkpointer = await pg.setup_checkpointer()
    _AGENT = create_deep_agent(
        model=_build_model(),
        tools=[ask_human],
        system_prompt=SYSTEM_PROMPT,
        interrupt_on={"ask_human": True},
        checkpointer=checkpointer,
    )
    return _AGENT


# ---------- 中断等待中的会话（带 TTL 惰性清理）----------

_LIVE_INTERRUPTS: dict[str, dict] = {}


def _gc_live() -> None:
    now = time.monotonic()
    stale = [k for k, v in _LIVE_INTERRUPTS.items() if now - v.get("ts", now) > TTL_SECONDS]
    for k in stale:
        _LIVE_INTERRUPTS.pop(k, None)


def _extract_interrupt(snapshot) -> dict | None:
    """从 langgraph 快照提取 HITL 中断载荷。

    deepagents 0.7 的中断 value 形如 HITLRequest：
    {"action_requests": [{"name", "args", "description"}], "review_configs": [...]}
    question/options 在 action_requests[0].args 里（ask_human 工具入参）。
    """
    try:
        for t in snapshot.tasks or []:
            for it in getattr(t, "interrupts", None) or []:
                value = getattr(it, "value", None)
                if isinstance(value, dict):
                    reqs = value.get("action_requests") or []
                    if reqs:
                        args = reqs[0].get("args") or {}
                        q = args.get("question") or reqs[0].get("name") or "agent 需要你的输入"
                        opts = args.get("options") or ""
                        if isinstance(opts, str):
                            opts = [o for o in opts.split("|") if o] if opts else []
                        return {"question": str(q), "options": [str(o) for o in opts]}
                if isinstance(value, str):
                    return {"question": value, "options": []}
    except Exception:
        return None
    return None


def _to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(p.get("text", "") for p in content if isinstance(p, dict))
    return ""


async def _checkpoint_has_messages(agent, config) -> bool:
    """checkpoint 是否已有消息（决定是否注入落盘历史，防重复膨胀）。"""
    try:
        state = await agent.aget_state(config)
        msgs = (state.values or {}).get("messages") if isinstance(state.values, dict) else None
        return bool(msgs)
    except Exception:
        return False


async def run_turn(session_key: str, message: str, pk: str, turn_id: str,
                   event_path: Path, emit: Callable, end: Callable,
                   save_turn: Callable | None = None) -> None:
    """跑一轮 deepagents 对话，按 Easel SSE 契约发帧；结束负责落盘与 done 帧。"""
    async with _session_lock(session_key):
        _gc_live()
        model = _build_model()
        if model is None:
            emit("error", "❌ 未配置模型：请设置 OPENAI_API_KEY（可选 OPENAI_BASE_URL / ZIMEITI_MODEL）")
            if save_turn:
                save_turn(pk, "error", "", {"turn_id": turn_id})
            emit("done", sessionKey=session_key)
            end()
            return
        try:
            agent = await _build_agent()
        except Exception as e:  # noqa: BLE001
            emit("error", f"❌ 运行时初始化失败：{str(e)[:180]}")
            emit("done", sessionKey=session_key)
            end()
            return

        config = {"configurable": {"thread_id": pg.thread_id(session_key)}}
        from langchain_core.messages import AIMessage, HumanMessage

        lc_messages: list = []
        if not await _checkpoint_has_messages(agent, config):
            # 仅 checkpoint 为空（新线程 / 重启后首轮）才注入落盘历史，
            # 否则 langgraph 追加语义会让上下文成倍膨胀。
            for m in _load_messages(session_key):
                if m.get("content"):
                    lc_messages.append(
                        HumanMessage(content=m["content"]) if m["role"] == "user"
                        else AIMessage(content=m["content"])
                    )
        lc_messages.append(HumanMessage(content=message))

        full_text: list[str] = []
        tool_names: set[str] = set()
        interrupted: dict | None = None
        try:
            async for chunk, _meta in agent.astream(
                {"messages": lc_messages}, config=config, stream_mode="messages"
            ):
                if not isinstance(chunk, AIMessageChunk):
                    continue  # 排除 ToolMessage / 状态回放，防止把用户回答当助手输出
                text = _to_text(getattr(chunk, "content", None))
                if text:
                    full_text.append(text)
                    emit("token", text)
                for tc in getattr(chunk, "tool_call_chunks", None) or []:
                    name = tc.get("name")
                    if name and name not in tool_names:
                        tool_names.add(name)
                        emit("activity", f"🔧 {name}…")
            snapshot = await agent.aget_state(config)
            interrupted = _extract_interrupt(snapshot)
        except Exception as e:  # noqa: BLE001
            if save_turn:
                save_turn(pk, "error", "", {"turn_id": turn_id})
            emit("error", f"❌ agent 运行失败：{str(e)[:180]}")
            emit("done", sessionKey=session_key)
            end()
            return

        if interrupted:
            qid = uuid.uuid4().hex
            payload = {"id": qid, "thread_id": session_key, "turn_id": turn_id,
                       "created_at": time.time(),
                       "questions": [{"questionId": qid,
                                      "question": interrupted["question"],
                                      "options": interrupted["options"]}]}
            _LIVE_INTERRUPTS[session_key] = {
                "emit": emit, "end": end, "pk": pk, "ts": time.monotonic(),
                "full_text": full_text, "config": config, "save_turn": save_turn,
                "pending_ids": [qid],
            }
            pg.pending_set(qid, session_key, {"id": qid, "thread_id": session_key,
                                              "created_at": time.time()})
            # 前端 ChatQuestion 契约：{"id", "questions":[{questionId,question,options}]}
            emit("question", json.dumps(payload, ensure_ascii=False))
            emit("activity", "⏸ 等待人工回答（回答后将自动继续）…")
            return  # 不发 done：SSE 保持打开，resume 后在同一连接续流

        text = "".join(full_text)
        _save_messages(session_key, _load_messages(session_key)
                       + [{"role": "user", "content": message},
                          {"role": "assistant", "content": text}])
        if save_turn:
            save_turn(pk, "done", text, {"turn_id": turn_id})
        emit("done", sessionKey=session_key)
        end()


def _finish_turn(session_key: str, pk: str, text: str, emit: Callable, end: Callable,
                 save_turn: Callable | None = None) -> None:
    history = _load_messages(session_key)
    _save_messages(session_key, history + [{"role": "assistant", "content": text}])
    if save_turn:
        try:
            save_turn(pk, "done", text, {})
        except Exception:
            pass
    emit("done", sessionKey=session_key)
    end()


async def answer(question_id: str, answers: Any, resolved_by: str = "web") -> dict:
    """恢复被 ask_human 中断的 agent：注入人工回答，续流输出到原 SSE 连接。"""
    payload = pg.pending_get(question_id)
    if payload is None:
        return {"ok": False, "error": "question not found"}
    sk = payload["thread_id"]
    live = _LIVE_INTERRUPTS.pop(sk, None)
    pg.pending_del(question_id)

    # 前端 QuestionCards 提交形如 {questionId: [选中的 label]}；格式化为可读文本注入
    if isinstance(answers, dict):
        parts = []
        for qid, sel in answers.items():
            sel_text = "、".join(sel) if isinstance(sel, list) else str(sel)
            parts.append(f"{qid} → {sel_text}")
        answer_text = "；".join(parts) if parts else json.dumps(answers, ensure_ascii=False)
    else:
        answer_text = str(answers)

    agent = await _build_agent()
    config = payload.get("config") or {"configurable": {"thread_id": pg.thread_id(sk)}}
    emit = (live or {}).get("emit")
    end = (live or {}).get("end")
    save_turn = (live or {}).get("save_turn")
    pk = (live or {}).get("pk")
    full_text: list[str] = (live or {}).get("full_text", [])
    live_stream = live is not None

    from langgraph.types import Command

    try:
        async for chunk, _meta in agent.astream(
            Command(resume={"decisions": [{"type": "respond", "message": answer_text}]}),
            config=config, stream_mode="messages",
        ):
            if not isinstance(chunk, AIMessageChunk):
                continue
            text = _to_text(getattr(chunk, "content", None))
            if text:
                full_text.append(text)
                if emit:
                    emit("token", text)
    except Exception as e:  # noqa: BLE001
        if emit:
            emit("error", f"❌ 续跑失败：{str(e)[:180]}")
        if live_stream and end:
            end()  # 修复 I3：resume 失败也要结束原连接，避免前端永久等待
        return {"ok": False, "error": str(e)}

    text = "".join(full_text)
    if live_stream and emit and end:
        _finish_turn(sk, pk, text, emit, end, save_turn)
    else:
        _save_messages(sk, _load_messages(sk) + [{"role": "assistant", "content": text}])
    return {"ok": True, "last_message": text}


def model_configured() -> bool:
    """模型是否已配置（OPENAI_API_KEY 存在）。供状态面板展示，替代原 OpenClaw 网关探活。"""
    return _build_model() is not None


async def ask(session_key: str, message: str) -> str:
    """非流式执行一轮，返回最终文本。

    被 ask_human 中断时不续答（非流式无法交互），返回提示文本让调用方改走流式对话。
    复用与 run_turn 相同的落盘历史 / checkpoint 注入逻辑。
    """
    async with _session_lock(session_key):
        _gc_live()
        model = _build_model()
        if model is None:
            return "❌ 未配置模型：请设置 OPENAI_API_KEY（可选 OPENAI_BASE_URL / ZIMEITI_MODEL）"
        try:
            agent = await _build_agent()
        except Exception as e:  # noqa: BLE001
            return f"❌ 运行时初始化失败：{str(e)[:180]}"

        config = {"configurable": {"thread_id": pg.thread_id(session_key)}}
        from langchain_core.messages import AIMessage, HumanMessage

        lc_messages: list = []
        if not await _checkpoint_has_messages(agent, config):
            for m in _load_messages(session_key):
                if m.get("content"):
                    lc_messages.append(
                        HumanMessage(content=m["content"]) if m["role"] == "user"
                        else AIMessage(content=m["content"])
                    )
        lc_messages.append(HumanMessage(content=message))

        full_text: list[str] = []
        try:
            async for chunk, _meta in agent.astream(
                {"messages": lc_messages}, config=config, stream_mode="messages"
            ):
                if not isinstance(chunk, AIMessageChunk):
                    continue
                text = _to_text(getattr(chunk, "content", None))
                if text:
                    full_text.append(text)
            snapshot = await agent.aget_state(config)
            interrupted = _extract_interrupt(snapshot)
        except Exception as e:  # noqa: BLE001
            return f"❌ agent 运行失败：{str(e)[:180]}"

        if interrupted:
            return (f"⏸ 该问题需要人工决策：{interrupted['question']}"
                    f"（请使用流式对话回答）")
        text = "".join(full_text)
        _save_messages(session_key, _load_messages(session_key)
                       + [{"role": "user", "content": message},
                          {"role": "assistant", "content": text}])
        return text


def ask_sync(session_key: str, message: str) -> str:
    """同步包装 ask（供线程池 / 同步上下文调用）。"""
    return asyncio.run(ask(session_key, message))
