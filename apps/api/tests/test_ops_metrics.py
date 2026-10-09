"""ops-metrics-collection 验收：发布事件 upsert / 快照回收 / 失败保留历史 / 只读归因。

设计来源：xiaobei published-track（SQLite/upsert/失败留痕）+ Easel 数据三层
（事件与快照分离、消费只读）。
"""

from zimeiti_api.ops_metrics import (
    MetricsDB,
    parse_gzh_datacube,
    parse_xhs_dashboard,
)


class TestPublishEvents:
    def test_record_event_and_upsert(self, tmp_path):
        db = MetricsDB(tmp_path / "m.db")
        eid1 = db.record_event(
            platform="gzh-main",
            title="标题A",
            source_folder="2026-10-09-a",
            publish_date="2026-10-09",
            profile="gzh-main",
            topic_direction="AI 提效",
            status="ok",
        )
        eid2 = db.record_event(
            platform="gzh-main",
            title="标题A（更新）",
            source_folder="2026-10-09-a",
            publish_date="2026-10-09",
            profile="gzh-main",
            topic_direction="AI 提效",
            status="ok",
            publish_url="https://mp.weixin.qq.com/s/abc",
        )
        assert eid1 == eid2  # upsert 而非插入
        events = db.list_events(platform="gzh-main")
        assert len(events) == 1
        assert events[0]["title"] == "标题A（更新）"
        assert events[0]["publish_url"].endswith("/abc")

    def test_record_failed_event_keeps_notes(self, tmp_path):
        db = MetricsDB(tmp_path / "m.db")
        db.record_event(
            platform="xhs-main",
            title="t",
            source_folder="f",
            publish_date="2026-10-09",
            profile="xhs-main",
            status="failed",
            notes="发布失败: 频控拒绝",
        )
        events = db.list_events(platform="xhs-main")
        assert events[0]["status"] == "failed"
        assert "频控" in events[0]["notes"]


class TestSnapshots:
    def test_snapshot_written_and_history_kept(self, tmp_path):
        db = MetricsDB(tmp_path / "m.db")
        eid = db.record_event(
            platform="gzh-main",
            title="t",
            source_folder="f",
            publish_date="2026-10-09",
            profile="gzh-main",
        )
        db.record_snapshot(eid, "gzh-main", "read", 512, source="datacube")
        snaps = db.list_snapshots("gzh-main")
        assert snaps[0]["metric"] == "read" and snaps[0]["value"] == 512

    def test_failed_collection_keeps_history_not_zero(self, tmp_path):
        """采集失败：记录错误，历史值不被零覆盖（spec 要求）。"""
        db = MetricsDB(tmp_path / "m.db")
        eid = db.record_event(
            platform="gzh-main",
            title="t",
            source_folder="f",
            publish_date="2026-10-09",
            profile="gzh-main",
        )
        db.record_snapshot(eid, "gzh-main", "read", 999, source="datacube")
        db.record_error("gzh-main", "datacube:2026-10-09", "接口异常")
        snaps = db.list_snapshots("gzh-main")
        # 失败不写零值快照，历史保持
        assert [s["value"] for s in snaps] == [999]
        assert db.list_errors("gzh-main")[0]["error"] == "接口异常"


class TestGzhDatacubeParse:
    def test_parse_user_summary(self):
        raw = {
            "list": [
                {
                    "ref_date": "2026-10-08",
                    "user_source": 0,
                    "new_user": 3,
                    "cancel_user": 1,
                    "cumulate_user": 212,
                }
            ]
        }
        metrics = parse_gzh_datacube(raw)
        assert metrics["new_user"] == 3
        assert metrics["cancel_user"] == 1
        assert metrics["cumulate_user"] == 212

    def test_parse_empty_returns_empty(self):
        assert parse_gzh_datacube({}) == {}


class TestXhsDashboardParse:
    SAMPLE = (
        "关注数 | 6 | 粉丝数 | 212 | 获赞与收藏 | 5281 | "
        "统计周期 10-02 至 10-08 | 曝光数 | 1234 | 观看数 | 900 | "
        "封面点击率 | 12% | 点赞数 | 30 | 评论数 | 4 | 收藏数 | 10 | "
        "分享数 | 2 | 净涨粉 | 5 | 新增关注 | 7 | 取消关注 | 2"
    )

    def test_parse_label_value_pairs(self):
        m = parse_xhs_dashboard(self.SAMPLE)
        assert m["曝光数"] == 1234
        assert m["点赞数"] == 30
        assert m["收藏数"] == 10
        assert m["净涨粉"] == 5
        assert m["粉丝数"] == 212
        assert m["获赞与收藏"] == 5281

    def test_missing_labels_recorded_not_zero(self):
        m = parse_xhs_dashboard("关注数 | 6 | 粉丝数 | 212")
        assert "曝光数" not in m  # 缺失不写零（零假阳性）
        assert m["粉丝数"] == 212


class TestReportReadonly:
    def test_report_does_not_mutate(self, tmp_path):
        db = MetricsDB(tmp_path / "m.db")
        eid = db.record_event(
            platform="gzh-main",
            title="t",
            source_folder="f",
            publish_date="2026-10-09",
            profile="gzh-main",
        )
        db.record_snapshot(eid, "gzh-main", "read", 100, source="datacube")
        before = db.list_snapshots("gzh-main")
        report = db.report(platform="gzh-main")
        after = db.list_snapshots("gzh-main")
        assert before == after  # 只读不回写
        assert report["platform"] == "gzh-main"

    def test_lifecycle_classification(self, tmp_path):
        """内容生命周期判定（速爆/稳增/长尾）为确定性规则。"""
        db = MetricsDB(tmp_path / "m.db")
        eid = db.record_event(
            platform="gzh-main",
            title="t",
            source_folder="f",
            publish_date="2026-10-01",
            profile="gzh-main",
        )
        # 首日冲高后停增 = 速爆型
        db.record_snapshot(eid, "gzh-main", "read", 1000, source="datacube")
        db.record_snapshot(eid, "gzh-main", "read", 1010, source="datacube")
        report = db.report(platform="gzh-main")
        notes = report["notes"]
        assert notes and notes[0]["lifecycle"] in ("速爆型", "稳增型", "长尾型", "数据不足")


class TestLifecycleRules:
    def test_classify_variants(self, tmp_path):
        from zimeiti_api.ops_metrics import classify_lifecycle

        assert classify_lifecycle([100]) == "数据不足"
        assert classify_lifecycle([1000, 1010]) == "速爆型"
        assert classify_lifecycle([100, 300]) == "稳增型"
        assert classify_lifecycle([100, 120]) == "长尾型"
        assert classify_lifecycle([0, 0]) == "长尾型"


class TestPullGzh:
    def test_pull_gzh_writes_snapshots(self, tmp_path, monkeypatch):
        from zimeiti_api import ops_metrics as om

        db = om.MetricsDB(tmp_path / "m.db")
        raw = {"list": [{"ref_date": "2026-10-08", "new_user": 3, "cancel_user": 1}]}

        class FakeGzhClient:
            def __init__(self, *a, **kw):
                pass

            def datacube(self, path, b, e):
                return raw

        monkeypatch.setattr("zimeiti_api.platforms.gzh.GzhClient", FakeGzhClient)
        monkeypatch.setattr(
            "zimeiti_api.credentials.load_account_credentials",
            lambda account: {"app_id": "a", "app_secret": "s"},
        )
        out = om.pull_gzh(db, "2026-10-08", "2026-10-08")
        assert out["ok"] is True and out["metrics"]["new_user"] == 3
        snaps = {s["metric"]: s["value"] for s in db.list_snapshots("gzh-main")}
        assert snaps["new_user"] == 3 and snaps["cancel_user"] == 1

    def test_pull_gzh_failure_records_error(self, tmp_path, monkeypatch):
        from zimeiti_api import ops_metrics as om

        db = om.MetricsDB(tmp_path / "m.db")

        class BoomClient:
            def __init__(self, *a, **kw):
                pass

            def datacube(self, path, b, e):
                raise RuntimeError("接口异常")

        monkeypatch.setattr("zimeiti_api.platforms.gzh.GzhClient", BoomClient)
        monkeypatch.setattr(
            "zimeiti_api.credentials.load_account_credentials",
            lambda account: {"app_id": "a", "app_secret": "s"},
        )
        out = om.pull_gzh(db, "2026-10-08", "2026-10-08")
        assert out["ok"] is False
        assert db.list_errors("gzh-main")[0]["error"] == "接口异常"


class TestPullXhs:
    SAMPLE = "关注数 | 6 | 粉丝数 | 212 | 曝光数 | 88 | 点赞数 | 3 | 收藏数 | 1"

    def test_pull_xhs_with_fake_page(self, tmp_path):
        from zimeiti_api import ops_metrics as om

        db = om.MetricsDB(tmp_path / "m.db")

        class FakePage:
            def goto(self, url):
                pass

            def wait_for_timeout(self, ms):
                pass

            def inner_text(self, sel):
                return TestPullXhs.SAMPLE

            def close(self):
                pass

        out = om.pull_xhs(db, page=FakePage())
        assert out["ok"] is True and out["metrics"]["曝光数"] == 88
        snaps = {s["metric"]: s["value"] for s in db.list_snapshots("xhs-main")}
        assert snaps["粉丝数"] == 212

    def test_pull_xhs_failure_records_error(self, tmp_path):
        from zimeiti_api import ops_metrics as om

        db = om.MetricsDB(tmp_path / "m.db")

        class BoomPage:
            def goto(self, url):
                raise RuntimeError("登录态失效")

            def wait_for_timeout(self, ms):
                pass

            def close(self):
                pass

        out = om.pull_xhs(db, page=BoomPage())
        assert out["ok"] is False
        assert db.list_errors("xhs-main")[0]["error"] == "登录态失效"


class TestCli:
    def test_cli_record_and_report(self, tmp_path, monkeypatch, capsys):
        from zimeiti_api import ops_metrics as om

        monkeypatch.setattr(om, "_db_path", lambda: str(tmp_path / "cli.db"))
        assert (
            om.main(
                [
                    "record",
                    "--platform",
                    "gzh-main",
                    "--title",
                    "标题",
                    "--source-folder",
                    "f1",
                    "--publish-date",
                    "2026-10-09",
                ]
            )
            == 0
        )
        assert om.main(["report", "--platform", "gzh-main"]) == 0
        printed = capsys.readouterr().out
        assert "gzh-main" in printed


class TestXhsLayoutRegression:
    """回归：首页两种排版并存（顶部「值→标签」、总览区「标签→值」），否则指标错位一位。"""

    REAL_LAYOUT = (
        "loopy的日常 | 6 | 关注数 | 212 | 粉丝数 | 5281 | 获赞与收藏 | "
        "小红书账号: 780428777 | 笔记数据总览 | 统计周期 10-02 至 10-08 | "
        "曝光数 | 0 | 环比- | 观看数 | 0 | 环比- | 点赞数 | 30 | 环比- | "
        "评论数 | 4 | 收藏数 | 10 | 分享数 | 2 | 净涨粉 | 5 | 新增关注 | 7 | 取消关注 | 2"
    )

    def test_top_area_value_then_label(self):
        m = parse_xhs_dashboard(self.REAL_LAYOUT)
        assert m["关注数"] == 6  # 顶部：值在前（错位会变成 212）
        assert m["粉丝数"] == 212
        assert m["获赞与收藏"] == 5281

    def test_summary_area_label_then_value(self):
        m = parse_xhs_dashboard(self.REAL_LAYOUT)
        assert m["曝光数"] == 0
        assert m["点赞数"] == 30
        assert m["评论数"] == 4
        assert m["收藏数"] == 10
        assert m["净涨粉"] == 5

    def test_non_numeric_neighbour_not_written(self):
        m = parse_xhs_dashboard("笔记数据总览 | 曝光数 | 环比- | 观看数 | 5")
        assert "曝光数" not in m  # 邻居为「环比-」，不写零
        assert m["观看数"] == 5
