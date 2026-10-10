"""FastAPI 应用（Task 1.4 + 7.2：审批 API）。"""

import re
from pathlib import Path

from fastapi import FastAPI, HTTPException
from langgraph.types import Command

from zimeiti_api import audit, hosted
from zimeiti_api.checkpoints import DATABASE_URL
from zimeiti_api.config import OUTPUTS_DIR
from zimeiti_api.publisher import PublishExecutor

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
        """
        if "__interrupt__" in result:
            hosted._add_pending(thread_id, instruction, account=account)
            audit.record("awaiting_approval", thread_id=thread_id)

    def _resume_thread(thread_id: str, decision: str, account: str) -> dict:
        """按 pending 记录的账号恢复执行图（修复评审遗留：profile 不再硬编码 xhs-main）。

        同步 saver：FastAPI sync 端点内零 async loop 问题；
        中断态由 async saver 写入，表结构相同，sync saver 可读。
        """
        from langgraph.checkpoint.postgres import PostgresSaver

        from zimeiti_api.graph import build_minimal_agent
        from zimeiti_api.models import get_model
        from zimeiti_api.profiles import load_profile

        if not _THREAD_ID_RE.match(thread_id):
            raise HTTPException(status_code=400, detail="非法 thread_id（允许字母数字._-）")
        profile = load_profile(account)
        cycle_dir = str(Path(OUTPUTS_DIR) / profile["account"] / thread_id)
        with PostgresSaver.from_conn_string(DATABASE_URL) as saver:
            saver.setup()
            agent = build_minimal_agent(get_model(), saver, profile, EXECUTOR, cycle_dir)
            return agent.invoke(
                Command(resume={"decisions": [{"type": decision}]}),
                config={"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}},
            )

    @app.post("/api/approvals/{thread_id}/confirm")
    def confirm_approval(thread_id: str) -> dict:
        """人工确认发布 → 同步 checkpointer resume 执行图（工厂接线，评审 C1-C4）。"""
        pending = [p for p in hosted.list_pending_approvals() if p["thread_id"] == thread_id]
        if not pending:
            raise HTTPException(status_code=404, detail=f"无待审批项: {thread_id}")
        # account 随中断记录；修复前遗留的旧记录无此字段，回退 xhs-main 保持原行为
        account = pending[0].get("account") or "xhs-main"
        instruction = pending[0].get("instruction", "")
        result = _resume_thread(thread_id, "approve", account)
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
        result = _resume_thread(thread_id, "reject", account)
        hosted._remove_pending(thread_id)
        audit.record("approval_rejected", thread_id=thread_id)
        _rearm_pending_if_interrupted(thread_id, result, account, instruction)
        return {"thread_id": thread_id, "last_message": result["messages"][-1].content}

    @app.get("/api/publish-log")
    def publish_log() -> list[dict]:
        return audit.list_entries()

    return app


# uvicorn 入口：zimeiti_api.app:app
app = create_app()
