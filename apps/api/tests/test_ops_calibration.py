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
    db.record_snapshot(
        eid1, "xhs-main", "read", 100, source="creator-center", captured_at="2026-10-09T20:00:00"
    )
    db.record_snapshot(
        eid2, "xhs-main", "read", 300, source="creator-center", captured_at="2026-10-09T20:05:00"
    )
    db.record_snapshot(
        None, "xhs-main", "粉丝数", 106, source="creator-center", captured_at="2026-10-09T20:10:00"
    )
    db.record_snapshot(
        None, "xhs-main", "粉丝数", 212, source="creator-center", captured_at="2026-10-09T20:15:00"
    )
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


class TestKeyFindings:
    """校准报告扩展：关键发现（确定性 Top 3）/ 方法论 / 局限性（Easel 对标）。"""

    def test_key_findings_generated(self, seeded_db, tmp_path):
        from zimeiti_api.ops_calibration import calibrate

        # 补足成熟度
        eid = seeded_db.list_events("xhs-main")[0]["id"]
        for i in range(5):
            seeded_db.record_snapshot(eid, "xhs-main", "read", 300 + i, source="creator-center")
        paths = calibrate(
            seeded_db, platform="xhs-main", profile="xhs-main", out_dir=str(tmp_path / "e")
        )
        md = Path(paths[0]).read_text(encoding="utf-8")
        assert "## 关键发现" in md
        assert "## 方法论" in md
        assert "## 局限性" in md
        assert "关联性不等于因果性" in md  # Easel 局限性声明措辞

    def test_findings_ranked_and_limited_to_three(self, seeded_db, tmp_path):
        from zimeiti_api.ops_calibration import build_evidence, build_key_findings

        # 丰富数据：生命周期稳增 2 篇、同weekday发布 2 篇、基线异常指标
        db = seeded_db
        db.record_event(
            platform="xhs-main",
            title="笔记三",
            source_folder="f3",
            publish_date="2026-10-08",
            profile="xhs-main",
        )
        db.record_event(
            platform="xhs-main",
            title="笔记四",
            source_folder="f4",
            publish_date="2026-10-03",
            profile="xhs-main",
        )
        eid2 = [e for e in db.list_events("xhs-main") if e["source_folder"] == "f2"][0]["id"]
        eid3 = [e for e in db.list_events("xhs-main") if e["source_folder"] == "f3"][0]["id"]
        db.record_snapshot(
            eid2,
            "xhs-main",
            "read",
            600,
            source="creator-center",
            captured_at="2026-10-09T20:06:00",
        )
        db.record_snapshot(
            eid3,
            "xhs-main",
            "read",
            100,
            source="creator-center",
            captured_at="2026-10-09T20:07:00",
        )
        db.record_snapshot(
            eid3,
            "xhs-main",
            "read",
            200,
            source="creator-center",
            captured_at="2026-10-09T20:08:00",
        )
        db.record_snapshot(
            None,
            "xhs-main",
            "获赞与收藏",
            1000,
            source="creator-center",
            captured_at="2026-10-09T20:09:00",
        )
        db.record_snapshot(
            None,
            "xhs-main",
            "获赞与收藏",
            5281,
            source="creator-center",
            captured_at="2026-10-09T20:10:00",
        )

        ev = build_evidence(db, platform="xhs-main", profile="xhs-main")
        findings = build_key_findings(ev)
        assert 1 <= len(findings) <= 3
        texts = " / ".join(f["text"] for f in findings)
        assert "稳增型" in texts  # 生命周期结构
        assert "周四" in texts or "周六" in texts  # 最佳发布日
        assert "获赞与收藏" in texts  # 基线异常

    def test_insufficient_data_no_fabrication(self, metrics_db):
        """证据不足不编造：仅 1 篇事件且无快照 → 关键发现为空。"""
        from zimeiti_api.ops_calibration import build_evidence, build_key_findings

        db = metrics_db
        db.record_event(
            platform="gzh-main",
            title="唯一一篇",
            source_folder="f0",
            publish_date="2026-10-09",
            profile="gzh-main",
        )
        ev = build_evidence(db, platform="gzh-main", profile="gzh-main")
        assert build_key_findings(ev) == []


class TestAutoTrigger:
    """按量触发：自上次校准以来新快照 ≥5 执行；--force 绕过（xiaobei）。"""

    def test_auto_below_threshold_skips(self, seeded_db, tmp_path, capsys):
        from zimeiti_api.ops_calibration import auto_calibrate

        out = auto_calibrate(
            seeded_db,
            platform="xhs-main",
            profile="xhs-main",
            out_dir=str(tmp_path / "a"),
            last_calibrated_at="2026-10-09T23:00:00",
        )
        assert out["skipped"] is True
        assert out["new_snapshots"] == 0  # fixture 快照（10-09 晚）都在校准时间戳之前
        assert not (tmp_path / "a").exists() or not list((tmp_path / "a").glob("*.md"))

    def test_auto_above_threshold_runs(self, seeded_db, tmp_path):
        from zimeiti_api.ops_calibration import auto_calibrate

        # 校准时间戳之前 0 条，之后新增 6 条
        eid = seeded_db.list_events("xhs-main")[0]["id"]
        for i in range(6):
            seeded_db.record_snapshot(
                eid,
                "xhs-main",
                "read",
                400 + i,
                source="creator-center",
                captured_at="2026-10-10T01:00:00",
            )
        out = auto_calibrate(
            seeded_db,
            platform="xhs-main",
            profile="xhs-main",
            out_dir=str(tmp_path / "a"),
            last_calibrated_at="2026-10-10T00:00:00",
        )
        assert out["skipped"] is False
        assert out["new_snapshots"] >= 5

    def test_force_bypasses_threshold(self, seeded_db, tmp_path):
        from zimeiti_api.ops_calibration import auto_calibrate

        out = auto_calibrate(
            seeded_db,
            platform="xhs-main",
            profile="xhs-main",
            out_dir=str(tmp_path / "a"),
            last_calibrated_at=None,
            force=True,
        )
        assert out["skipped"] is False


class TestEvidenceZeroBaseline:
    def test_zero_mean_baseline_degrades_not_crashes(self, metrics_db):
        """定时任务无人值守：基线为零（如点赞数全程 0）必须降级，禁止除零崩溃。

        回归：2026-10-10 ops-daily 首轮 xhs-main 校准 division by zero。
        """
        from zimeiti_api.ops_calibration import build_evidence

        metrics_db.record_event(
            platform="xhs-main",
            title="笔记",
            source_folder="f1",
            publish_date="2026-10-01",
            profile="xhs-main",
        )
        for ts in ("2026-10-09T20:00:00", "2026-10-09T20:05:00"):
            metrics_db.record_snapshot(
                None, "xhs-main", "点赞数", 0, source="creator-center", captured_at=ts
            )
            metrics_db.record_snapshot(
                None, "xhs-main", "粉丝数", 212, source="creator-center", captured_at=ts
            )
        ev = build_evidence(metrics_db, platform="xhs-main", profile="xhs-main")
        assert ev["baseline"]["点赞数"]["normalized"] is None  # 基线为零 → 降级
        assert ev["baseline"]["粉丝数"]["normalized"] == 1.0
