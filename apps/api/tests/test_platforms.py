"""Task 6.2/6.3 验收：公众号草稿箱上传（vendor my-tools 排版管线）+ 小红书发布框架读回。"""

from pathlib import Path

from zimeiti_api.creation import GzhDraft, XhsDraft


class TestGzh:
    def test_publish_draft_verified(self, monkeypatch, tmp_path):
        from zimeiti_api.platforms import gzh

        draft_payloads = []
        client = gzh.GzhClient("appid", "secret", token_cache=tmp_path / "token.json")
        # token 缓存路径直传 toolkit，不再落到 cwd
        assert client._client._token_cache_path == tmp_path / "token.json"
        monkeypatch.setattr(client._client, "get_access_token", lambda force=False: "TOKEN123")

        def fake_add_draft(**kw):
            draft_payloads.append(kw)
            return "MEDIA_001"

        monkeypatch.setattr(client._client, "add_draft", fake_add_draft)
        monkeypatch.setattr(client._client, "count_drafts", lambda: 3)
        monkeypatch.setattr(gzh, "_DEFAULT_COVER_MEDIA_FILE", tmp_path / "no_cover.txt")

        draft = GzhDraft(title="AI 提效指南", body="正文内容", summary="摘要")
        result = gzh.publish_gzh_draft(client, draft)
        assert result["platform_result"] == "MEDIA_001"
        assert result["readback"] == "verified"
        assert draft_payloads[0]["title"] == "AI 提效指南"
        # 正文经 vendor 排版管线转为微信兼容 HTML（内联样式），不再是裸 <p> 包裹
        assert "正文内容" in draft_payloads[0]["content"]
        assert 'style="' in draft_payloads[0]["content"]

    def test_publish_accepts_dict_draft(self, monkeypatch, tmp_path):
        """真实发布路径从 drafts.json 读回的是 dict，publish 必须兼容。"""
        from zimeiti_api.platforms import gzh

        seen = {}
        client = gzh.GzhClient("appid", "secret", token_cache=tmp_path / "token.json")
        monkeypatch.setattr(client._client, "get_access_token", lambda force=False: "T")

        def fake_add_draft(**kw):
            seen.update(kw)
            return "MEDIA_D"

        monkeypatch.setattr(client._client, "add_draft", fake_add_draft)
        monkeypatch.setattr(client._client, "count_drafts", lambda: 1)
        monkeypatch.setattr(gzh, "_DEFAULT_COVER_MEDIA_FILE", tmp_path / "no_cover.txt")

        result = gzh.publish_gzh_draft(client, {"title": "标题", "body": "正文", "summary": "摘要"})
        assert result["platform_result"] == "MEDIA_D"
        assert seen["title"] == "标题"

    def test_publish_draft_cover_upload_and_cache(self, monkeypatch, tmp_path):
        from zimeiti_api.platforms import gzh

        client = gzh.GzhClient("appid", "secret", token_cache=tmp_path / "token.json")
        cover = tmp_path / "cover.png"
        cover.write_bytes(b"png")
        kw_seen = {}
        monkeypatch.setattr(client._client, "get_access_token", lambda force=False: "TOKEN123")
        monkeypatch.setattr(client._client, "add_material", lambda path: {"media_id": "THUMB_001"})

        def fake_add_draft(**kw):
            kw_seen.update(kw)
            return "MEDIA_002"

        monkeypatch.setattr(client._client, "add_draft", fake_add_draft)
        monkeypatch.setattr(client._client, "count_drafts", lambda: 1)
        cover_cache = tmp_path / "cover_media.txt"
        monkeypatch.setattr(gzh, "_DEFAULT_COVER_MEDIA_FILE", cover_cache)

        draft = GzhDraft(title="t", body="b", summary="s")
        gzh.publish_gzh_draft(client, draft, cover_image_path=str(cover))
        assert kw_seen["thumb_media_id"] == "THUMB_001"
        assert cover_cache.read_text(encoding="utf-8") == "THUMB_001"

    def test_publish_draft_unverified_when_count_zero(self, monkeypatch, tmp_path):
        from zimeiti_api.platforms import gzh

        client = gzh.GzhClient("appid", "secret", token_cache=tmp_path / "token.json")
        monkeypatch.setattr(client._client, "get_access_token", lambda force=False: "T")
        monkeypatch.setattr(client._client, "add_draft", lambda **kw: "M")
        monkeypatch.setattr(client._client, "count_drafts", lambda: 0)
        monkeypatch.setattr(gzh, "_DEFAULT_COVER_MEDIA_FILE", tmp_path / "no_cover.txt")
        draft = GzhDraft(title="t", body="b", summary="s")
        result = gzh.publish_gzh_draft(client, draft)
        assert result["readback"] == "unverified"


class TestGzhFormatPipeline:
    """vendor 排版管线（my-tools/wechat-mp-manage 移植）冒烟。"""

    def test_markdown_code_block_gets_wechat_inline_styles(self):
        from zimeiti_api.vendor.wechatfmt import apply_wechat_styles, convert_md_to_html

        md = "# 文章\n\n```python\nprint(1)\n```\n"
        html = apply_wechat_styles(convert_md_to_html(md))
        assert "print" in html
        assert "#272822" in html  # Pygments monokai 深色代码块容器（内联样式）
        assert "class=" not in html  # 微信不支持 class，必须全内联

    def test_h2_and_list_rendered_with_inline_styles(self):
        from zimeiti_api.vendor.wechatfmt import apply_wechat_styles, convert_md_to_html

        md = "# 文章\n\n## 小节\n\n- 第一条\n- 第二条\n"
        html = apply_wechat_styles(convert_md_to_html(md))
        assert "小节" in html
        assert "第一条" in html
        assert "<ul" not in html  # 列表被转为 div，避免微信渲染多余黑点


class _FakeLocator:
    """模拟 Playwright Locator（支持 tab 可见性/accept 属性判定路径）。"""

    def __init__(self, actions, sel, texts=None, accept=".jpg,.png,image", visible=True):
        self._actions = actions
        self.sel = sel
        self._texts = texts or ["上传图文"]
        self._accept = accept
        self._visible = visible

    @property
    def first(self):
        return self

    def all(self):
        return [self]

    def inner_text(self):
        return self._texts[0] if self._texts else ""

    def is_visible(self):
        return self._visible

    def get_attribute(self, name):
        return self._accept if name == "accept" else None

    def set_input_files(self, files):
        self._actions.append(("upload", self.sel, files))

    def click(self, timeout=None):
        if "btn-wrapper" in self.sel or "发布笔记" in self.sel or ".publishBtn" in self.sel:
            self._actions.append(("click_publish", self.sel))
        elif "creator-tab" in self.sel:
            self._actions.append(("click_tab", self.sel))
        elif "仅自己可见" in self.sel:
            self._actions.append(("click_private", self.sel))
        elif "公开可见" in self.sel:
            self._actions.append(("click_visibility", self.sel))
        else:
            self._actions.append(("click", self.sel))

    def fill(self, text):
        self._actions.append(("fill", self.sel, text))


class _FakeKeyboard:
    def __init__(self, actions):
        self._actions = actions

    def press(self, key):
        self._actions.append(("key", key))

    def type(self, text):
        self._actions.append(("type", text))


class _FakePage:
    def __init__(self, actions, body="", tabs_visible=True):
        self.keyboard = _FakeKeyboard(actions)
        self._actions = actions
        self._body = body
        self._tabs_visible = tabs_visible

    def on(self, event, handler):
        """模拟站点响应回调（发布请求立即成功返回）。"""

        class _R:
            url = "https://edith.xiaohongshu.com/web_api/sns/v2/note"
            status = 200

            def text(self):
                return (
                    '{"success":true,"msg":"","data":{"id":"NOTE_X","score":10},'
                    '"share_link":"https://www.xiaohongshu.com/discovery/item/NOTE_X"}'
                )

        handler(_R())

    def goto(self, url):
        self._actions.append(("goto", url))

    def wait_for_selector(self, sel, timeout=None, state=None):
        self._actions.append(("wait", sel))

    def wait_for_timeout(self, ms):
        self._actions.append(("wait_ms", ms))

    def locator(self, sel):
        if "creator-tab" in sel:
            return _FakeLocator(self._actions, sel, visible=self._tabs_visible)
        if "input[type='file']" in sel:
            return _FakeLocator(
                self._actions,
                sel,
                accept="" if not self._tabs_visible else ".jpg,.png,image",
                visible=self._tabs_visible,
            )
        return _FakeLocator(self._actions, sel)

    def inner_text(self, sel):
        return self._body


class TestXhs:
    """XhsPublisher = xiaohongshu-mcp 本地服务的 API 客户端。"""

    def test_parse_readback_found(self):
        from zimeiti_api.platforms.xhs import parse_readback

        assert parse_readback(["AI 提效指南", "其他"], "AI 提效指南") == "verified"
        assert parse_readback(["其他"], "AI 提效指南") == "unverified"

    def _pub(self, tmp_path):
        from zimeiti_api.platforms.xhs import XhsPublisher

        return XhsPublisher(
            base_url="http://localhost:18060",
            token="T",
            storage_state=str(tmp_path / "state.json"),
        )

    def test_publish_draft_calls_mcp_api_with_private_visibility(self, tmp_path, monkeypatch):
        from zimeiti_api.platforms.xhs import make_cover_png

        cover = make_cover_png(tmp_path / "cover.png")
        seen = {}

        class FakeResp:
            def json(self):
                return {
                    "success": True,
                    "message": "发布成功",
                    "data": {"status": "success", "title": "x"},
                }

        def fake_post(url, json=None, headers=None, timeout=None):
            seen.update(url=url, payload=json, headers=headers)
            return FakeResp()

        monkeypatch.setattr("zimeiti_api.platforms.xhs.requests.post", fake_post)
        pub = self._pub(tmp_path)
        res = pub.publish_draft(
            XhsDraft(title="标" * 30, body="正文", tags=["t1", "t2"]),
            cover_path=str(cover),
        )
        assert seen["url"].endswith("/api/v1/publish")
        assert seen["payload"]["visibility"] == "仅自己可见"  # 宪法 I
        assert len(seen["payload"]["title"]) <= 20
        assert seen["payload"]["images"] == [str(Path(cover).resolve())]
        assert seen["payload"]["tags"] == ["t1", "t2"]
        assert seen["headers"]["Authorization"] == "Bearer T"
        assert res["raw"]["success"] is True

    def test_publish_public_visibility(self, tmp_path, monkeypatch):
        seen = {}

        class FakeResp:
            def json(self):
                return {"success": True, "data": {"status": "success"}}

        def fake_post(url, json=None, headers=None, timeout=None):
            seen.update(payload=json)
            return FakeResp()

        monkeypatch.setattr("zimeiti_api.platforms.xhs.requests.post", fake_post)
        self._pub(tmp_path).publish(
            XhsDraft(title="t", body="b"), cover_path=str(tmp_path / "c.png")
        )
        assert seen["payload"]["visibility"] == "公开可见"

    def test_publish_accepts_dict_draft(self, tmp_path, monkeypatch):
        seen = {}

        class FakeResp:
            def json(self):
                return {"success": True, "data": {}}

        def fake_post(url, json=None, headers=None, timeout=None):
            seen.update(payload=json)
            return FakeResp()

        monkeypatch.setattr("zimeiti_api.platforms.xhs.requests.post", fake_post)
        self._pub(tmp_path).publish_draft(
            {"title": "标题", "body": "正文"}, cover_path=str(tmp_path / "c.png")
        )
        assert seen["payload"]["title"] == "标题"

    def test_publish_failure_raises(self, tmp_path, monkeypatch):
        class FakeResp:
            def json(self):
                return {"success": False, "message": "发布失败", "error": "标题超限"}

        monkeypatch.setattr(
            "zimeiti_api.platforms.xhs.requests.post",
            lambda url, json=None, headers=None, timeout=None: FakeResp(),
        )
        try:
            self._pub(tmp_path).publish_draft(
                XhsDraft(title="t", body="b"), cover_path=str(tmp_path / "c.png")
            )
            raise AssertionError("应抛 RuntimeError")
        except RuntimeError as exc:
            assert "发布失败" in str(exc)

    def test_readback_with_fake_page(self, tmp_path):
        class FakeLocator:
            def all(self):
                return []

        class FakePage:
            def goto(self, url):
                pass

            def wait_for_timeout(self, ms):
                pass

            def locator(self, sel):
                return FakeLocator()

            def inner_text(self, sel):
                return "笔记管理：我把选题到发布交给了一个AI助手"

        pub = self._pub(tmp_path)
        assert pub.readback("我把选题到发布交给了一个AI助手", page=FakePage()) == "verified"
        assert pub.readback("不存在的标题", page=FakePage()) == "unverified"
