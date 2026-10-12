"""FastAPI 应用（Task 1.4 + 7.2：审批 API）。"""

import json
import re
from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from fastapi import FastAPI, HTTPException
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from zimeiti_api.config import OUTPUTS_DIR
from zimeiti_api.content import profiles as content_profiles
from zimeiti_api.core import audit
from zimeiti_api.governance.publisher import PublishExecutor
from zimeiti_api.operations.metrics import MetricsDB
from zimeiti_api.runtime import hosted
from zimeiti_api.runtime.checkpoints import DATABASE_URL

# 进程级单例执行器：频控计数跨请求持久（评审 W2 升级项修复）
EXECUTOR = PublishExecutor(daily_limit=2, allowed_accounts={"xhs-main", "gzh-main"})
_THREAD_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def create_app(lifespan=None) -> FastAPI:
    """lifespan：网关模式注入调度器后台任务（app.py 纯 API 模式不启动调度）。"""
    app = FastAPI(title="Zimeiti AI API", lifespan=lifespan)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/api/approvals")
    def list_approvals() -> list[dict]:
        return hosted.list_pending_approvals()

    def _rearm_pending_if_interrupted(
        thread_id: str, result: dict, account: str, instruction: str
    ) -> None:
        """双闸门重登记：恢复后若再次中断（如选题通过→发布审批），必须重新登记待审批。

        实测缺陷（2026-10-10 托管 E2E）：单闸门测试未覆盖「一次恢复命中下一个中断」，
        旧实现只删 pending 不补登，循环在发布闸门永久卡死（审批页看不到）。
        ask_human 提问中断（P1⑧）同样重登记为 question 类型。
        """
        if "__interrupt__" not in result:
            return
        payload = hosted.extract_interrupt_payload(result)
        if payload:
            hosted._add_pending(
                thread_id, instruction, account=account, kind="question", question=payload
            )
        else:
            hosted._add_pending(thread_id, instruction, account=account)
        audit.record("awaiting_approval", thread_id=thread_id)

    def _resume_thread(thread_id: str, decisions: list[dict], account: str) -> dict:
        """按 pending 记录的账号恢复执行图（修复评审遗留：profile 不再硬编码 xhs-main）。

        同步 saver：FastAPI sync 端点内零 async loop 问题；
        中断态由 async saver 写入，表结构相同，sync saver 可读。
        decisions：deepagents/langchain HITL 决策（approve/reject/respond…）。
        """
        from langgraph.checkpoint.postgres import PostgresSaver

        from zimeiti_api.content.profiles import load_profile
        from zimeiti_api.core.models import get_model
        from zimeiti_api.runtime.graph import build_minimal_agent

        if not _THREAD_ID_RE.match(thread_id):
            raise HTTPException(status_code=400, detail="非法 thread_id（允许字母数字._-）")
        profile = load_profile(account)
        cycle_dir = str(Path(OUTPUTS_DIR) / profile["account"] / thread_id)
        with PostgresSaver.from_conn_string(DATABASE_URL) as saver:
            saver.setup()
            agent = build_minimal_agent(get_model(), saver, profile, EXECUTOR, cycle_dir)
            return agent.invoke(
                Command(resume={"decisions": decisions}),
                config={"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}},
            )

    @app.post("/api/approvals/{thread_id}/confirm")
    def confirm_approval(thread_id: str) -> dict:
        """人工确认发布 → 同步 checkpointer resume 执行图（工厂接线，评审 C1-C4）。"""
        pending = [p for p in hosted.list_pending_approvals() if p["thread_id"] == thread_id]
        if not pending:
            raise HTTPException(status_code=404, detail=f"无待审批项: {thread_id}")
        if pending[0].get("kind") == "question":
            raise HTTPException(status_code=400, detail="提问类型请用 /api/questions/{id}/answer")
        # account 随中断记录；修复前遗留的旧记录无此字段，回退 xhs-main 保持原行为
        account = pending[0].get("account") or "xhs-main"
        instruction = pending[0].get("instruction", "")
        result = _resume_thread(thread_id, [{"type": "approve"}], account)
        hosted._remove_pending(thread_id)
        audit.record("approval_received", thread_id=thread_id)
        _rearm_pending_if_interrupted(thread_id, result, account, instruction)
        if "__interrupt__" not in result:
            audit.record("cycle_completed", thread_id=thread_id)
        return {"thread_id": thread_id, "last_message": result["messages"][-1].content}

    @app.post("/api/approvals/{thread_id}/reject")
    def reject_approval(thread_id: str) -> dict:
        """拒绝发布 → 以 reject 决策恢复执行图（评审 W5）。"""
        pending = [p for p in hosted.list_pending_approvals() if p["thread_id"] == thread_id]
        if not pending:
            raise HTTPException(status_code=404, detail=f"无待审批项: {thread_id}")
        account = pending[0].get("account") or "xhs-main"  # 兼容修复前遗留的旧记录
        instruction = pending[0].get("instruction", "")
        result = _resume_thread(thread_id, [{"type": "reject"}], account)
        hosted._remove_pending(thread_id)
        audit.record("approval_rejected", thread_id=thread_id)
        _rearm_pending_if_interrupted(thread_id, result, account, instruction)
        return {"thread_id": thread_id, "last_message": result["messages"][-1].content}

    @app.post("/api/questions/{thread_id}/answer")
    def answer_question(thread_id: str, body: dict) -> dict:
        """回答 agent 的结构化提问（P1⑧）：respond 决策把人的回答注入为工具结果。"""
        pending = [p for p in hosted.list_pending_approvals() if p["thread_id"] == thread_id]
        if not pending:
            raise HTTPException(status_code=404, detail=f"无待处理项: {thread_id}")
        if pending[0].get("kind") != "question":
            raise HTTPException(status_code=400, detail="该待处理项不是提问类型")
        message = str(body.get("message", "")).strip()
        if not message:
            raise HTTPException(status_code=400, detail="回答不能为空")
        account = pending[0].get("account") or "xhs-main"
        instruction = pending[0].get("instruction", "")
        result = _resume_thread(thread_id, [{"type": "respond", "message": message}], account)
        hosted._remove_pending(thread_id)
        audit.record("question_answered", thread_id=thread_id, message=message[:200])
        _rearm_pending_if_interrupted(thread_id, result, account, instruction)
        return {"thread_id": thread_id, "last_message": result["messages"][-1].content}

    @app.get("/api/kanban")
    def kanban() -> dict:
        """选题三态看板（P1⑪，Easel IdeasPage 对标）。"""
        from zimeiti_api.operations.kanban import collect_cards

        return collect_cards(OUTPUTS_DIR)

    @app.post("/api/kanban/move")
    def kanban_move(body: dict) -> dict:
        from zimeiti_api.operations.kanban import set_status

        set_status(str(body.get("title", "")), str(body.get("status", "")))
        return {"ok": True}

    @app.get("/api/calendar")
    def calendar() -> list[dict]:
        """内容日历（P1⑪，Easel CalendarPage 对标；发布事件只读）。"""
        from zimeiti_api.operations.kanban import calendar_events
        from zimeiti_api.operations.metrics import MetricsDB

        return calendar_events(MetricsDB())

    @app.get("/api/dashboard")
    def dashboard() -> dict:
        """概览（web-workbench T1）：待审批数/账号启停/今日发布/最近日志。"""
        from zimeiti_api.operations.workbench import dashboard_summary, list_accounts

        accounts = {
            a["account"]: a["enabled"]
            for a in list_accounts(Path(content_profiles.DEFAULT_BASE_DIR))
        }
        return dashboard_summary(
            pending_count=len(hosted.list_pending_approvals()),
            accounts=accounts,
            publish_events=MetricsDB().list_events(),
            recent_log=audit.list_entries(),
        )

    @app.get("/api/profiles")
    def profiles_list() -> list[dict]:
        from zimeiti_api.operations.workbench import list_accounts

        return list_accounts(Path(content_profiles.DEFAULT_BASE_DIR))

    @app.get("/api/profiles/{account}")
    def profile_get(account: str) -> dict:
        from zimeiti_api.operations.workbench import load_profile_data

        try:
            data = load_profile_data(account)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if data is None:
            raise HTTPException(status_code=404, detail=f"账号不存在: {account}")
        return data

    @app.put("/api/profiles/{account}")
    def profile_put(account: str, body: dict) -> dict:
        """受控画像写（D3）：validate fail-closed，非法输入 400 不落盘。"""
        from zimeiti_api.operations.workbench import save_profile

        try:
            save_profile(account, body)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"ok": True}

    @app.get("/api/trends/{account}")
    def trends(account: str) -> dict:
        from zimeiti_api.operations.workbench import trends as trends_data

        try:
            data = trends_data(account)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if data is None:
            raise HTTPException(status_code=404, detail=f"账号无运营数据: {account}")
        return data

    @app.get("/api/outputs/{account}")
    def outputs(account: str) -> list[dict]:
        from zimeiti_api.operations.workbench import outputs as outputs_data

        try:
            return outputs_data(account, Path(OUTPUTS_DIR))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/accounts")
    def accounts_detail() -> list[dict]:
        """账号管理数据面（web-pages-batch T2）。"""
        from zimeiti_api.config import CREDENTIALS_DIR, LOGIN_STATE_PATH
        from zimeiti_api.operations.workbench import accounts_detail

        return accounts_detail(
            Path(content_profiles.DEFAULT_BASE_DIR), Path(CREDENTIALS_DIR), Path(LOGIN_STATE_PATH)
        )

    @app.post("/api/accounts/{account}/toggle")
    def account_toggle(account: str, body: dict) -> dict:
        """启停切换（fail-closed 语义复用 platform_state）。"""
        import re as _re

        if not _re.match(r"^[A-Za-z0-9_-]+$", account):
            raise HTTPException(status_code=400, detail="非法账号名")
        from zimeiti_api.content.profiles import DEFAULT_BASE_DIR as _profiles_dir
        from zimeiti_api.governance import platform_state

        if not (_profiles_dir / account / "profile.yaml").exists():
            raise HTTPException(status_code=404, detail=f"账号不存在: {account}")
        enabled = bool(body.get("enabled"))
        platform_state.set_enabled(account, enabled, reason="手动切换（账号管理页）")
        audit.record("account_toggled", account=account, enabled=enabled)
        return {"account": account, "enabled": enabled}

    @app.get("/api/postmortems/{platform}")
    def postmortem_list(platform: str) -> dict:
        """复盘清单（web-pages-batch T3，复用 postmortem 模块）。"""
        from zimeiti_api.operations.metrics import MetricsDB
        from zimeiti_api.operations.postmortem import top_formula

        return top_formula(MetricsDB(), platform, top=50)

    @app.get("/api/postmortems/{platform}/{title}")
    def postmortem_note(platform: str, title: str) -> dict:
        from zimeiti_api.operations.metrics import MetricsDB
        from zimeiti_api.operations.postmortem import note_evidence, render_note

        ev = note_evidence(MetricsDB(), platform, title)
        if ev is None:
            raise HTTPException(status_code=404, detail=f"未找到事件: {title}")
        return {"evidence": ev, "markdown": render_note(ev)}

    @app.get("/api/settings")
    def settings_get() -> dict:
        from zimeiti_api.core.settings import get_settings

        return get_settings()

    @app.put("/api/settings")
    def settings_put(body: dict) -> dict:
        from zimeiti_api.core.settings import update_settings

        try:
            return update_settings(body)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/ops/trigger")
    def ops_trigger(body: dict) -> dict:
        """手动触发运维任务（写标记文件，网关下一循环消费——D4）。"""
        import json as _json

        job = str(body.get("job", ""))
        if job not in ("hosted_content", "ops_data", "health_check"):
            raise HTTPException(status_code=400, detail="非法任务名")
        from zimeiti_api.config import DATA_DIR

        p = Path(DATA_DIR) / "state" / "ops-trigger.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        # W1：读-合并-写（避免连续触发两个不同任务时后者覆写前者）
        existing: dict = {}
        try:
            existing = _json.loads(p.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            existing = {}
        existing[job] = True
        p.write_text(_json.dumps(existing, ensure_ascii=False), encoding="utf-8")
        audit.record("ops_triggered", job=job)
        return {"triggered": job}

    @app.get("/api/tools")
    def tools_list() -> list[dict]:
        """agent 工具清单（web-pages-batch T5，只读）。"""
        from zimeiti_api.content.profiles import load_profile
        from zimeiti_api.runtime.tools import tool_catalog

        try:
            profile = load_profile("xhs-main")
        except Exception:  # noqa: BLE001 - 画像缺失时返回空清单（评审 S2）
            return []
        cycle_dir = str(Path(OUTPUTS_DIR) / profile["account"] / "_catalog")
        # model 传 None：清单只读 name/description，闭包不调用（省 LLM 客户端创建）
        return tool_catalog(profile, None, EXECUTOR, cycle_dir)

    @app.post("/api/chat/sessions")
    def chat_sessions_create(body: dict) -> dict:
        """创建对话会话（thread_id 即 checkpointer 线程，D1）。"""
        from zimeiti_api.runtime.chat import create_session

        account = str(body.get("account", "xhs-main"))
        title = str(body.get("title", ""))
        return create_session(account, title)

    @app.get("/api/chat/sessions")
    def chat_sessions_list() -> list[dict]:
        from zimeiti_api.runtime.chat import list_sessions

        return list_sessions()

    def _sse(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    @app.post("/api/chat/sessions/{thread_id}/stream")
    async def chat_stream(thread_id: str, body: dict):
        """流式对话（D2）：token 增量 + interrupt 帧 + done。"""
        from zimeiti_api.runtime.chat import get_session

        session = get_session(thread_id)
        if session is None:
            raise HTTPException(status_code=404, detail=f"会话不存在: {thread_id}")
        message = str(body.get("message", "")).strip()
        if not message:
            raise HTTPException(status_code=400, detail="消息不能为空")
        account = session["account"]
        from zimeiti_api.content.profiles import load_profile
        from zimeiti_api.core.models import get_model

        profile = load_profile(account)

        from zimeiti_api.runtime.checkpoints import get_checkpointer
        from zimeiti_api.runtime.graph import build_minimal_agent

        async def gen():
            from langchain_core.messages import AIMessageChunk, HumanMessage

            yield _sse("start", {"thread_id": thread_id})
            try:
                async with get_checkpointer() as saver:
                    agent = build_minimal_agent(
                        get_model(),
                        saver,
                        profile,
                        EXECUTOR,
                        cycle_dir=str(Path(OUTPUTS_DIR) / account / thread_id),
                    )
                    config: RunnableConfig = {
                        "configurable": {"thread_id": thread_id, "checkpoint_ns": ""}
                    }
                    # stream_mode 双模式为 langgraph 运行时合法参数（mypy overload 不覆盖列表形态）
                    stream = cast(
                        "AsyncIterator[tuple[str, Any]]",
                        agent.astream(
                            {"messages": [HumanMessage(message)]},
                            config,
                            stream_mode=["messages", "updates"],
                        ),
                    )
                    async for mode, payload in stream:
                        if mode == "messages":
                            chunk, _meta = payload
                            if isinstance(chunk, AIMessageChunk) and chunk.content:
                                # S2：list 型 content 取 str 块拼接（评审 S2）
                                text = (
                                    chunk.text() if hasattr(chunk, "text") else str(chunk.content)
                                )
                                yield _sse("token", {"text": text})
                        elif isinstance(payload, dict) and "__interrupt__" in payload:
                            payloads = hosted.extract_interrupt_payload(
                                {"__interrupt__": payload["__interrupt__"]}
                            )
                            if payloads:
                                hosted._add_pending(
                                    thread_id,
                                    message,
                                    account=account,
                                    kind="question",
                                    question=payloads,
                                )
                            else:
                                hosted._add_pending(thread_id, message, account=account)
                            audit.record("awaiting_approval", thread_id=thread_id)
                            yield _sse("interrupt", {"pending": True})
                yield _sse("done", {})
            except Exception as exc:  # noqa: BLE001 - 流内错误以 error 帧下发
                yield _sse("error", {"message": str(exc)[:300]})
                yield _sse("done", {})

        from fastapi.responses import StreamingResponse

        return StreamingResponse(gen(), media_type="text/event-stream")

    @app.get("/api/chat/sessions/{thread_id}/messages")
    async def chat_messages(thread_id: str) -> dict:
        """从 checkpointer 重建消息流（D3）。"""
        from langchain_core.messages import AIMessage, HumanMessage

        from zimeiti_api.runtime.chat import get_session
        from zimeiti_api.runtime.checkpoints import get_checkpointer

        session = get_session(thread_id)
        if session is None:
            raise HTTPException(status_code=404, detail=f"会话不存在: {thread_id}")
        config: RunnableConfig = {"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}}
        async with get_checkpointer() as saver:
            tup = await saver.aget_tuple(config)
        messages: list[dict] = []
        if tup is not None:
            for m in (tup.checkpoint.get("channel_values", {}) or {}).get("messages", []):
                if isinstance(m, (HumanMessage, AIMessage)) and m.content:
                    text = m.text() if hasattr(m, "text") else str(m.content)
                    messages.append({"role": m.type, "content": text})
        return {"messages": messages}

    @app.get("/api/publish-queue")
    def publish_queue_list() -> list[dict]:
        from zimeiti_api.governance.queue import list_entries

        return list_entries()

    @app.post("/api/publish-queue/enqueue")
    def publish_queue_enqueue(body: dict) -> dict:
        """内容库草稿入队（幂等：同 drafts_path 的 pending 拒绝重复）。"""
        from zimeiti_api.governance import queue
        from zimeiti_api.operations.workbench import valid_account

        account = str(body.get("account", ""))
        slug = str(body.get("slug", ""))
        if not (valid_account(account) and valid_account(slug)):
            raise HTTPException(status_code=400, detail="非法 account/slug")
        drafts_dir = Path(OUTPUTS_DIR) / account / slug
        if not (drafts_dir / "drafts.json").exists():
            raise HTTPException(status_code=404, detail="草稿不存在")
        # C1（评审）：存目录路径——queue.execute_approved_publish 约定 drafts_path
        # 为目录（其内拼接 drafts.json）；存文件路径会导致到期发布必然 FileNotFoundError
        drafts_path = str(drafts_dir)
        for e in queue.list_entries():
            if e.get("drafts_path") == drafts_path and e.get("status") == "pending":
                raise HTTPException(status_code=409, detail="该草稿已在待发布队列")
        run_at = (
            str(body.get("run_at"))
            if body.get("run_at")
            else datetime.now().isoformat(timespec="seconds")
        )
        title = str(body.get("title", ""))
        entry_id = queue.schedule(account, drafts_path, run_at, title=title)
        return {"entry_id": entry_id}

    @app.get("/api/outputs/{account}/{slug}")
    def output_detail(account: str, slug: str) -> dict:
        """单篇产物全文（feat-outputs-viewer）。"""
        from zimeiti_api.operations.workbench import output_detail as _detail

        try:
            return _detail(account, slug, Path(OUTPUTS_DIR))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/outputs/{account}/{slug}/cover.png")
    def output_cover(account: str, slug: str):
        """封面图（D2：FileResponse，不存在 404）。"""
        from fastapi.responses import FileResponse

        from zimeiti_api.operations.workbench import cover_path

        try:
            p = cover_path(account, slug, Path(OUTPUTS_DIR))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if p is None:
            raise HTTPException(status_code=404, detail="封面不存在")
        return FileResponse(str(p))

    @app.get("/api/publish-log")
    def publish_log() -> list[dict]:
        return audit.list_entries()

    return app


# uvicorn 入口：zimeiti_api.app:app
app = create_app()
