"""会话用量统计 API 端点（model-resilience-cron）。"""

from __future__ import annotations

from fastapi import APIRouter

from zimeiti_harness import usage

router = APIRouter()


@router.get("/api/usage")
async def get_usage(session_key: str | None = None, days: int = 30):
    return usage.summary(session_key=session_key, days=days)
