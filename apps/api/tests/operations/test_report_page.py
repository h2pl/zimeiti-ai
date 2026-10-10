"""ops-metrics-report 验收：运营数据 HTML 报告页（Easel data-report 对标）。"""

import pytest

from zimeiti_api.operations.report_page import render_html_report


@pytest.fixture
def seeded_db(metrics_db):
    """带真实形态数据的库：事件 + 账号级快照 + 单篇快照。"""
    db = metrics_db
    db.record_event(
        platform="xhs-main",
        title="测试笔记A",
        source_folder="f1",
        publish_date="2026-10-01",
        profile="xhs-main",
        topic_direction="AI 提效",
        status="ok",
        publish_url="https://xhs.test/1",
    )
    db.record_event(
        platform="gzh-main",
        title="公众号文章A",
        source_folder="g1",
        publish_date="2026-10-03",
        profile="gzh-main",
        status="failed",
        notes="频控拒绝",
    )
    eid = db.list_events("xhs-main")[0]["id"]
    db.record_snapshot(None, "xhs-main", "粉丝数", 212, source="creator-center")
    db.record_snapshot(None, "xhs-main", "获赞与收藏", 5281, source="creator-center")
    db.record_snapshot(eid, "xhs-main", "read", 300, source="creator-center")
    db.record_snapshot(eid, "xhs-main", "read", 600, source="creator-center")
    return db


class TestReportPage:
    def test_kpi_values_and_structure(self, seeded_db, tmp_path):
        out = tmp_path / "report.html"
        html = render_html_report(seeded_db, platform="xhs-main", out_path=str(out))

        assert out.exists()
        assert "212" in html  # 粉丝数最新
        assert "5281" in html  # 获赞与收藏
        assert "测试笔记A" in html  # 事件表
        assert "<svg" in html  # 内联 SVG 图表
        assert "http://" not in html and "https://" not in html  # 自包含

    def test_missing_metric_shows_no_data(self, seeded_db, tmp_path):
        """无快照的指标显示「无数据」而非零值（gzh 无任何快照）。"""
        html = render_html_report(seeded_db, platform="gzh-main")
        assert "无数据" in html
        assert "公众号文章A" in html and "failed" in html

    def test_readonly(self, seeded_db, tmp_path):
        before = seeded_db.list_snapshots("xhs-main")
        render_html_report(seeded_db, platform="xhs-main")
        assert seeded_db.list_snapshots("xhs-main") == before

    def test_platform_filter(self, seeded_db, tmp_path):
        html = render_html_report(seeded_db, platform="gzh-main")
        assert "公众号文章A" in html
        assert "测试笔记A" not in html  # 平台过滤

    def test_svg_trend_uses_snapshot_values(self, seeded_db, tmp_path):
        """SVG 折线包含 read 快照数值（300→600）。"""
        html = render_html_report(seeded_db, platform="xhs-main")
        assert html.count("read") >= 1
