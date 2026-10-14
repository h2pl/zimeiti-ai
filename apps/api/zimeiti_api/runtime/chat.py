"""对话链路（runtime）：SSE 流式/非流式/HITL/技能执行/会话删除。

agent 执行委托 runtime.agent_runtime；历史与 checkpoint 在 PG（core.pg）。
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from . import agent_runtime as _agent_runtime
from ..content.uploads import _attachment_id, _attachment_scope
from ..content.personas import chat_turn_message, _persona_prefix
from ..content.skills import find_skill
from ..core import pg
from ..core.paths import (DEBUG_DIR, OUTPUTS_DIR, PROJECT_ROOT, SESSIONS_DIR, SHARED_SCRIPTS,
                          _safe_output_target)

router = APIRouter()

class AttachmentRef(BaseModel):
    id: str
    name: str
    path: str


class ChatRequest(BaseModel):
    message: str
    persona: str | None = None
    sessionId: str | None = None
    turnId: str | None = None
    attachments: list[AttachmentRef] = Field(default_factory=list)


def _attachment_context(req: ChatRequest) -> str:
    """Validate attachment ownership and build an Agent-only attachment manifest."""
    if not req.attachments:
        return ""
    if not req.sessionId:
        raise HTTPException(400, "附件必须绑定到会话")

    scope = _attachment_scope(req.sessionId)
    rows: list[str] = []
    seen: set[str] = set()
    for attachment in req.attachments:
        rel = Path(attachment.path)
        if rel.is_absolute() or ".." in rel.parts or len(rel.parts) != 4:
            raise HTTPException(400, "附件路径无效")
        if rel.parts[0] != "_inbox" or rel.parts[1] != scope:
            raise HTTPException(403, "附件不属于当前会话")
        normalized = rel.as_posix()
        if attachment.id != _attachment_id(scope, normalized):
            raise HTTPException(403, "附件标识校验失败")
        full = _safe_output_target(normalized)
        if not full.is_file():
            raise HTTPException(404, f"附件不存在：{attachment.name}")
        if normalized in seen:
            continue
        seen.add(normalized)
        rows.append(f"- outputs/{normalized}")

    return (
        "〔系统附件清单，仅供本轮执行，不要向用户复述文件上传过程或内部路径〕\n"
        "只允许使用下列当前会话附件；禁止扫描、枚举或猜测 outputs/_inbox 中的其他文件：\n"
        + "\n".join(rows)
        + "\n需要纳入内容项目时，将清单内文件复制到 outputs/<项目>/assets/ 后再使用；"
          "保留 inbox 原件，确保重试仍可复现。"
    )


def _chat_message(req: ChatRequest) -> str:
    context = _attachment_context(req)
    message = req.message.strip()
    if context:
        message = f"{message}\n\n{context}" if message else context
    if not message:
        raise HTTPException(400, "消息不能为空")
    return chat_turn_message(message, req.persona)


def _turn_file(sk: str) -> Path:
    """每会话最近一轮结果的落盘路径（sk 做文件名安全化）。"""
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", sk)[:120]
    return SESSIONS_DIR / f"{safe}.json"


def _job_event_file(turn_id: str) -> Path:
    """Per-turn append-only event log used to resume SSE without restarting the agent."""
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", turn_id)[:160]
    return SESSIONS_DIR / "jobs" / f"{safe}.jsonl"


def _read_job_events(turn_id: str, after: int = 0) -> list[dict]:
    path = _job_event_file(turn_id)
    if not path.is_file():
        return []
    events = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            event = json.loads(line)
            if int(event.get("id", 0)) > after:
                events.append(event)
    except (OSError, ValueError, json.JSONDecodeError):
        return []
    return events


def _raw_event_for_run(line: str, expected_run_id: str | None) -> dict | None:
    """Parse one agent event and reject events from other runs.

    The gateway multiplexes every run into one shared raw-stream file, and its
    events carry `runId` (not `sessionId`). A turn latches onto its own runId —
    the first event seen after the turn starts — and must ignore any event with
    a different runId. `expected_run_id=None` means not-yet-latched → accept, so
    the caller can latch from `event['runId']`.
    """
    line = line.strip()
    if not line:
        return None
    try:
        event = json.loads(line)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(event, dict):
        return None
    if expected_run_id is not None:
        rid = event.get("runId")
        if rid is not None and rid != expected_run_id:
            return None
    return event


def _save_turn(sk: str, status: str, text: str, extra: dict | None = None) -> None:
    """持久化本轮结果（running/done），供 SSE 连接中断后前端用 /api/chat/last 取回。

    后端跑完整轮不依赖客户端连接——长任务时 webide 代理会掐断 SSE，但 deepagents 仍跑到底，
    结果写这里，前端断线后轮询即可拿到完整回答（否则"运行完也不说一声"）。
    """
    try:
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        payload = {"status": status, "text": text, "at": time.strftime("%Y-%m-%dT%H:%M:%S")}
        if extra:
            payload.update(extra)
        tmp = _turn_file(sk).with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, _turn_file(sk))
    except Exception:
        pass


# 后台 supervisor 任务集合：持有强引用防被 GC；每个对话流的 deepagents 回合跑在这里，
# 与客户端 SSE 连接解耦（断线不杀回合）。
_BG_TASKS: set = set()

# 正在跑的对话回合（sk→asyncio.Task），供用户**显式「停止」**取消；断线**不**经此路径（断线不杀）。
_RUNNING_CHAT: dict[str, asyncio.Task] = {}


@router.get("/api/chat/last/{session_id}")
async def api_chat_last(session_id: str, turn_id: str | None = None):
    """取某会话最近一轮的完整结果（SSE 断线后前端据此取回，避免丢结果）。"""
    f = _turn_file(f"web:{session_id}")
    if not f.is_file():
        return {"status": "none", "text": ""}
    try:
        payload = json.loads(f.read_text(encoding="utf-8"))
        if turn_id and payload.get("turn_id") != turn_id:
            return {"status": "stale", "text": "", "turn_id": payload.get("turn_id")}
        return payload
    except Exception:
        return {"status": "none", "text": ""}


@router.get("/api/chat/jobs/{turn_id}/stream")
async def api_chat_job_stream(turn_id: str, after: int = 0):
    """Replay missed events, then tail this turn until its terminal event arrives."""
    # A stale browser-side pendingTurnId must fail promptly instead of receiving
    # heartbeats forever. The frontend can then recover from the final snapshot.
    if not _job_event_file(turn_id).is_file():
        raise HTTPException(404, "对话任务记录不存在或已失效")

    async def events():
        cursor = max(0, after)
        idle_since = time.monotonic()
        while True:
            batch = _read_job_events(turn_id, cursor)
            if batch:
                idle_since = time.monotonic()
                for event in batch:
                    cursor = int(event["id"])
                    yield {
                        "id": str(cursor),
                        "event": event["event"],
                        "data": json.dumps(event.get("data"), ensure_ascii=False),
                    }
                    if event["event"] in ("done", "error"):
                        return
            else:
                # Keep proxy connections active; reconnecting remains safe if it still drops.
                if time.monotonic() - idle_since >= 15:
                    yield {"event": "ping", "data": "{}"}
                    idle_since = time.monotonic()
                await asyncio.sleep(0.25)

    return EventSourceResponse(events(), headers={
        "Cache-Control": "no-cache, no-transform",
        "X-Accel-Buffering": "no",
        "Content-Encoding": "identity",
    })


@router.post("/api/chat/stream")
async def api_chat_stream(req: ChatRequest):
    """SSE 真流式对话。

    由 deepagents 进程内运行时（替代 OpenClaw 网关）按 SSE 契约逐 token 发帧；结果落盘，
    前端断线后可由 /api/chat/last 取回完整结果。
    """
    # 每轮末尾追加「先查技能库」提醒，抗长对话指令衰减（对用户不可见）
    message = _chat_message(req)

    # supervisor（跑 deepagents 一轮）与 forward（转发 SSE 给浏览器）之间的事件通道。
    # 关键：run 跑在独立后台任务里，客户端断开只结束 forward，不取消 supervisor →
    # deepagents 照常跑到底、结果落盘，前端断线后 /api/chat/last 取回。
    client_q: asyncio.Queue = asyncio.Queue()
    CLIENT_DONE = object()

    sk = req.sessionId or f"web-{int(time.time() * 1000)}"

    async def supervisor(sk: str):
        pk = f"web:{sk}"                 # 落盘 key（与 /api/chat/last 一致）
        turn_id = req.turnId or uuid.uuid4().hex
        event_seq = 0

        # Claim this turn before waiting for locks, so recovery cannot return the previous turn.
        _save_turn(pk, "running", "", {"turn_id": turn_id})

        event_path = _job_event_file(turn_id)
        try:
            event_path.parent.mkdir(parents=True, exist_ok=True)
            event_path.write_text("", encoding="utf-8")
        except OSError:
            pass

        def to_client(kind, text=None, **extra):
            nonlocal event_seq
            event_seq += 1
            data = ({"sessionKey": extra.get("sessionKey")} if kind == "done" else text)
            event = {"id": event_seq, "event": kind, "data": data}
            try:
                with event_path.open("a", encoding="utf-8") as ef:
                    ef.write(json.dumps(event, ensure_ascii=False) + "\n")
                    ef.flush()
            except OSError:
                pass
            client_q.put_nowait({"t": kind, "text": text, "id": event_seq, **extra})

        # 秒级反馈：发出即亮「已收到」，不等 agent 冷启动（首个 SSE 事件，随流回放必达）
        to_client("activity", "⏳ 已收到，正在唤醒 agent…")

        # deepagents 进程内运行时（openclaw 已全面移除）。
        try:
            await _agent_runtime.run_turn(
                sk, message, pk, turn_id, event_path, to_client,
                lambda: client_q.put_nowait(CLIENT_DONE),
                save_turn=_save_turn,
            )
        except asyncio.CancelledError:
            # 用户经 /api/chat/stop 显式停止：正常收尾（落盘 + 解锁 forward），不当异常上报。
            to_client("activity", "⏹ 已按要求停止本轮对话")
            _save_turn(pk, "stopped", "", {"turn_id": turn_id, "stopped": True})
            client_q.put_nowait(CLIENT_DONE)
            return
        return


    # 把 run 跑在独立后台任务里（持强引用防 GC）——客户端断开不取消它。
    task = asyncio.create_task(supervisor(sk))
    _BG_TASKS.add(task)
    _RUNNING_CHAT[sk] = task

    def _bg_done(t):
        _BG_TASKS.discard(t)
        _RUNNING_CHAT.pop(sk, None)
        try:
            exc = t.exception()   # 取出异常避免「never retrieved」告警
        except Exception:
            exc = None
        if exc is not None:
            # supervisor 意外崩溃：解锁 forward，别让它空等
            try:
                client_q.put_nowait(CLIENT_DONE)
            except Exception:
                pass
    task.add_done_callback(_bg_done)

    async def forward():
        """纯转发：从 client_q 取事件 yield 给浏览器。

        客户端断开（关标签/代理掐断）只会结束本生成器，supervisor 任务不受影响，
        继续把 deepagents 跑完并落盘 → 前端断线后 /api/chat/last 取回完整结果。
        """
        idle_since = time.monotonic()
        while True:
            try:
                item = await asyncio.wait_for(client_q.get(), timeout=10)
            except asyncio.TimeoutError:
                # 长时间无输出（等模型长回复 / 制作类长任务）→ 发心跳，让用户知道没卡死。
                # 用独立的 `heartbeat` 事件，不走 `activity`：否则会覆盖掉真实的
                # 「🧠 正在思考…/🛠️ 制作中…」状态与思考流（防呆消息把思考设计顶掉的根因）。
                # 发出后重置 idle_since → 心跳按 30s 一次的节奏，不再每 10s 重复刷屏。
                if time.monotonic() - idle_since >= 30:
                    idle_since = time.monotonic()
                    yield {"event": "heartbeat", "data": json.dumps(
                        "仍在处理中，未卡住…（复杂或制作类任务会花点时间）", ensure_ascii=False)}
                continue
            if item is CLIENT_DONE:
                break
            idle_since = time.monotonic()
            t = item["t"]
            if t == "token":
                yield {"id": str(item["id"]), "event": "token", "data": json.dumps(item["text"], ensure_ascii=False)}
            elif t == "thinking":
                yield {"id": str(item["id"]), "event": "thinking", "data": json.dumps(item["text"], ensure_ascii=False)}
            elif t == "activity":
                yield {"id": str(item["id"]), "event": "activity", "data": json.dumps(item["text"], ensure_ascii=False)}
            elif t == "question":
                yield {"id": str(item["id"]), "event": "question", "data": item["text"]}
            elif t == "error":
                yield {"id": str(item["id"]), "event": "error", "data": json.dumps(item["text"], ensure_ascii=False)}
            elif t == "done":
                yield {"id": str(item["id"]), "event": "done", "data": json.dumps({"sessionKey": item.get("sessionKey")}, ensure_ascii=False)}

    return EventSourceResponse(forward(), headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no", "Content-Encoding": "identity"})


class QuestionAnswerRequest(BaseModel):
    sessionId: str | None = None
    questionId: str
    answers: dict  # {questionId: [optionValues]}
    resolvedBy: str | None = None


@router.post("/api/chat/question/answer")
async def api_question_answer(req: QuestionAnswerRequest):
    """前端点击 ask_user 选项后调用：resume 被中断的 deepagents，续流输出到原 SSE 连接。"""
    return await _agent_runtime.answer(req.questionId, req.answers or {}, req.resolvedBy)


class QuestionStatusRequest(BaseModel):
    questionIds: list[str]


@router.post("/api/chat/question/status")
async def api_question_status(req: QuestionStatusRequest):
    """批量查 question 状态（重放旧事件时过滤已解决的题）。"""
    return {"ok": True, "questions": _agent_runtime.pending_status(req.questionIds)}


class StopRequest(BaseModel):
    sessionId: str | None = None


@router.post("/api/chat/stop")
async def api_chat_stop(req: StopRequest):
    """用户显式停止当前会话正在跑的 deepagents 回合：取消后台任务 → supervisor 收尾落盘
    并解锁 forward → 下一句立刻能发。仅此显式入口会取消；客户端断线不经此路径。"""
    sk = (req.sessionId or "").strip()
    task = _RUNNING_CHAT.get(sk) if sk else None
    if task is not None and not task.done():
        task.cancel()
        try:
            await asyncio.wait({task}, timeout=3)   # 等 supervisor 完成收尾（落盘/解锁）
        except Exception:  # noqa: BLE001
            pass
        return {"stopped": True}
    return {"stopped": False}          # 没有在跑（可能已结束）→ 前端照常清理即可


@router.post("/api/chat")
async def api_chat(req: ChatRequest):
    """非流式对话（备选）。"""
    # 每轮末尾追加「先查技能库」提醒，抗长对话指令衰减（对用户不可见）
    message = _chat_message(req)
    sk = req.sessionId or f"web-{int(time.time() * 1000)}"
    # 与流式 /api/chat/stream 一致走 deepagents 运行时
    result = await _agent_runtime.ask(sk, message)
    return {"response": result}


class SkillRequest(BaseModel):
    skill: str
    input: str
    persona: str | None = None


@router.post("/api/skill")
async def api_skill(req: SkillRequest):
    skill_full = find_skill(req.skill)
    if skill_full is None:
        raise HTTPException(404, f"SKILL '{req.skill}' 不存在")
    message = f"{_persona_prefix(req.persona)}请执行 /{skill_full}，内容如下：\n\n{req.input}"
    sk = req.sessionId or f"web-{int(time.time() * 1000)}"
    result = await _agent_runtime.ask(sk, message)
    return {"response": result}


@router.delete("/api/session/{session_key}")
async def api_delete_session(session_key: str):
    """删除会话全部状态：PG 消息/会话行 + PG checkpoint + HITL pending
    （pg-data-layer 变更，历史/checkpoint/pending 均已迁 PostgreSQL，不再是
    apps/sessions 文件与 InMemorySaver）+ 活跃中断登记 + 轮次结果
    （apps/outputs/_sessions，按设计留文件）。
    各处都删净，同 key 再聊才不会「复活」旧上下文。"""
    deleted = await _agent_runtime.delete_session(session_key)
    try:
        tf = _turn_file(session_key)   # 内部已做文件名安全化
        if tf.is_file():
            tf.unlink()
            deleted = True
    except OSError:
        pass
    return {'deleted': deleted}


TREND_SOURCES: dict[str, tuple[str, str | None]] = {
    "weibo": ("https://60s.viki.moe/v2/weibo", "https://v2.xxapi.cn/api/weibohot"),
    "douyin": ("https://60s.viki.moe/v2/douyin", "https://v2.xxapi.cn/api/douyinhot"),
    "zhihu": ("https://60s.viki.moe/v2/zhihu", None),
    "bilibili": ("https://60s.viki.moe/v2/bili", "https://v2.xxapi.cn/api/bilibilihot"),
    "baidu": ("https://60s.viki.moe/v2/baidu/hot", "https://v2.xxapi.cn/api/baiduhot"),
    "toutiao": ("https://60s.viki.moe/v2/toutiao", None),
}
TREND_LABELS = {
    "weibo": "微博",
    "douyin": "抖音",
    "zhihu": "知乎",
    "bilibili": "B站",
    "baidu": "百度",
    "toutiao": "头条",
}
_TREND_CACHE: dict[str, tuple[float, list]] = {}


