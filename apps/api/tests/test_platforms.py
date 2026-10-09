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


class TestXhs:
    def test_parse_readback_found(self):
        from zimeiti_api.platforms.xhs import parse_readback

        assert parse_readback(["AI 提效指南", "其他"], "AI 提效指南") == "verified"
        assert parse_readback(["其他"], "AI 提效指南") == "unverified"

    def test_publish_flow_order_with_fake_page(self):
        from zimeiti_api.creation import XhsDraft
        from zimeiti_api.platforms.xhs import XhsPublisher

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
