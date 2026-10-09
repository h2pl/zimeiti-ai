"""FastAPI 应用（Task 1.4 + 7.2：审批 API）。"""

import re

from fastapi import FastAPI, HTTPException
from langgraph.types import Command

from zimeiti_api.publisher import PublishExecutor

from zimeiti_api import audit, hosted
from zimeiti_api.checkpoints import DATABASE_URL


# 进程级单例执行器：频控计数跨请求持久（评审 W2 升级项修复）
EXECUTOR = PublishExecutor(daily_limit=2, allowed_accounts={"xhs-main", "gzh-main"})
_THREAD_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def create_app() -> FastAPI:
    app = FastAPI(title="Zimeiti AI API")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/api/approvals")
    def list_approvals() -> list[dict]:
        return hosted.list_pending_approvals()

    @app.post("/api/approvals/{thread_id}/confirm")
    def confirm_approval(thread_id: str) -> dict:
        """人工确认发布 → 同步 checkpointer resume 执行图（工厂接线，评审 C1-C4）。"""
        pending = [p for p in hosted.list_pending_approvals() if p["thread_id"] == thread_id]
        if not pending:
            raise HTTPException(status_code=404, detail=f"无待审批项: {thread_id}")

        # 同步 saver：FastAPI sync 端点内零 async loop 问题；
        # 中断态由 async saver 写入，表结构相同，sync saver 可读。
        from langgraph.checkpoint.postgres import PostgresSaver

        from zimeiti_api.graph import build_minimal_agent
        from zimeiti_api.models import get_model
        from zimeiti_api.profiles import load_profile
        from zimeiti_api.publisher import PublishExecutor

        if not _THREAD_ID_RE.match(thread_id):
            raise HTTPException(status_code=400, detail="非法 thread_id（允许字母数字._-）")
        profile = load_profile("xhs-main")
        cycle_dir = f"outputs/{profile['account']}/{thread_id}"
        with PostgresSaver.from_conn_string(DATABASE_URL) as saver:
            saver.setup()
            agent = build_minimal_agent(get_model(), saver, profile, EXECUTOR, cycle_dir)
            result = agent.invoke(
                Command(resume={"decisions": [{"type": "approve"}]}),
                config={"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}},
            )
        hosted._remove_pending(thread_id)
        audit.record("approval_received", thread_id=thread_id)
        if "__interrupt__" not in result:
            audit.record("cycle_completed", thread_id=thread_id)
        return {"thread_id": thread_id, "last_message": result["messages"][-1].content}

    @app.post("/api/approvals/{thread_id}/reject")
    def reject_approval(thread_id: str) -> dict:
        """拒绝发布 → 以 reject 决策恢复执行图（评审 W5）。"""
        pending = [p for p in hosted.list_pending_approvals() if p["thread_id"] == thread_id]
        if not pending:
            raise HTTPException(status_code=404, detail=f"无待审批项: {thread_id}")

        from langgraph.checkpoint.postgres import PostgresSaver

        from zimeiti_api.graph import build_minimal_agent
        from zimeiti_api.models import get_model
        from zimeiti_api.profiles import load_profile
        from zimeiti_api.publisher import PublishExecutor

        if not _THREAD_ID_RE.match(thread_id):
            raise HTTPException(status_code=400, detail="非法 thread_id（允许字母数字._-）")
        profile = load_profile("xhs-main")
        cycle_dir = f"outputs/{profile['account']}/{thread_id}"
        with PostgresSaver.from_conn_string(DATABASE_URL) as saver:
            saver.setup()
            agent = build_minimal_agent(get_model(), saver, profile, EXECUTOR, cycle_dir)
            result = agent.invoke(
                Command(resume={"decisions": [{"type": "reject"}]}),
                config={"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}},
            )
        hosted._remove_pending(thread_id)
        audit.record("approval_rejected", thread_id=thread_id)
        return {"thread_id": thread_id, "last_message": result["messages"][-1].content}

    @app.get("/api/publish-log")
    def publish_log() -> list[dict]:
        return audit.list_entries()

    return app


# uvicorn 入口：zimeiti_api.app:app
app = create_app()
