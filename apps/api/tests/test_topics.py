"""Task 4.1/4.2 验收：选题卡产出与人工挑选闸门。"""

import pytest

from zimeiti_api.topics import discover_topics, select_topic


def test_discover_produces_at_least_three_cards():
    cards = discover_topics(
        profile={"positioning": "职场干货"},
        hotspot_items=["AI 编程取代初级工程师？", "某大厂裁员传闻"],
        manual_direction="写一篇 AI 工具提效的选题",
    )
    assert len(cards) >= 3
    for c in cards:
        assert {"title", "reason", "direction"} <= set(c.keys())


def test_creation_not_triggered_without_selection():
    # 未挑选（None）时必须报错，创作流程不得启动
    with pytest.raises(ValueError):
        select_topic(None)


def test_selected_topic_object():
    card = {"title": "AI 工具提效指南", "reason": "热点相关", "direction": "教程向"}
    selected = select_topic(card)
    assert selected.title == "AI 工具提效指南"
