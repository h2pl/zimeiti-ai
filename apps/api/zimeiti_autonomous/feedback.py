"""发布数据回流（autonomous-feedback D1/D2）：汇总发布事实 → 校准信号 → 注入发现层。

诚实优先：没有表现数据就只陈述「发过什么」，绝不虚构阅读数/CTR 等数值
（项目既定决策：ops_analytics 只落发布事实，不做平台数据拉取）。
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta

from zimeiti_api.core.paths import OUTPUTS_DIR

_ANALYTICS_DIR = OUTPUTS_DIR / "_analytics"
_FEEDBACK_DIR = OUTPUTS_DIR / "_feedback"

_MAX_ITEMS = 200
_SUMMARY_LIMIT = 800


def _parse_day(name: str) -> date | None:
    try:
        return datetime.strptime(name[:10], "%Y-%m-%d").date()
    except Exception:  # noqa: BLE001   文件名非日期格式则忽略
        return None


def collect_published(days: int = 14) -> list[dict]:
    """汇总发布事实：读 outputs/_analytics/<platform>/<date>.json（近 days 天）。

    源目录缺失 / 坏 JSON / 非日期文件名 → 跳过（容错优先，绝不抛给调用方）。
    """
    if not _ANALYTICS_DIR.is_dir():
        return []
    cutoff = date.today() - timedelta(days=max(0, int(days)))
    items: list[dict] = []
    for pf in sorted(_ANALYTICS_DIR.iterdir()):
        if not pf.is_dir() or not (pf / "").is_dir():
            continue
        platform = pf.name
        for f in sorted(pf.glob("*.json")):
            d = _parse_day(f.name)
            if d is None or d < cutoff:
                continue
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001   坏文件跳过，不拖垮整次汇总
                continue
            rows = data if isinstance(data, list) else [data]
            for r in rows:
                if not isinstance(r, dict):
                    continue
                item = dict(r)
                item.setdefault("platform", platform)
                item.setdefault("date", d.isoformat())
                items.append(item)
                if len(items) >= _MAX_ITEMS:
                    return items
    return items


def build_calibration(items: list[dict]) -> str:
    """事实 → 校准信号（只陈述事实与缺口提示，不含任何虚构表现数值）。"""
    if not items:
        return "暂无发布记录——本轮按常规发现流程进行，无需规避重复。"

    by_platform: dict[str, int] = {}
    titles: list[str] = []
    for it in items:
        p = str(it.get("platform") or "unknown")
        by_platform[p] = by_platform.get(p, 0) + 1
        t = str(it.get("title") or it.get("media_id") or "").strip()
        if t:
            titles.append(t)

    lines = [
        f"近期已发布 {len(items)} 条（平台分布："
        + "、".join(f"{p} {n} 条" for p, n in sorted(by_platform.items()))
        + "）。"
    ]
    if titles:
        recent = titles[-5:]
        lines.append("最近发布：" + "；".join(recent))
        lines.append("缺口提示：优先补充与上述不同的角度/主题，避免重复选题。")
    else:
        lines.append("缺口提示：发布记录缺少标题，按平台与条数规避重复即可。")
    return "\n".join(lines)[:_SUMMARY_LIMIT]


def context_for_discover(days: int = 14) -> str:
    """生成校准信号并归档到 outputs/_feedback/<date>.md（人可读）。"""
    items = collect_published(days=days)
    text = build_calibration(items)
    try:
        _FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
        (_FEEDBACK_DIR / f"{date.today().isoformat()}.md").write_text(
            f"# 选题校准信号（{date.today().isoformat()}）\n\n{text}\n", encoding="utf-8"
        )
    except Exception:  # noqa: BLE001   归档失败不影响注入
        pass
    return text


def latest(days: int = 14) -> dict:
    """最近一次校准信号（供 /api/feedback）。"""
    items = collect_published(days=days)
    return {
        "date": date.today().isoformat(),
        "published_count": len(items),
        "calibration": build_calibration(items),
        "has_facts": bool(items),
    }
