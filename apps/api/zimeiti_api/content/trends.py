"""热点趋势（content，多平台只读聚合）。"""

from __future__ import annotations

import asyncio
import json
import time

import httpx
from fastapi import APIRouter

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
    # URL 全部来自模块级 TREND_SOURCES 常量表（固定 https）；raise_for_status
    # 保持与原 urllib 一致：4xx/5xx 抛异常 → 调用方走备用源。
    r = httpx.get(url, headers={"User-Agent": "Mozilla/5.0 Easel"}, timeout=timeout)
    r.raise_for_status()
    return json.loads(r.content.decode("utf-8", "replace"))


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
            out.append(
                {
                    "title": str(title),
                    "hot": str(it.get("hot") or it.get("hot_value") or it.get("num") or ""),
                    "url": it.get("url") or it.get("link") or it.get("mobil_url") or "",
                }
            )
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
        # 有数据 TTL 300s；空结果（源抖动/失效）TTL 60s——死源不该让每次请求都吃重试耗时
        ttl = 300 if (c and c[1]) else 60
        if c and now - c[0] < ttl:
            items = c[1]
        else:
            items = await loop.run_in_executor(None, _fetch_platform, pf)
            if items or c is None:
                _TREND_CACHE[pf] = (now, items)
            elif not items:
                items = c[1]
        result.append(
            {
                "platform": pf,
                "label": TREND_LABELS.get(pf, pf),
                "items": items[: max(1, min(limit, 30))],
            }
        )
    return {"trends": result, "updated": int(now)}


async def _warm_once() -> None:
    """并行抓取全部平台（串行时最慢源 15s+ 会拖长首热窗口）。"""
    loop = asyncio.get_running_loop()
    pfs = list(TREND_SOURCES)
    results = await asyncio.gather(
        *(loop.run_in_executor(None, _fetch_platform, pf) for pf in pfs),
        return_exceptions=True,
    )
    now = time.time()
    for pf, r in zip(pfs, results, strict=False):
        if isinstance(r, list) and r:
            _TREND_CACHE[pf] = (now, r)


async def _trends_warmup_loop():
    """后台保热循环：缓存 TTL 300s，冷了再抓时首个访问者要吃 12s+ 外部抓取
    空窗（实测）。启动立即预抓一轮（并行），此后每 280s 主动刷新。"""
    while True:
        try:
            await _warm_once()
        except Exception:  # noqa: BLE001  外部源抖动不影响服务
            pass
        await asyncio.sleep(280)


_warmup_task: asyncio.Task | None = None


def start_trends_warmup() -> None:
    """lifespan 调用：启动保热后台任务（持强引用防 GC）。"""
    global _warmup_task
    if _warmup_task is None or _warmup_task.done():
        _warmup_task = asyncio.get_running_loop().create_task(_trends_warmup_loop())


SCHEDULE_FILE = OUTPUTS_DIR / "_schedule.json"  # 旧文件存储路径（迁 PG 后仅迁移/兼容引用）
SCHEDULE_STATUSES = {"idea", "draft", "scheduled", "published"}
SCHEDULE_KINDS = {"content", "event"}
