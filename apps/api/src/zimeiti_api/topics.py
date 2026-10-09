"""选题辅助（Task 4.1/4.2）：选题卡产出 + 人工挑选闸门。

T2 决策：信息源 = 公益热搜 API + 用户手动方向 双通道；
MVP 的 API 拉取允许失败降级为仅手动方向（无 SLA，已记录风险）。
"""

import logging
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)


@dataclass
class SelectedTopic:
    """人工挑选后的选题（创作流程的唯一合法入口类型）。"""

    title: str
    reason: str
    direction: str


def discover_topics(
    profile: dict[str, Any],
    hotspot_items: list[str] | None = None,
    manual_direction: str | None = None,
    hot_api_url: str | None = None,
) -> list[dict[str, str]]:
    """产出 ≥3 张选题卡：{title, reason, direction}。

    由 agent 在选题环节调用；信息源 = 热点条目（可来自热搜 API 或用户）+ 手动方向。
    """
    if hot_api_url:
        try:
            resp = httpx.get(hot_api_url, timeout=10)
            resp.raise_for_status()
            hotspot_items = (hotspot_items or []) + [
                item.get("title", "") for item in resp.json()[:10] if isinstance(item, dict)
            ]
        except Exception as exc:
            # 降级是有意设计：公益源无 SLA，失败不影响手动方向（design T2）
            logger.debug("热搜源拉取失败，降级为手动方向: %s", exc)
    hotspot_items = [h for h in (hotspot_items or []) if h]

    positioning = profile.get("positioning", "")
    cards: list[dict[str, str]] = []
    if manual_direction:
        cards.append(
            {
                "title": manual_direction,
                "reason": "用户指定方向，优先级最高",
                "direction": f"围绕「{manual_direction}」展开，贴合「{positioning}」定位",
            }
        )
    for h in hotspot_items:
        cards.append(
            {
                "title": h,
                "reason": "当前热点，蹭流量窗口",
                "direction": f"从「{positioning}」视角解读「{h}」，给出可执行建议",
            }
        )
    if len(cards) < 3:
        for i in range(len(cards), 3):
            cards.append(
                {
                    "title": f"备选选题 {i + 1}（基于定位延展）",
                    "reason": "信息源不足时的兜底选题",
                    "direction": f"围绕「{positioning}」的核心痛点自拟角度",
                }
            )
    return cards[:5]


def select_topic(card: dict[str, str] | None) -> SelectedTopic:
    """人工挑选闸门：未挑选（None）MUST 抛错，创作流程不得启动。"""
    if not card or not card.get("title"):
        raise ValueError("未选择选题：创作流程不允许在无人工挑选时启动")
    return SelectedTopic(
        title=card["title"], reason=card.get("reason", ""), direction=card.get("direction", "")
    )
