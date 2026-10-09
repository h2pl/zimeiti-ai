"""FastAPI 应用（Task 1.4 + 7.2：审批 API）。"""

from fastapi import FastAPI, HTTPException
from langgraph.types import Command

from zimeiti_api import audit, hosted
from zimeiti_api.checkpoints import DATABASE_URL


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
        """人工确认发布 → 同步 checkpointer resume 执行图。"""
        pending = [p for p in hosted.list_pending_approvals() if p["thread_id"] == thread_id]
        if not pending:
            raise HTTPException(status_code=404, detail=f"无待审批项: {thread_id}")

        # 同步 saver：FastAPI sync 端点内零 async loop 问题；
        # 中断态由 async saver 写入，表结构相同，sync saver 可读。
        from langgraph.checkpoint.postgres import PostgresSaver

        from zimeiti_api.models import get_model

        with PostgresSaver.from_conn_string(DATABASE_URL) as saver:
            saver.setup()
            from zimeiti_api.graph import build_minimal_agent_sync
            agent = build_minimal_agent_sync(get_model(), checkpointer=saver)
            result = agent.invoke(
                Command(resume={"decisions": [{"type": "approve"}]}),
                config={"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}},
            )
        hosted._remove_pending(thread_id)
        audit.record("approval_received", thread_id=thread_id)
        audit.record("cycle_completed", thread_id=thread_id)
        return {"thread_id": thread_id, "last_message": result["messages"][-1].content}

    @app.get("/api/publish-log")
    def publish_log() -> list[dict]:
        return audit.list_entries()

    return app
