"""autonomous-feedback：发布数据回流校准下一轮选题。

覆盖规格三条：
- 发布事实汇总（有事实 / 无事实降级 / 坏 JSON 容错）
- 校准信号只注入 discover 步（其余步骤不含），且只陈述事实不虚构
- 校准结论归档 outputs/_feedback/<date>.md + /api/feedback 可查
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from zimeiti_autonomous import feedback as fb
from zimeiti_autonomous import flows as fl
from zimeiti_autonomous import runner as rn


@pytest.fixture(autouse=True)
def _reset_entry():
    rn.set_agent_entry(None)
    yield
    rn.set_agent_entry(None)


def _seed_analytics(root: Path, platform: str, day: str, items: list[dict]) -> Path:
    d = root / "_analytics" / platform
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{day}.json"
    p.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    return p


# ── 1. 汇总 ────────────────────────────────────────────────────────────────
def test_collect_published_with_facts(tmp_path, monkeypatch):
    _seed_analytics(
        tmp_path,
        "wechat",
        "2026-10-18",
        [
            {"media_id": "m1", "title": "选题 A", "created": "2026-10-18T09:00:00"},
            {"media_id": "m2", "title": "选题 B", "created": "2026-10-18T10:00:00"},
        ],
    )
    monkeypatch.setattr(fb, "_ANALYTICS_DIR", tmp_path / "_analytics")
    items = fb.collect_published(days=14)
    assert len(items) == 2
    assert {i["platform"] for i in items} == {"wechat"}
    assert any(i.get("title") == "选题 A" for i in items)


def test_collect_published_empty_is_not_error(tmp_path, monkeypatch):
    """源目录不存在 → 空列表，不抛异常（降级而非崩溃）。"""
    monkeypatch.setattr(fb, "_ANALYTICS_DIR", tmp_path / "nope")
    assert fb.collect_published(days=14) == []


def test_collect_published_tolerates_bad_json(tmp_path, monkeypatch):
    """坏 JSON 跳过并计数，不影响其余文件（容错优先）。"""
    _seed_analytics(tmp_path, "wechat", "2026-10-18", [{"media_id": "m1", "title": "好记录"}])
    bad = tmp_path / "_analytics" / "wechat" / "2026-10-17.json"
    bad.write_text("{ not json", encoding="utf-8")
    monkeypatch.setattr(fb, "_ANALYTICS_DIR", tmp_path / "_analytics")
    items = fb.collect_published(days=14)
    assert len(items) == 1  # 坏文件被跳过，好记录仍在


# ── 2. 校准信号 ────────────────────────────────────────────────────────────
def test_build_calibration_states_facts_only():
    items = [
        {"platform": "wechat", "title": "选题 A", "created": "2026-10-18T09:00:00"},
        {"platform": "wechat", "title": "选题 B", "created": "2026-10-17T09:00:00"},
    ]
    text = fb.build_calibration(items)
    assert "wechat" in text and "2" in text
    # 不得虚构表现数值（无阅读数/CTR 等字段来源）
    for banned in ("阅读数", "CTR", "点赞数", "10 万+"):
        assert banned not in text


def test_build_calibration_empty_says_so():
    text = fb.build_calibration([])
    assert "暂无发布记录" in text


def test_context_for_discover_archives(tmp_path, monkeypatch):
    _seed_analytics(tmp_path, "wechat", "2026-10-18", [{"media_id": "m1", "title": "选题 A"}])
    monkeypatch.setattr(fb, "_ANALYTICS_DIR", tmp_path / "_analytics")
    monkeypatch.setattr(fb, "_FEEDBACK_DIR", tmp_path / "_feedback")
    text = fb.context_for_discover()
    assert text
    files = list((tmp_path / "_feedback").glob("*.md"))
    assert len(files) == 1


# ── 3. 仅 discover 注入 ─────────────────────────────────────────────────────
def test_feedback_only_in_discover_prompt():
    p_discover = fl.build_step_prompt("discover", {}, "", feedback="校准段XYZ")
    p_produce = fl.build_step_prompt("produce", {}, "", feedback="校准段XYZ")
    assert "校准段XYZ" in p_discover
    assert "校准段XYZ" not in p_produce


def test_runner_injects_feedback_into_discover(tmp_path, monkeypatch):
    """实测链路：discover 步收到校准段，produce 步没有。"""
    _seed_analytics(tmp_path, "wechat", "2026-10-18", [{"media_id": "m1", "title": "选题 A"}])
    monkeypatch.setattr(fb, "_ANALYTICS_DIR", tmp_path / "_analytics")
    monkeypatch.setattr(fb, "_FEEDBACK_DIR", tmp_path / "_feedback")

    seen: dict[str, str] = {}

    def entry(sk: str, msg: str) -> str:
        seen[sk.split("-")[-1]] = msg
        return "产出"

    rn.set_agent_entry(entry)
    res = rn.run_flow(
        flow_id="f-fb",
        name="回流流程",
        steps=["discover", "produce"],
        config={},
        archive_root=tmp_path,
    )
    assert res["status"] == "done"
    assert "wechat" in seen["discover"] and "暂无发布记录" not in seen["discover"]
    assert "wechat" not in seen["produce"]


def test_runner_feedback_can_be_disabled(tmp_path, monkeypatch):
    _seed_analytics(tmp_path, "wechat", "2026-10-18", [{"media_id": "m1", "title": "选题 A"}])
    monkeypatch.setattr(fb, "_ANALYTICS_DIR", tmp_path / "_analytics")
    monkeypatch.setattr(fb, "_FEEDBACK_DIR", tmp_path / "_feedback")

    seen: dict[str, str] = {}
    rn.set_agent_entry(lambda sk, msg: (seen.__setitem__("discover", msg), "产出")[1])
    rn.run_flow(
        flow_id="f-off",
        name="关闭回流",
        steps=["discover"],
        config={"feedback": False},
        archive_root=tmp_path,
    )
    assert "wechat" not in seen.get("discover", "")
