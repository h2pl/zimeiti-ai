"""选题看板/内容日历验收（P1⑪，Easel IdeasPage/CalendarPage 对标）。"""

import json

import pytest

from zimeiti_api.operations import kanban


class TestKanban:
    def test_collect_and_move(self, tmp_path, monkeypatch):
        outputs = tmp_path / "outputs"
        cycle = outputs / "xhs-main" / "cycle-1"
        cycle.mkdir(parents=True)
        (cycle / "state.json").write_text(
            json.dumps(
                {
                    "cards": [
                        {"title": "选题A", "reason": "r", "direction": "d"},
                        {"title": "选题B", "reason": "r", "direction": "d"},
                    ]
                }
            ),
            encoding="utf-8",
        )
        kb_file = tmp_path / "kb.json"
        monkeypatch.setattr(kanban, "_kanban_path", lambda: kb_file)

        board = kanban.collect_cards(outputs)
        assert [c["title"] for c in board["待做"]] == ["选题A", "选题B"]

        kanban.set_status("选题A", "进行中")
        board = kanban.collect_cards(outputs)
        assert [c["title"] for c in board["进行中"]] == ["选题A"]
        assert [c["title"] for c in board["待做"]] == ["选题B"]

    def test_invalid_status_rejected(self, tmp_path, monkeypatch):
        monkeypatch.setattr(kanban, "_kanban_path", lambda: tmp_path / "kb.json")
        with pytest.raises(ValueError):
            kanban.set_status("t", "乱写")

    def test_collect_dedup_and_corrupt_state(self, tmp_path, monkeypatch):
        outputs = tmp_path / "outputs"
        for name in ("cycle-1", "cycle-2"):
            d = outputs / "xhs-main" / name
            d.mkdir(parents=True)
        (outputs / "xhs-main" / "cycle-1" / "state.json").write_text(
            json.dumps({"cards": [{"title": "T", "reason": "old", "direction": "d"}]}),
            encoding="utf-8",
        )
        (outputs / "xhs-main" / "cycle-2" / "state.json").write_text("{broken", encoding="utf-8")
        board = kanban.collect_cards(outputs)
        assert len(board["待做"]) == 1 and board["待做"][0]["reason"] == "old"

    def test_calendar_events_readonly(self):
        class FakeDB:
            def list_events(self):
                return [
                    {
                        "publish_date": "2026-10-10",
                        "title": "B",
                        "platform": "gzh-main",
                        "status": "ok",
                    },
                    {
                        "publish_date": "2026-10-09",
                        "title": "A",
                        "platform": "xhs-main",
                        "status": "ok",
                    },
                ]

        ev = kanban.calendar_events(FakeDB())
        assert ev[0]["date"] == "2026-10-10"  # 按日期倒序
        assert set(ev[0]) == {"date", "title", "platform", "status"}


# ── ask_human 问题卡片端到端（P1⑧） ────────────────────────────────
