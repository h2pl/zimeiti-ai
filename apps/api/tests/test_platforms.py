"""Task 6.2/6.3 验收：公众号草稿箱上传（vendor my-tools 排版管线）+ 小红书发布框架读回。"""

from zimeiti_api.creation import GzhDraft


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
        if "发布笔记" in self.sel or ".publishBtn" in self.sel:
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
    def test_parse_readback_found(self):
        from zimeiti_api.platforms.xhs import parse_readback

        assert parse_readback(["AI 提效指南", "其他"], "AI 提效指南") == "verified"
        assert parse_readback(["其他"], "AI 提效指南") == "unverified"

    def test_publish_draft_flow_order(self, tmp_path):
        """DOM 存草稿流程：切图文 tab → 上传封面 → 等编辑器 → 标题 → 正文 → 存草稿。"""
        from zimeiti_api.creation import XhsDraft
        from zimeiti_api.platforms.xhs import XhsPublisher, make_cover_png

        actions = []
        fake = _FakePage(actions)
        cover = make_cover_png(tmp_path / "cover.png")
        pub = XhsPublisher(storage_state=str(tmp_path / "state.json"))
        outcome = pub.publish_draft(
            XhsDraft(title="标" * 30, body="第一行\n第二行"),
            page=fake,
            cover_path=str(cover),
        )
        assert outcome == "submitted_private"
        kinds = [a[0] for a in actions]
        assert kinds.index("click_tab") < kinds.index("upload") < kinds.index("fill")
        # 私密发布序列：可见性切换 → 仅自己可见 → 发布
        assert "click_visibility" in kinds and "click_private" in kinds
        assert "click_publish" in kinds
        assert kinds.index("click_private") < kinds.index("click_publish")
        fill = next(a for a in actions if a[0] == "fill")
        assert len(fill[2]) <= 20  # 标题截断到 20 字
        typed = "".join(a[1] for a in actions if a[0] == "type")
        assert "第一行" in typed and "第二行" in typed

    def test_publish_flow_clicks_publish_button(self, tmp_path):
        from zimeiti_api.creation import XhsDraft
        from zimeiti_api.platforms.xhs import XhsPublisher, make_cover_png

        actions = []
        fake = _FakePage(actions)
        cover = make_cover_png(tmp_path / "cover.png")
        pub = XhsPublisher(storage_state=str(tmp_path / "state.json"))
        outcome = pub.publish(XhsDraft(title="t", body="b"), page=fake, cover_path=str(cover))
        assert outcome == "submitted"
        assert actions[-2][0] == "click_publish"
        assert "发布笔记" in actions[-2][1] or ".publishBtn" in actions[-2][1]

    def test_publish_missing_image_tab_raises(self, tmp_path):
        from zimeiti_api.creation import XhsDraft
        from zimeiti_api.platforms.xhs import XhsPublisher, make_cover_png

        actions = []
        fake = _FakePage(actions, tabs_visible=False)
        cover = make_cover_png(tmp_path / "cover.png")
        pub = XhsPublisher(storage_state=str(tmp_path / "state.json"))
        try:
            pub.publish_draft(XhsDraft(title="t", body="b"), page=fake, cover_path=str(cover))
            raise AssertionError("应抛 RuntimeError")
        except RuntimeError as exc:
            assert "上传图文" in str(exc)

    def test_readback_with_fake_page(self, tmp_path):
        from zimeiti_api.platforms.xhs import XhsPublisher

        actions = []
        fake = _FakePage(actions, body="草稿箱列表：把选题到发布交给了一个Agent")
        pub = XhsPublisher(storage_state=str(tmp_path / "state.json"))
        assert pub.readback("把选题到发布交给了一个Agent", page=fake) == "verified"
        assert pub.readback("不存在的标题", page=fake) == "unverified"
