"""web-workbench 后端端点验收（T1-T3）：dashboard/profiles/trends/outputs。"""

import json

import pytest
import yaml

from zimeiti_api.governance import platform_state
from zimeiti_api.operations import workbench


@pytest.fixture
def profile_dir(tmp_path, monkeypatch):
    """隔离 profiles 目录 + 平台启停状态。"""
    pdir = tmp_path / "profiles"
    acc = pdir / "xhs-main"
    acc.mkdir(parents=True)
    data = {
        "account": "xhs-main",
        "positioning": "AI 工具分享",
        "style": "口语化",
        "audience": "效率爱好者",
        "content_focus": "图文",
        "boundary": "不承诺收益",
        "platform_rules": "标题≤20字",
        "preferences": "结合定位",
    }
    (acc / "profile.yaml").write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    monkeypatch.setattr("zimeiti_api.content.profiles.DEFAULT_BASE_DIR", pdir)
    ps = tmp_path / "ps.json"
    monkeypatch.setattr(platform_state, "_state_path", lambda: ps)
    platform_state.ensure_defaults()
    return pdir


class TestDashboard:
    def test_summary(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "zimeiti_api.runtime.hosted.list_pending_approvals", lambda: [{"thread_id": "t"}]
        )
        out = workbench.dashboard_summary(
            pending_count=1,
            accounts={"xhs-main": True},
            publish_events=[{"publish_date": "2026-10-10", "title": "x"}],
            recent_log=[{"action": "a"}],
        )
        assert out["pending_approvals"] == 1
        assert out["today_publishes"] == 1
        assert out["accounts"] == {"xhs-main": True}


class TestProfiles:
    def test_list_accounts(self, profile_dir):
        out = workbench.list_accounts(profile_dir)
        assert out == [{"account": "xhs-main", "enabled": True}]

    def test_load_and_save_roundtrip(self, profile_dir):
        data = workbench.load_profile_data("xhs-main")
        assert data["positioning"] == "AI 工具分享"
        assert data["enabled"] is True
        data["positioning"] = "新定位"
        workbench.save_profile("xhs-main", data)
        assert workbench.load_profile_data("xhs-main")["positioning"] == "新定位"

    def test_save_rejects_invalid(self, profile_dir):
        data = workbench.load_profile_data("xhs-main")
        data.pop("positioning")
        with pytest.raises(Exception, match="必填|缺少|positioning"):
            workbench.save_profile("xhs-main", data)

    def test_save_rejects_account_mismatch(self, profile_dir):
        data = workbench.load_profile_data("xhs-main")
        data["account"] = "gzh-main"
        with pytest.raises(ValueError, match="不一致"):
            workbench.save_profile("xhs-main", data)

    def test_save_rejects_path_traversal(self, profile_dir):
        with pytest.raises(ValueError, match="非法账号名"):
            workbench.load_profile_data("../etc")
        with pytest.raises(ValueError, match="非法账号名"):
            workbench.save_profile("..%2Fetc", {})

    def test_load_unknown_account_none(self, profile_dir):
        assert workbench.load_profile_data("ghost") is None


class TestTrendsOutputs:
    def test_trends_none_when_empty(self, metrics_db):
        assert workbench.trends("xhs-main", db=metrics_db) is None

    def test_trends_with_data(self, metrics_db):
        metrics_db.record_snapshot(
            None, "xhs-main", "粉丝数", 100, source="datacube", captured_at="2026-10-09T10:00:00"
        )
        ev = workbench.trends("xhs-main", db=metrics_db)
        assert ev["snapshots"] == 1
        assert "粉丝数" in ev["baseline"]

    def test_outputs_scan(self, tmp_path):
        slug_dir = tmp_path / "xhs-main" / "20261010-120000"
        slug_dir.mkdir(parents=True)
        (slug_dir / "drafts.json").write_text(
            json.dumps(
                {
                    "topic": "测试选题",
                    "created_at": "2026-10-10T12:00:00",
                    "compliance": {"passed": True},
                    "drafts": {"xhs": {"title": "标题X"}},
                }
            ),
            encoding="utf-8",
        )
        (tmp_path / "xhs-main" / "empty").mkdir()
        out = workbench.outputs("xhs-main", tmp_path)
        assert len(out) == 1
        assert out[0]["title"] == "标题X" and out[0]["compliance_passed"] is True

    def test_outputs_empty_account(self, tmp_path):
        assert workbench.outputs("ghost", tmp_path) == []

    def test_save_reject_keeps_file_unchanged(self, profile_dir):
        """规格场景（W2）：非法编辑必须保证 profile.yaml 内容不变。"""
        f = profile_dir / "xhs-main" / "profile.yaml"
        before = f.read_text(encoding="utf-8")
        data = workbench.load_profile_data("xhs-main")
        data.pop("style")  # 缺必填 → validate 拒绝
        with pytest.raises(ValueError, match="必填"):
            workbench.save_profile("xhs-main", data)
        assert f.read_text(encoding="utf-8") == before

    def test_save_filters_unknown_keys(self, profile_dir):
        """W3：未知键不得持久化进画像文件。"""
        data = workbench.load_profile_data("xhs-main")
        data["hacked_field"] = "evil"
        workbench.save_profile("xhs-main", data)
        on_disk = yaml.safe_load(
            (profile_dir / "xhs-main" / "profile.yaml").read_text(encoding="utf-8")
        )
        assert "hacked_field" not in on_disk
