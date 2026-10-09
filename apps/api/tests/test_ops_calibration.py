"""content-strategy-calibration 验收：策略校准证据引擎与评估报告。

设计来源：xiaobei content-calibrator（四条评估铁律：趋势优先/脚本只给证据/
先排混杂再归因/不自动改策略）+ Easel publish-analytics（基线归一化/确定性聚合）。
"""

from pathlib import Path

import pytest


@pytest.fixture
def seeded_db(metrics_db):
    """已回收真实数据的库：事件（跨 2 天）+ 账号级快照（粉丝数两条，均值 159）。"""
    db = metrics_db
    db.record_event(
        platform="xhs-main",
        title="笔记一",
        source_folder="f1",
        publish_date="2026-10-01",
        profile="xhs-main",
        topic_direction="AI 提效",
    )
    db.record_event(
        platform="xhs-main",
        title="笔记二",
        source_folder="f2",
        publish_date="2026-10-03",
        profile="xhs-main",
        topic_direction="AI 提效",
    )
    eid1, eid2 = [e["id"] for e in db.list_events("xhs-main")]
    db.record_snapshot(eid1, "xhs-main", "read", 100, source="creator-center")
    db.record_snapshot(eid2, "xhs-main", "read", 300, source="creator-center")
    db.record_snapshot(None, "xhs-main", "粉丝数", 106, source="creator-center")
    db.record_snapshot(None, "xhs-main", "粉丝数", 212, source="creator-center")
    return db


class TestEvidence:
    def test_baseline_normalization(self, seeded_db):
        from zimeiti_api.ops_calibration import build_evidence

        ev = build_evidence(seeded_db, platform="xhs-main", profile="xhs-main")
        # 基线归一化：最新值 / 历史均值（212 / 159 ≈ 1.333）
        assert ev["baseline"]["粉丝数"]["latest"] == 212
        assert ev["baseline"]["粉丝数"]["mean"] == 159
        assert ev["baseline"]["粉丝数"]["normalized"] == pytest.approx(212 / 159, rel=1e-3)

    def test_trend_and_lifecycle_distribution(self, seeded_db):
        from zimeiti_api.ops_calibration import build_evidence

        ev = build_evidence(seeded_db, platform="xhs-main", profile="xhs-main")
        assert ev["trend"]["read"]["delta"] == 200
        dist = ev["lifecycle_distribution"]
        assert sum(dist.values()) == 2
        assert set(dist) <= {"速爆型", "稳增型", "长尾型", "数据不足"}

    def test_publish_rhythm(self, seeded_db):
        from zimeiti_api.ops_calibration import build_evidence

        ev = build_evidence(seeded_db, platform="xhs-main", profile="xhs-main")
        assert sum(ev["rhythm"].values()) == 2  # 按星期分布计数

    def test_readonly(self, seeded_db):
        from zimeiti_api.ops_calibration import build_evidence

        before = seeded_db.list_snapshots("xhs-main")
        build_evidence(seeded_db, platform="xhs-main", profile="xhs-main")
        assert seeded_db.list_snapshots("xhs-main") == before


class TestEvalReport:
    def test_report_structure_and_downgrade(self, seeded_db, tmp_path):
        """成熟记录不足 → 结论降级「观察」；报告含证据与洞察留位。"""
        from zimeiti_api.ops_calibration import calibrate

        paths = calibrate(
            seeded_db,
            platform="xhs-main",
            profile="xhs-main",
            out_dir=str(tmp_path / "evals"),
        )
        assert len(paths) == 1
        md = Path(paths[0]).read_text(encoding="utf-8")
        assert "## 证据（脚本计算）" in md
        assert "## Agent 洞察（待填写）" in md
        assert "## 建议" in md
        assert "观察（混杂：样本不足）" in md  # 快照 2 条 < 5 → 降级

    def test_profile_not_mutated(self, seeded_db, tmp_path, monkeypatch):
        """校准 MUST NOT 修改画像文件（铁律 4）。"""
        from zimeiti_api.ops_calibration import calibrate

        profile_file = tmp_path / "xhs-main.yaml"
        profile_file.write_text("account: xhs-main\n", encoding="utf-8")
        monkeypatch.setattr(
            "zimeiti_api.ops_calibration.profile_paths",
            lambda platform: [profile_file],
        )
        calibrate(
            seeded_db, platform="xhs-main", profile="xhs-main", out_dir=str(tmp_path / "evals")
        )
        assert profile_file.read_text(encoding="utf-8") == "account: xhs-main\n"

    def test_mature_report_marks_conclusions(self, seeded_db, tmp_path):
        """成熟记录充足（≥5 快照 + 跨度 ≥3 天）→ 正常结论标注。"""
        from zimeiti_api.ops_calibration import calibrate

        # 补足成熟度：再挂 3 条快照（共 5 条）
        eid = seeded_db.list_events("xhs-main")[0]["id"]
        for i in range(3):
            seeded_db.record_snapshot(eid, "xhs-main", "read", 300 + i, source="creator-center")
        paths = calibrate(
            seeded_db,
            platform="xhs-main",
            profile="xhs-main",
            out_dir=str(tmp_path / "evals"),
        )
        md = Path(paths[0]).read_text(encoding="utf-8")
        assert "观察（混杂：样本不足）" not in md


class TestCli:
    def test_cli_calibrate(self, seeded_db, tmp_path, monkeypatch, capsys):
        from zimeiti_api import ops_calibration as oc

        monkeypatch.setattr(oc, "_eval_dir", lambda: str(tmp_path / "evals"))
        assert oc.main(["calibrate", "--platform", "xhs-main", "--profile", "xhs-main"]) == 0
        out = capsys.readouterr().out
        assert "eval.md" in out
