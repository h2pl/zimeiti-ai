"""Task 6.2/6.3 验收：公众号草稿箱上传（my-tools 移植）+ 小红书发布框架读回。"""

import pytest

from zimeiti_api.creation import GzhDraft


class TestGzh:
    def test_publish_draft_verified(self, monkeypatch, tmp_path):
        from zimeiti_api.platforms.gzh import GzhClient, publish_gzh_draft

        calls = []

        def fake_get(url, params=None, timeout=None):
            assert "api.weixin.qq.com" in url
            if "/token" in url:
                return _FakeResp({"access_token": "TOKEN123", "expires_in": 7200})
            if "/draft/count" in url:
                calls.append(url)
                return _FakeResp({"total_count": 3})
            raise AssertionError(f"unexpected GET {url}")

        def fake_post(url, params=None, json=None, timeout=None):
            calls.append(url)
            assert json["articles"][0]["title"] == "AI 提效指南"
            return _FakeResp({"media_id": "MEDIA_001"})

        monkeypatch.setattr("zimeiti_api.platforms.gzh.httpx.get", fake_get)
        monkeypatch.setattr("zimeiti_api.platforms.gzh.httpx.post", fake_post)

        client = GzhClient("appid", "secret", token_cache=tmp_path / "token.json")

        draft = GzhDraft(title="AI 提效指南", body="正文内容", summary="摘要")
        result = publish_gzh_draft(client, draft)
        assert result["platform_result"] == "MEDIA_001"
        assert result["readback"] == "verified"
        assert any("/draft/add" in c for c in calls)
        assert any("/draft/count" in c for c in calls)

    def test_publish_draft_unverified_when_count_zero(self, monkeypatch, tmp_path):
        from zimeiti_api.platforms.gzh import GzhClient, publish_gzh_draft

        monkeypatch.setattr(
            "zimeiti_api.platforms.gzh.httpx.get",
            lambda url, params=None, timeout=None: (
                _FakeResp({"access_token": "T", "expires_in": 7200})
                if "/token" in url
                else _FakeResp({"total_count": 0})
            ),
        )
        monkeypatch.setattr(
            "zimeiti_api.platforms.gzh.httpx.post",
            lambda url, params=None, json=None, timeout=None: _FakeResp({"media_id": "M"}),
        )
        client = GzhClient("appid", "secret", token_cache=tmp_path / "token.json")
        draft = GzhDraft(title="t", body="b", summary="s")
        result = publish_gzh_draft(client, draft)
        assert result["readback"] == "unverified"


class _FakeResp:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data

    def raise_for_status(self):
        pass


class TestXhs:
    def test_parse_readback_found(self):
        from zimeiti_api.platforms.xhs import parse_readback

        assert parse_readback(["AI 提效指南", "其他"], "AI 提效指南") == "verified"
        assert parse_readback(["其他"], "AI 提效指南") == "unverified"

    def test_publish_flow_order_with_fake_page(self):
        from zimeiti_api.platforms.xhs import XhsPublisher
        from zimeiti_api.creation import XhsDraft

        actions = []

        class FakePage:
            def goto(self, url):
                actions.append(("goto", url))

            def fill(self, sel, text):
                actions.append(("fill", sel, text))

            def click(self, sel):
                actions.append(("click", sel))

        pub = XhsPublisher(
            selectors={
                "creator_url": "https://creator.test/publish",
                "title_input": "#title",
                "content_editor": "#body",
                "publish_button": ".btn",
            }
        )
        draft = XhsDraft(title="t", body="b")
        outcome = pub.publish(draft, page=FakePage())
        assert outcome == "submitted"
        assert actions[0][0] == "goto"
        assert ("fill", "#title", "t") in actions
        assert ("fill", "#body", "b") in actions
        assert actions[-1][0] == "click"
