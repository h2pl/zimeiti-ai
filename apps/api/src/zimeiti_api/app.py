"""FastAPI 应用（Task 1.4 + 7.2：审批 API）。"""

import re
from pathlib import Path

from fastapi import FastAPI, HTTPException
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

        data = load_profile_data(account)
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

        data = trends_data(account)
        if data is None:
            raise HTTPException(status_code=404, detail=f"账号无运营数据: {account}")
        return data

    @app.get("/api/outputs/{account}")
    def outputs(account: str) -> list[dict]:
        from zimeiti_api.operations.workbench import outputs as outputs_data

        return outputs_data(account, Path(OUTPUTS_DIR))

    @app.get("/api/publish-log")
    def publish_log() -> list[dict]:
        return audit.list_entries()

    return app


# uvicorn 入口：zimeiti_api.app:app
app = create_app()
