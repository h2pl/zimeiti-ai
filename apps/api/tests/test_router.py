"""Task 1.1-1.5 验收：平台路由器、读回三档真实判定、小红书登录态管理、W1 退役。"""

import pytest

from zimeiti_api.creation import GzhDraft, XhsDraft


class TestRouter:
    def test_gzh_account_routes_to_gzh_client(self, monkeypatch):
        """gzh-* 账号必须路由到公众号草稿箱流程。"""
        import zimeiti_api.platforms.gzh as gzh_mod
        from zimeiti_api.tools import real_platform_router

        sent = []

        class FakeClient:
            def __init__(self, app_id, app_secret, token_cache=None):
                pass

            def add_draft(self, articles):
                sent.append(("add", articles[0]["title"]))
                return "MEDIA_X"

            def draft_count(self):
                return 5

            def draft_list(self, count=10):
                return ["测试标题"]

        monkeypatch.setattr(gzh_mod, "GzhClient", FakeClient)
        # 凭证走加密存储（宪法 II），路由器从 sealed 解密注入
        monkeypatch.setattr(
            "zimeiti_api.credentials.load_account_credentials",
            lambda account: {"app_id": "wxtest", "app_secret": "sectest"},
        )

        result = real_platform_router("gzh-main", GzhDraft(title="测试标题", body="b", summary="s"))
        assert result["readback"] == "verified"
        assert sent == [("add", "测试标题")]

    def test_xhs_account_routes_to_xhs_publisher(self, monkeypatch):
        import zimeiti_api.platforms.xhs as xhs_mod
        from zimeiti_api.tools import real_platform_router

        actions = []

        class FakePage:
            def goto(self, url):
                actions.append(("goto", url))

            def fill(self, sel, text):
                actions.append(("fill", text))

            def click(self, sel):
                actions.append(("click",))

            def query_selector_all(self, sel):
                return [_El("AI 提效指南")]

        class _El:
            def __init__(self, t):
                self._t = t

            def text_content(self):
                return self._t

        class FakePub:
            def __init__(self, storage_state=None, selectors=None):
                pass

            def publish(self, draft, page=None):
                actions.append(("publish_flow",))
                return "submitted"

            def readback(self, title, page=None):
                actions.append(("readback",))
                return "verified"

        monkeypatch.setattr(xhs_mod, "XhsPublisher", FakePub)
        result = real_platform_router("xhs-main", XhsDraft(title="AI 提效指南", body="b"))
        assert result["readback"] == "verified"
        assert ("readback",) in actions

    def test_unknown_account_rejected(self):
        from zimeiti_api.tools import real_platform_router

        with pytest.raises(ValueError, match="未知平台账号"):
            real_platform_router("weibo-main", GzhDraft(title="t", body="b", summary="s"))


class TestGzhReadback:
    def _client(self, monkeypatch, titles):
        from zimeiti_api.platforms.gzh import GzhClient

        class FakeClient(GzhClient):
            def __init__(self):
                pass

            def draft_list(self, count=10):
                return titles

        return FakeClient()

    def test_verified_when_title_in_list(self):
        from zimeiti_api.platforms.gzh import readback_gzh_draft

        class Client:
            def draft_list(self, count=10):
                return ["AI 提效指南"]

        assert readback_gzh_draft(Client(), "AI 提效指南") == "verified"

    def test_unverified_when_not_in_list(self):
        from zimeiti_api.platforms.gzh import readback_gzh_draft

        class EmptyClient:
            def draft_list(self, count=10):
                return []

        assert readback_gzh_draft(EmptyClient(), "AI 提效指南") == "unverified"

    def test_exception_returns_unverified(self):
        from zimeiti_api.platforms.gzh import readback_gzh_draft

        class BoomClient:
            def draft_list(self, count=10):
                raise RuntimeError("接口挂了")

        assert readback_gzh_draft(BoomClient(), "AI 提效指南") == "unverified"


class TestXhsLoginFlow:
    def _fake_pw(self, actions, state_exists):

        class FakePage:
            def goto(self, url):
                actions.append(("goto", url))

            def wait_for_url(self, url, timeout=None):
                actions.append(("wait_login_ok",))

            def on(self, *a, **k):
                pass

        class FakeContext:
            def add_init_script(self, script):
                actions.append(("init_script",))

            def new_page(self):
                return FakePage()

            def storage_state(self, path=None):
                actions.append(("save", path))
                if path:
                    Path_(path).write_text("{}", encoding="utf-8")

        class FakeBrowser:
            def new_context(self, storage_state=None, **kw):
                actions.append(("context", storage_state))
                return FakeContext()

            def launch(self, headless=False, **kw):
                actions.append(("launch",))
                return self

            def close(self):
                pass

        return _FakePW(FakeBrowser())

    def test_first_run_opens_login_and_saves_state(self, tmp_path, monkeypatch):
        from zimeiti_api.platforms.xhs import XhsPublisher

        state_file = tmp_path / "xhs_state.json"
        actions: list = []
        monkeypatch.setattr(
            "zimeiti_api.platforms.xhs.sync_playwright",
            lambda: self._fake_pw(actions, state_exists=False),
        )
        pub = XhsPublisher(storage_state=str(state_file))
        pub.login_interactive()
        assert ("goto", "https://creator.xiaohongshu.com/login") in actions
        assert ("save", str(state_file)) in actions

    def test_reuse_existing_state(self, tmp_path, monkeypatch):
        from zimeiti_api.platforms.xhs import XhsPublisher

        state_file = tmp_path / "xhs_state.json"
        state_file.write_text("{}", encoding="utf-8")
        actions: list = []
        monkeypatch.setattr(
            "zimeiti_api.platforms.xhs.sync_playwright",
            lambda: self._fake_pw(actions, state_exists=True),
        )
        pub = XhsPublisher(storage_state=str(state_file))
        pub._open_page()
        assert ("context", str(state_file)) in actions


class _FakePW:
    def __init__(self, browser):
        self._b = browser

    @property
    def chromium(self):
        return self._b

    def start(self):
        return self

    def stop(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


from pathlib import Path as Path_  # noqa: E402


def test_production_path_has_no_placeholder_hook():
    """Task 1.5 W1 回归：生产模块不再引用占位钩子 default_platform_call。"""
    import inspect

    import zimeiti_api.tools as tools_mod

    src = inspect.getsource(tools_mod)
    # 占位钩子只允许作为测试兜底注释存在，不允许出现在发布路径调用中
    assert "platform_call=default_platform_call" not in src
