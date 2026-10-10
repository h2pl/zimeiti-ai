"""单篇复盘验收（P1⑨，Easel skill-content-postmortem 对标）。"""

import pytest

from zimeiti_api.operations import postmortem


class TestPostmortem:
    @pytest.fixture
    def seeded(self, metrics_db):
        db = metrics_db
        for i, (title, vals) in enumerate(
            [("爆文", [100, 400, 500]), ("扑文", [10, 12, 12]), ("新文", [30])]
        ):
            db.record_event(
                platform="xhs-main",
                title=title,
                source_folder=f"f{i}",
                publish_date=f"2026-10-0{i + 1}",
                profile="xhs-main",
                topic_direction="AI 提效",
            )
            eid = [e for e in db.list_events("xhs-main") if e["title"] == title][0]["id"]
            for j, v in enumerate(vals):
                db.record_snapshot(
                    eid,
                    "xhs-main",
                    "read",
                    v,
                    source="creator-center",
                    captured_at=f"2026-10-09T10:0{j}:00",
                )
        return db

    def test_note_evidence(self, seeded):
        ev = postmortem.note_evidence(seeded, "xhs-main", "爆文")
        assert ev["read_series"] == [100.0, 400.0, 500.0]
        assert ev["lifecycle"] == "稳增型"  # 终值/首值 = 5 ≥ 1.5
        assert ev["peer_mean"] is not None and ev["vs_peers"] is not None

    def test_note_not_found(self, seeded):
        assert postmortem.note_evidence(seeded, "xhs-main", "不存在") is None

    def test_render_note_has_disclaimer(self, seeded):
        md = postmortem.render_note(postmortem.note_evidence(seeded, "xhs-main", "扑文"))
        assert "关联性不等于因果性" in md

    def test_formula_ranking(self, seeded):
        ev = postmortem.top_formula(seeded, "xhs-main")
        assert ev["top"][0]["title"] == "爆文"
        assert ev["top"][0]["read_latest"] == 500.0
        md = postmortem.render_formula(ev)
        assert "样本 3 < 5" in md  # 可信度提示

    def test_formula_insufficient_sample_note(self, seeded):
        ev = postmortem.top_formula(seeded, "xhs-main")
        assert ev["sample"] < 5  # 提示语覆盖在 render 中


# ── DNA 载体（P1⑩） ────────────────────────────────────────────────
