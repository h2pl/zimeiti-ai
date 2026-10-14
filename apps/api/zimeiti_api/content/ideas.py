"""选题 ideas（content，PG 存储见 core.pg）。"""
from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..core import pg
from .schedule import IDEA_STATUSES

router = APIRouter()

def _read_ideas() -> list[dict]:
    """选题列表（PG，pg-data-layer 变更；字段与文件版 JSON 一致，最新在前）。"""
    return pg.ideas_list()


def _write_ideas(items: list[dict]) -> None:
    """整表替换（read-modify-write 调用方的 PG 等价，反序插入保「最新在前」）。"""
    pg.ideas_replace_all(items)


class IdeaItem(BaseModel):
    title: str
    note: str = ""
    source: str = ""
    status: str = "pending"


@router.get("/api/ideas")
async def api_ideas_list():
    return _read_ideas()


@router.post("/api/ideas")
async def api_ideas_create(req: IdeaItem):
    items = _read_ideas()
    st = req.status if req.status in IDEA_STATUSES else "pending"
    item = {
        "id": uuid.uuid4().hex[:12],
        "title": req.title.strip() or "未命名选题",
        "note": req.note,
        "source": req.source,
        "status": st,
        "created": int(time.time()),
    }
    items.insert(0, item)
    _write_ideas(items)
    return item


@router.put("/api/ideas/{iid}")
async def api_ideas_update(iid: str, req: IdeaItem):
    items = _read_ideas()
    for it in items:
        if it.get("id") == iid:
            it.update({
                "title": req.title.strip() or it.get("title", "未命名选题"),
                "note": req.note,
                "source": req.source,
                "status": req.status if req.status in IDEA_STATUSES else it.get("status", "pending"),
            })
            _write_ideas(items)
            return it
    raise HTTPException(404, "选题不存在")


@router.delete("/api/ideas/{iid}")
async def api_ideas_delete(iid: str):
    items = _read_ideas()
    new = [it for it in items if it.get("id") != iid]
    if len(new) == len(items):
        raise HTTPException(404, "选题不存在")
    _write_ideas(new)
    return {"ok": True, "deleted": iid}
