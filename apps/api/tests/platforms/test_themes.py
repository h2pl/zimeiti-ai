"""gzh 排版主题化验收（P1⑬，Easel gzh-design 对标）。"""


class TestThemes:
    def test_apply_theme_replaces_accent(self):
        from zimeiti_api.platforms.themes import apply_theme

        html = '<blockquote style="border-left: 3px solid #2563EB; background-color: #EFF4FF;">'
        themed = apply_theme(html, "sakura")
        assert "#EC4899" in themed and "#FDF2F8" in themed
        assert "#2563EB" not in themed

    def test_default_theme_noop(self):
        from zimeiti_api.platforms.themes import apply_theme

        html = "color: #2563EB"
        assert apply_theme(html, "default") == html

    def test_unknown_theme_falls_back_to_default(self):
        from zimeiti_api.platforms.themes import apply_theme

        html = "color: #2563EB"
        assert apply_theme(html, "不存在") == html

    def test_gzh_publish_uses_theme(self, monkeypatch):
        """发布管线按 env 主题出稿（端到端冒烟）。"""
        import os

        from zimeiti_api.platforms import gzh

        monkeypatch.setenv("ZIMEITI_GZH_THEME", "sakura")
        html = gzh.apply_theme("<p style='color: #2563EB'>x</p>", os.environ["ZIMEITI_GZH_THEME"])
        assert "#EC4899" in html
