"""web-workbench 后端端点验收（T1-T3）：dashboard/profiles/trends/outputs。"""

import json
from datetime import datetime

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
            publish_events=[{"publish_date": datetime.now().strftime("%Y-%m-%d"), "title": "x"}],
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


class TestAccountsDetail:
    def test_detail_aggregation(self, profile_dir, tmp_path, monkeypatch):
        from zimeiti_api.governance import platform_state
        from zimeiti_api.operations import workbench

        cred = tmp_path / "creds"
        cred.mkdir()
        (cred / "xhs-main.sealed").write_text("sealed", encoding="utf-8")
        login = tmp_path / "xhs_state.json"
        monkeypatch.setattr(platform_state, "_state_path", lambda: tmp_path / "ps.json")
        platform_state.ensure_defaults()

        out = workbench.accounts_detail(profile_dir, cred, login)
        assert out == [
            {
                "account": "xhs-main",
                "enabled": True,
                "credentials_sealed": True,
                "login_state": False,
            }
        ]


class TestSettings:
    def test_roundtrip_and_whitelist(self, tmp_path, monkeypatch):
        from zimeiti_api.core import settings

        f = tmp_path / "settings.json"
        monkeypatch.setattr(settings, "settings_path", lambda: f)
        settings.update_settings({"notify_webhook_url": "https://x.example/hook"})
        assert settings.get_setting("notify_webhook_url") == "https://x.example/hook"
        with pytest.raises(ValueError, match="未知设置项"):
            settings.update_settings({"evil": 1})

    def test_notify_uses_runtime_setting(self, tmp_path, monkeypatch):
        from zimeiti_api.core import notify, settings

        f = tmp_path / "settings.json"
        monkeypatch.setattr(settings, "settings_path", lambda: f)
        monkeypatch.delenv("ZIMEITI_NOTIFY_WEBHOOK", raising=False)
        settings.update_settings({"notify_webhook_url": "https://feishu.example/hook"})
        sent = []
        monkeypatch.setattr(
            notify.requests,
            "post",
            lambda url, **k: sent.append(url) or type("R", (), {"status_code": 200})(),
        )
        notify.send("test_event", "hello")
        assert sent == ["https://feishu.example/hook"]


class TestToolCatalog:
    def test_catalog_lists_five_tools(self, tmp_path):
        from zimeiti_api.runtime.tools import tool_catalog

        profile = {
            "account": "xhs-main",
            "positioning": "测试",
            "style": "s",
            "audience": "a",
            "content_focus": "图文",
            "boundary": "b",
            "platform_rules": "r",
            "preferences": "p",
        }
        cat = tool_catalog(profile, None, None, tmp_path / "c")
        names = [t["name"] for t in cat]
        assert names == ["discover_topics", "select_topic", "create_drafts", "publish", "ask_human"]
        assert all(t["description"] for t in cat)


class TestOutputDetail:
    def test_detail_full(self, tmp_path):
        slug_dir = tmp_path / "xhs-main" / "20261010-120000"
        slug_dir.mkdir(parents=True)
        (slug_dir / "drafts.json").write_text(
            json.dumps(
                {
                    "topic": "T",
                    "created_at": "2026-10-10T12:00:00",
                    "compliance": {"passed": True},
                    "drafts": {"xhs": {"title": "标题X", "body": "正文", "tags": ["a"]}},
                }
            ),
            encoding="utf-8",
        )
        out = workbench.output_detail("xhs-main", "20261010-120000", tmp_path)
        assert out["drafts"]["xhs"]["title"] == "标题X"
        assert out["compliance"]["passed"] is True

    def test_detail_404(self, tmp_path):
        assert workbench.output_detail("xhs-main", "ghost", tmp_path) is None

    def test_detail_traversal_rejected(self, tmp_path):
        with pytest.raises(ValueError, match="非法"):
            workbench.output_detail("xhs-main", "..%2Fetc", tmp_path)


class TestAccountsCrud:
    """feat-accounts-crud：创建/删除账号（含凭证清理与审计）。"""

    def test_create_account(self, profile_dir, tmp_path, monkeypatch):
        from zimeiti_api.governance import platform_state
        from zimeiti_api.operations import workbench

        ps = tmp_path / "ps.json"
        monkeypatch.setattr(platform_state, "_state_path", lambda: ps)
        platform_state.ensure_defaults()
        data = {
            "account": "gzh-test",
            "positioning": "p",
            "style": "s",
            "audience": "a",
            "content_focus": "图文",
            "boundary": "b",
            "platform_rules": "r",
            "preferences": "p",
        }
        out = workbench.create_account(data, profile_dir)
        assert out["enabled"] is True
        assert (profile_dir / "gzh-test" / "profile.yaml").exists()

    def test_create_duplicate_409(self, profile_dir, tmp_path, monkeypatch):
        from zimeiti_api.governance import platform_state
        from zimeiti_api.operations import workbench

        monkeypatch.setattr(platform_state, "_state_path", lambda: tmp_path / "ps.json")
        platform_state.ensure_defaults()
        data = {
            "account": "gzh-test",
            "positioning": "p",
            "style": "s",
            "audience": "a",
            "content_focus": "图文",
            "boundary": "b",
            "platform_rules": "r",
            "preferences": "p",
        }
        workbench.create_account(data, profile_dir)
        with pytest.raises(FileExistsError):
            workbench.create_account(data, profile_dir)

    def test_delete_account_cleans_credentials(self, profile_dir, tmp_path, monkeypatch):
        from zimeiti_api.governance import platform_state
        from zimeiti_api.operations import workbench

        ps = tmp_path / "ps.json"
        monkeypatch.setattr(platform_state, "_state_path", lambda: ps)
        platform_state.ensure_defaults()
        cred = tmp_path / "creds"
        cred.mkdir()
        (cred / "xhs-main.sealed").write_text("sealed", encoding="utf-8")
        out = workbench.delete_account("xhs-main", profile_dir, cred, ps)
        assert out["removed"]["profile"] is True
        assert out["removed"]["credentials"] is True
        assert not (profile_dir / "xhs-main").exists()
        assert not (cred / "xhs-main.sealed").exists()

    def test_delete_unknown_404(self, profile_dir, tmp_path):
        from zimeiti_api.operations import workbench

        with pytest.raises(FileNotFoundError):
            workbench.delete_account("ghost", profile_dir, tmp_path, tmp_path / "ps.json")
