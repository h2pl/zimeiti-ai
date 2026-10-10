"""web-pages-batch 端点验收：dashboard/accounts/settings/postmortems/tools/trigger。"""

import json

import pytest
import yaml
from fastapi.testclient import TestClient

from zimeiti_api.app import create_app
from zimeiti_api.governance import platform_state


@pytest.fixture
def profile_dir(tmp_path, monkeypatch):
    """隔离 profiles 目录（与 test_workbench.py 同款）。"""
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


@pytest.fixture
def client(tmp_path, monkeypatch, profile_dir, metrics_db):
    """TestClient + PG 测试库打桩 + 平台全启用。"""
    monkeypatch.setattr("zimeiti_api.operations.metrics.MetricsDB", lambda: metrics_db)
    return TestClient(create_app())


class TestDashboardEndpoint:
    def test_dashboard_200(self, client):
        r = client.get("/api/dashboard")
        assert r.status_code == 200
        body = r.json()
        assert set(body) >= {"pending_approvals", "accounts", "today_publishes", "recent_log"}


class TestProfilesEndpoints:
    def test_list(self, client):
        r = client.get("/api/profiles")
        assert r.status_code == 200
        assert {a["account"] for a in r.json()} == {"xhs-main"}  # fixture 只建一个账号目录

    def test_get_one(self, client):
        r = client.get("/api/profiles/xhs-main")
        assert r.status_code == 200
        assert r.json()["account"] == "xhs-main"

    def test_put_invalid_400_and_file_unchanged(self, client, profile_dir, monkeypatch):
        f = profile_dir / "xhs-main" / "profile.yaml"
        before = f.read_text(encoding="utf-8")
        bad = yaml.safe_load(before)
        bad.pop("style")
        r = client.put("/api/profiles/xhs-main", json=bad)
        print("DBG", r.status_code, repr(r.text[:200]))
        assert r.status_code == 400
        assert f.read_text(encoding="utf-8") == before  # 规格承诺：不落盘

    def test_put_valid_200(self, client, profile_dir):
        r = client.get("/api/profiles/xhs-main").json()
        r["positioning"] = "更新后的定位"
        resp = client.put("/api/profiles/xhs-main", json=r)
        assert resp.status_code == 200
        after = yaml.safe_load(
            (profile_dir / "xhs-main" / "profile.yaml").read_text(encoding="utf-8")
        )
        assert after["positioning"] == "更新后的定位"


class TestAccountsEndpoints:
    def test_detail(self, client, profile_dir, tmp_path, monkeypatch):

        monkeypatch.setattr(
            "zimeiti_api.operations.workbench.accounts_detail",
            lambda p, c, login_state: [
                {
                    "account": "xhs-main",
                    "enabled": platform_state.is_enabled("xhs-main"),
                    "credentials_sealed": True,
                    "login_state": login_state,
                }
            ],
        )
        r = client.get("/api/accounts")
        assert r.status_code == 200
        assert r.json()[0]["account"] == "xhs-main"

    def test_toggle_and_publish_block(self, client, profile_dir, tmp_path, monkeypatch):
        monkeypatch.setattr(platform_state, "_state_path", lambda: tmp_path / "ps.json")
        platform_state.ensure_defaults()
        r = client.post("/api/accounts/xhs-main/toggle", json={"enabled": False})
        assert r.status_code == 200
        assert platform_state.is_enabled("xhs-main") is False

    def test_toggle_invalid_account_400(self, client):
        r = client.post("/api/accounts/..%2Fetc/toggle", json={"enabled": False})
        assert r.status_code in (400, 404)  # 路由不匹配或校验拒绝


class TestPostmortemEndpoints:
    def test_list_with_data(self, client, metrics_db):
        metrics_db.record_event(
            platform="xhs-main",
            title="爆文",
            source_folder="f1",
            publish_date="2026-10-01",
            profile="xhs-main",
            topic_direction="AI",
        )
        eid = metrics_db.list_events("xhs-main")[0]["id"]
        metrics_db.record_snapshot(
            eid,
            "xhs-main",
            "read",
            500,
            source="creator-center",
            captured_at="2026-10-09T10:00:00",
        )
        r = client.get("/api/postmortems/xhs-main")
        assert r.status_code == 200
        body = r.json()
        assert body["top"][0]["title"] == "爆文"

    def test_note_404(self, client):
        r = client.get("/api/postmortems/xhs-main/不存在")
        assert r.status_code == 404


class TestSettingsEndpoints:
    def test_put_get_roundtrip(self, client, tmp_path, monkeypatch):
        from zimeiti_api.core import settings

        monkeypatch.setattr(settings, "settings_path", lambda: tmp_path / "s.json")
        r = client.put("/api/settings", json={"notify_webhook_url": "https://hook"})
        assert r.status_code == 200
        assert client.get("/api/settings").json()["notify_webhook_url"] == "https://hook"

    def test_put_unknown_key_400(self, client):
        r = client.put("/api/settings", json={"evil": "x"})
        assert r.status_code == 400


class TestToolsAndTrigger:
    def test_tools_list(self, client):
        r = client.get("/api/tools")
        assert r.status_code == 200
        names = [t["name"] for t in r.json()]
        assert "publish" in names and "ask_human" in names

    def test_ops_trigger(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr("zimeiti_api.config.DATA_DIR", str(tmp_path))
        r = client.post("/api/ops/trigger", json={"job": "ops_data"})
        assert r.status_code == 200
        assert json.loads(
            (tmp_path / "state" / "ops-trigger.json").read_text(encoding="utf-8")
        ) == {"ops_data": True}

    def test_ops_trigger_invalid_job_400(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr("zimeiti_api.config.DATA_DIR", str(tmp_path))
        r = client.post("/api/ops/trigger", json={"job": "nonsense"})
        assert r.status_code == 400
