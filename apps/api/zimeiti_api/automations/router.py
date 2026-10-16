"""定时自动化 API 端点（model-resilience-cron）。"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from . import scheduler, store

router = APIRouter()


class AutoIn(BaseModel):
    name: str
    kind: str = "case"  # case / prompt
    schedule: str  # HH:MM 每日时刻
    payload: str = ""


@router.get("/api/automations")
async def list_automations():
    return {"automations": store.list_all()}


@router.post("/api/automations")
async def create_automation(body: AutoIn):
    if body.kind not in ("case", "prompt"):
        return {"error": "kind 必须是 case 或 prompt"}
    next_run = scheduler.validate_schedule(body.schedule)
    if not next_run:
        return {"error": "schedule 只支持每日时刻 HH:MM（cron 表达式后续扩展）"}
    if body.kind == "prompt" and not body.payload.strip():
        return {"error": "prompt 类任务必须带 payload 指令文本"}
    aid = store.create(
        body.name.strip(), body.kind, body.schedule.strip(), body.payload.strip(), next_run
    )
    return {"id": aid, "next_run": next_run}


@router.patch("/api/automations/{auto_id}")
async def update_automation(auto_id: str, body: dict):
    fields = {k: v for k, v in body.items() if k in ("name", "enabled", "schedule", "payload")}
    if "schedule" in fields:
        nxt = scheduler.validate_schedule(str(fields["schedule"]))
        if not nxt:
            return {"error": "schedule 非法"}
        fields["next_run"] = nxt
    store.update(auto_id, **fields)
    return {"ok": True}


@router.delete("/api/automations/{auto_id}")
async def delete_automation(auto_id: str):
    store.delete(auto_id)
    return {"ok": True}


@router.get("/api/automations/runs")
async def list_runs(auto_id: str | None = None):
    return {"runs": store.list_runs(auto_id)}


@router.post("/api/automations/{auto_id}/run-now")
async def run_now(auto_id: str):
    """手动触发一次（不改变排定计划）——后台执行，立即返回（case 可能跑几分钟）。"""
    import asyncio

    items = [a for a in store.list_all() if a["id"] == auto_id]
    if not items:
        return {"error": "任务不存在"}
    asyncio.get_running_loop().create_task(
        scheduler._run_one(items[0])  # noqa: SLF001  手动触发复用执行链路
    )
    return {"ok": True, "started": True}
