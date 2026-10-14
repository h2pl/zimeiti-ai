"""服务状态（runtime）：模型配置 + 技能 + 画像概览。"""

from __future__ import annotations

from fastapi import APIRouter

from ..content.personas import list_personas
from ..content.skills import get_skills
from . import agent_runtime as _agent_runtime

router = APIRouter()


@router.get("/api/status")
async def api_status():
    return {
        "gateway": _agent_runtime.model_configured(),
        "skills": get_skills(),
        "personas": list_personas(),
    }
