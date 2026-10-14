"""排期 schedule（content，PG 存储见 core.pg）。

context 端点把 PG 数据投影临时 JSON 喂 vendor 脚本 calendar_ops。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..core import pg
from ..core.paths import OUTPUTS_DIR, PROJECT_ROOT, SHARED_SCRIPTS
from ..core.settings import _proxy_env
from .trends import SCHEDULE_KINDS, SCHEDULE_STATUSES

router = APIRouter()

def _read_schedule() -> list[dict]:
    """排期列表（PG，pg-data-layer 变更；字段与文件版 JSON 一致）。"""
    return pg.schedule_list()


def _write_schedule(items: list[dict]) -> None:
    """整表替换（read-modify-write 调用方的 PG 等价，事务内 DELETE+INSERT）。"""
    pg.schedule_replace_all(items)


class ScheduleItem(BaseModel):
    title: str
    date: str
    platform: str = ""
    time: str = ""
    status: str = "idea"
    note: str = ""
    kind: str = "content"          # content（内容/发布）| event（平台活动/节日/特殊日期）
    url: str = ""                  # 已发布内容链接（可选）
    source: str = "manual"         # manual | publish-page | chat | scheduler
    event_type: str = ""           # event 专属：节日/电商/平台活动/行业
    end_date: str = ""             # event 专属：活动区间结束日


@router.get("/api/schedule")
async def api_schedule_list():
    return _read_schedule()


@router.post("/api/schedule")
async def api_schedule_create(req: ScheduleItem):
    items = _read_schedule()
    kind = req.kind if req.kind in SCHEDULE_KINDS else "content"
    st = req.status if req.status in SCHEDULE_STATUSES else "idea"
    item = {
        "id": uuid.uuid4().hex[:12],
        "title": req.title.strip() or ("未命名活动" if kind == "event" else "未命名"),
        "date": req.date,
        "platform": req.platform,
        "time": req.time,
        "status": st,
        "note": req.note,
        "kind": kind,
        "url": req.url,
        "source": req.source if req.source in {"manual", "publish-page", "chat", "scheduler"} else "manual",
        "event_type": req.event_type,
        "end_date": req.end_date,
    }
    items.append(item)
    _write_schedule(items)
    return item


@router.put("/api/schedule/{sid}")
async def api_schedule_update(sid: str, req: ScheduleItem):
    items = _read_schedule()
    for it in items:
        if it.get("id") == sid:
            kind = req.kind if req.kind in SCHEDULE_KINDS else it.get("kind", "content")
            it.update({
                "title": req.title.strip() or it.get("title", "未命名"),
                "date": req.date,
                "platform": req.platform,
                "time": req.time,
                "status": req.status if req.status in SCHEDULE_STATUSES else it.get("status", "idea"),
                "note": req.note,
                "kind": kind,
                "url": req.url,
                "event_type": req.event_type,
                "end_date": req.end_date,
            })
            _write_schedule(items)
            return it
    raise HTTPException(404, "排期不存在")


@router.delete("/api/schedule/{sid}")
async def api_schedule_delete(sid: str):
    items = _read_schedule()
    new = [it for it in items if it.get("id") != sid]
    if len(new) == len(items):
        raise HTTPException(404, "排期不存在")
    _write_schedule(new)
    return {"ok": True, "deleted": sid}


@router.get("/api/schedule/context")
async def api_schedule_context(days: int = 14):
    """规划摘要（发布节奏/断更缺口 + 待发排期 + 临近节点 + 建议）——薄封装 calendar_ops，
    前端页头「近期节点/建议」与 Agent 读回共用同一逻辑。失败返回空摘要不抛错。

    pg-data-layer 适配：排期已迁 PG，而 calendar_ops 是 vendor 脚本只认
    `--data <json 文件>`（skills/shared/scripts，与上游一字不差不改动）。
    此处把 PG 数据投影成临时 JSON 喂它，用完即删——适配层，非第二份存储。
    """
    items = _read_schedule()
    tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    try:
        json.dump(items, tmp, ensure_ascii=False)
        tmp.close()
        cmd = [sys.executable, str(SHARED_SCRIPTS / "calendar_ops.py"),
               "--data", tmp.name, "context", "--days", str(max(1, min(days, 90)))]
        proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT), env=_proxy_env(),
                              capture_output=True, text=True, timeout=20)
        return json.loads(proc.stdout) if proc.returncode == 0 and proc.stdout.strip() else {}
    except Exception:
        return {}
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


IDEAS_FILE = OUTPUTS_DIR / "_ideas.json"   # 旧文件存储路径（迁 PG 后仅迁移/兼容引用）
IDEA_STATUSES = {"pending", "doing", "done"}


