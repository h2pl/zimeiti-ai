"""热点趋势（content，多平台只读聚合）。"""
from __future__ import annotations

import asyncio
import json
import time
import urllib.request

from fastapi import APIRouter, HTTPException

from ..core.paths import OUTPUTS_DIR

router = APIRouter()

TREND_LABELS = {
    "weibo": "微博",
    "douyin": "抖音",
    "zhihu": "知乎",
    "bilibili": "B站",
    "baidu": "百度",
    "toutiao": "头条",
}
TREND_SOURCES: dict[str, tuple[str, str | None]] = {
    "weibo": ("https://60s.viki.moe/v2/weibo", "https://v2.xxapi.cn/api/weibohot"),
    "douyin": ("https://60s.viki.moe/v2/douyin", "https://v2.xxapi.cn/api/douyinhot"),
    "zhihu": ("https://60s.viki.moe/v2/zhihu", None),
    "bilibili": ("https://60s.viki.moe/v2/bili", "https://v2.xxapi.cn/api/bilibilihot"),
    "baidu": ("https://60s.viki.moe/v2/baidu/hot", "https://v2.xxapi.cn/api/baiduhot"),
    "toutiao": ("https://60s.viki.moe/v2/toutiao", None),
}
_TREND_CACHE: dict[str, tuple[float, list]] = {}


def _http_get_json(url: str, timeout: int = 8):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 Easel"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def _parse_hot(obj: dict) -> list[dict]:
    data = obj.get("data")
    if isinstance(data, dict):
        data = data.get("data") or data.get("list") or []
    out = []
    if isinstance(data, list):
        for it in data:
            if not isinstance(it, dict):
                continue
            title = it.get("title") or it.get("word") or it.get("name") or it.get("keyword")
            if not title:
                continue
            out.append({
                "title": str(title),
                "hot": str(it.get("hot") or it.get("hot_value") or it.get("num") or ""),
                "url": it.get("url") or it.get("link") or it.get("mobil_url") or "",
            })
    return out


def _fetch_platform(pf: str) -> list[dict]:
    primary, backup = TREND_SOURCES.get(pf, (None, None))
    for url in (primary, backup):
        if not url:
            continue
        try:
            items = _parse_hot(_http_get_json(url))
            if items:
                return items
        except Exception:
            continue
    return []


@router.get("/api/trends")
async def api_trends(platforms: str = "weibo,douyin,zhihu", limit: int = 12):
    pfs = [p.strip() for p in platforms.split(",") if p.strip() in TREND_SOURCES]
    now = time.time()
    loop = asyncio.get_event_loop()
    result = []
    for pf in pfs:
        c = _TREND_CACHE.get(pf)
        if c and now - c[0] < 300:
            items = c[1]
        else:
            items = await loop.run_in_executor(None, _fetch_platform, pf)
            if items:
                _TREND_CACHE[pf] = (now, items)
            elif c:
                items = c[1]
        result.append({
            "platform": pf,
            "label": TREND_LABELS.get(pf, pf),
            "items": items[:max(1, min(limit, 30))],
        })
    return {"trends": result, "updated": int(now)}


SCHEDULE_FILE = OUTPUTS_DIR / "_schedule.json"   # 旧文件存储路径（迁 PG 后仅迁移/兼容引用）
SCHEDULE_STATUSES = {"idea", "draft", "scheduled", "published"}
SCHEDULE_KINDS = {"content", "event"}


