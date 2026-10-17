"""运营流程 API（autonomous-flow）：/api/flows CRUD + 立即执行。

本变更只交付后端能力；前端看板与告警归 autonomous-observability。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from . import feedback as fb
from . import flows as fl
from . import guardrails as gr
from . import runner as rn
from . import store as st

router = APIRouter()


class FlowIn(BaseModel):
    name: str = Field(default="", description="流程名")
    steps: list[str] = Field(default_factory=list, description="五层步骤有序子集")
    schedule: str = Field(default="", description="cron 五段式 或 HH:MM")
    config: dict[str, Any] = Field(default_factory=dict, description="topic/platform/draft_only 等")


@router.get("/api/flows")
def list_flows() -> dict:
    try:
        return {"flows": st.list_flows()}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"流程存储不可用：{e}") from e


@router.post("/api/flows")
def create_flow(body: FlowIn) -> dict:
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="流程名不能为空")
    try:
        steps = fl.validate_steps(body.steps)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    try:
        fid = st.create_flow(body.name.strip(), steps, body.schedule.strip(), body.config)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"流程存储不可用：{e}") from e
    return {"id": fid}


@router.get("/api/flows/{flow_id}")
def get_flow(flow_id: str) -> dict:
    f = st.get_flow(flow_id)
    if not f:
        raise HTTPException(status_code=404, detail="流程不存在")
    return f


@router.delete("/api/flows/{flow_id}")
def delete_flow(flow_id: str) -> dict:
    st.delete_flow(flow_id)
    return {"ok": True}


@router.post("/api/flows/{flow_id}/run")
def run_flow(flow_id: str) -> dict:
    """立即执行一次（同步返回执行结果；长链路耗时与对话链路同量级）。"""
    f = st.get_flow(flow_id)
    if not f:
        raise HTTPException(status_code=404, detail="流程不存在")
    try:
        res = rn.run_flow(
            flow_id=flow_id,
            name=f["name"],
            steps=f["steps"],
            config=f.get("config") or {},
            archive_root=None,  # 由调用方（scheduler）指定归档根；此处仅试跑
        )
    except rn.EntryNotInjected as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e)[:300]) from e
    st.save_run(flow_id, res)
    return res


@router.get("/api/autonomous/status")
def autonomous_status() -> dict:
    """护栏状态（autonomous-guardrails）：熔断态（被停用的流程）+ 当日预算用量。

    用量由组装层注入（本包不 import harness）；未注入时如实标注 unknown。
    """
    return gr.status()


@router.get("/api/feedback")
def get_feedback(days: int = 14) -> dict:
    """最近一次选题校准信号（autonomous-feedback）：发布事实汇总与缺口提示。

    无发布记录时如实返回「暂无发布记录」，不虚构任何表现数值。
    """
    try:
        return fb.latest(days=days)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"校准信号不可用：{e}") from e


@router.get("/api/flows/steps/catalog")
def steps_catalog() -> dict:
    """步骤枚举（供前端勾选）：值 + 中文名 + 层序。"""
    return {"steps": [{"value": s, "label": fl.STEP_LABELS[s]} for s in fl.STEPS]}
