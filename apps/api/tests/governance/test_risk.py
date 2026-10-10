"""risk/platform_state/notify/preflight 验收：风控分级、fail-closed 开关、通知、预检。"""

from datetime import datetime, timedelta

from zimeiti_api.core import notify
from zimeiti_api.governance import platform_state, risk
from zimeiti_api.governance.preflight import preflight

# ── 风控信号分级（P0①③） ──────────────────────────────────────────


class TestClassify:
    def test_soft_block_signals(self):
        assert risk.classify("redirect error_code=300017") == "soft_block"
        assert risk.classify("error_code=300031 太快了") == "soft_block"
        assert risk.classify("页面提示：请求太频繁") == "soft_block"
        assert risk.classify("安全限制", status=None) == "soft_block"
        assert risk.classify("whatever", status=429) == "soft_block"

    def test_login_wall_signals(self):
        assert risk.classify("<head><title>登录</title>") == "login_wall"
        assert risk.classify("creator.xiaohongshu.com/login?foo=1") == "login_wall"
        assert risk.classify("请先登录后再操作") == "login_wall"
        assert risk.classify("boom", status=401) == "login_wall"

    def test_soft_block_before_login_wall(self):
        """判定顺序铁律（xiaobei relay-sign.ts）：软风控先于登录墙。"""
        combined = "error_code=300017 redirect to /login 请登录"
        assert risk.classify(combined) == "soft_block"

    def test_transient_and_unknown(self):
        assert risk.classify("connection timed out") == "transient"
        assert risk.classify("boom", status=502) == "transient"
        assert risk.classify("奇怪的全新错误") == "unknown"


class TestCooldown:
    def test_set_and_expire(self, monkeypatch, tmp_path):
        monkeypatch.setattr(risk, "_cooldown_path", lambda: tmp_path / "cd.json")
        assert risk.in_cooldown("xhs-main") is False
        risk.set_cooldown("xhs-main", minutes=30)
        assert risk.in_cooldown("xhs-main", now=datetime.now()) is True
        assert risk.in_cooldown("xhs-main", now=datetime.now() + timedelta(hours=1)) is False


class TestHandlePlatformError:
    def test_login_wall_disables_and_notifies(self, monkeypatch, tmp_path):
        monkeypatch.setattr(platform_state, "_state_path", lambda: tmp_path / "ps.json")
        sent = []
        monkeypatch.setattr(notify, "send", lambda event, text: sent.append(event) or True)
        level = risk.handle_platform_error("xhs-main", "publish", "<head>登录页")
        assert level == "login_wall"
        assert platform_state.is_enabled("xhs-main") is False  # 自动停用
        assert "login_wall" in sent

    def test_soft_block_sets_cooldown(self, monkeypatch, tmp_path):
        monkeypatch.setattr(platform_state, "_state_path", lambda: tmp_path / "ps.json")
        platform_state.ensure_defaults()  # fail-closed：无状态文件 = 全停
        monkeypatch.setattr(risk, "_cooldown_path", lambda: tmp_path / "cd.json")
        monkeypatch.setattr(notify, "send", lambda event, text: True)
        level = risk.handle_platform_error("xhs-main", "pull", "error_code=300017")
        assert level == "soft_block"
        assert risk.in_cooldown("xhs-main") is True
        assert platform_state.is_enabled("xhs-main") is True  # 软风控不停用（登录态是好的）

    def test_unknown_only_records(self, monkeypatch, tmp_path):
        monkeypatch.setattr(platform_state, "_state_path", lambda: tmp_path / "ps.json")
        monkeypatch.setattr(risk, "_cooldown_path", lambda: tmp_path / "cd.json")
        level = risk.handle_platform_error("xhs-main", "pull", "全新未知错误")
        assert level == "unknown"
        assert risk.in_cooldown("xhs-main") is False


# ── 平台启停开关（P0⑦，fail-closed） ───────────────────────────────


class TestPlatformState:
    def test_missing_file_is_disabled(self, tmp_path, monkeypatch):
        monkeypatch.setattr(platform_state, "_state_path", lambda: tmp_path / "ps.json")
        assert platform_state.is_enabled("xhs-main") is False  # fail-closed

    def test_corrupt_file_is_disabled(self, tmp_path, monkeypatch):
        f = tmp_path / "ps.json"
        f.write_text("{broken", encoding="utf-8")
        monkeypatch.setattr(platform_state, "_state_path", lambda: f)
        assert platform_state.is_enabled("xhs-main") is False

    def test_ensure_defaults_then_enabled(self, tmp_path, monkeypatch):
        f = tmp_path / "ps.json"
        monkeypatch.setattr(platform_state, "_state_path", lambda: f)
        platform_state.ensure_defaults()
        assert platform_state.is_enabled("xhs-main") is True
        assert platform_state.is_enabled("gzh-main") is True
        # ensure 幂等：不覆盖已有状态
        platform_state.set_enabled("xhs-main", False, "测试停用")
        platform_state.ensure_defaults()
        assert platform_state.is_enabled("xhs-main") is False

    def test_disabled_accounts(self, tmp_path, monkeypatch):
        f = tmp_path / "ps.json"
        monkeypatch.setattr(platform_state, "_state_path", lambda: f)
        platform_state.ensure_defaults()
        platform_state.set_enabled("gzh-main", False, "登录失效")
        assert platform_state.disabled_accounts() == ["gzh-main"]


# ── 通知 webhook（P0④） ───────────────────────────────────────────


class TestNotify:
    def test_no_webhook_is_silent_skip(self, monkeypatch):
        monkeypatch.delenv("ZIMEITI_NOTIFY_WEBHOOK", raising=False)
        assert notify.send("e", "text") is False

    def test_generic_payload(self, monkeypatch):
        seen = {}
        monkeypatch.setenv("ZIMEITI_NOTIFY_WEBHOOK", "https://example.com/hook")

        class Resp:
            status_code = 200

        def fake_post(url, json=None, timeout=None):
            seen.update(url=url, payload=json)
            return Resp()

        monkeypatch.setattr(notify.requests, "post", fake_post)
        assert notify.send("publish_result", "ok") is True
        assert seen["payload"]["event"] == "publish_result"

    def test_feishu_format_auto_adapted(self, monkeypatch):
        seen = {}
        monkeypatch.setenv(
            "ZIMEITI_NOTIFY_WEBHOOK", "https://open.feishu.cn/open-apis/bot/v2/hook/x"
        )

        class Resp:
            status_code = 200

        monkeypatch.setattr(
            notify.requests,
            "post",
            lambda url, json=None, timeout=None: seen.update(payload=json) or Resp(),
        )
        notify.send("e", "hello")
        assert seen["payload"] == {"msg_type": "text", "content": {"text": "[e] hello"}}

    def test_send_failure_is_silent(self, monkeypatch):
        monkeypatch.setenv("ZIMEITI_NOTIFY_WEBHOOK", "https://example.com/hook")

        def boom(url, json=None, timeout=None):
            raise RuntimeError("网络挂了")

        monkeypatch.setattr(notify.requests, "post", boom)
        assert notify.send("e", "x") is False  # 观测层失败不影响主链路


# ── 发布前约束校验（P0⑥） ──────────────────────────────────────────


class TestPreflight:
    def test_xhs_limits(self):
        assert preflight("xhs-main", {"title": "t", "body": "b"}) == []
        assert any("标题" in v for v in preflight("xhs-main", {"title": "x" * 21, "body": "b"}))
        assert any("正文" in v for v in preflight("xhs-main", {"title": "t", "body": "x" * 1001}))
        assert any(
            "标签" in v
            for v in preflight("xhs-main", {"title": "t", "body": "b", "tags": ["a"] * 11})
        )

    def test_gzh_limits(self):
        assert preflight("gzh-main", {"title": "t", "body": "b", "summary": "s"}) == []
        assert any("标题" in v for v in preflight("gzh-main", {"title": "x" * 65, "body": "b"}))
        assert any(
            "摘要" in v
            for v in preflight("gzh-main", {"title": "t", "body": "b", "summary": "x" * 121})
        )

    def test_empty_rejected(self):
        assert len(preflight("xhs-main", {"title": "", "body": ""})) >= 2
