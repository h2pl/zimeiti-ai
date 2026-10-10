"""模板库验收（P1⑫，Easel template-library 对标）。"""

import pytest

from zimeiti_api.content import templates


class TestTemplates:
    def test_save_list_render(self, tmp_path, monkeypatch):
        monkeypatch.setattr(templates, "_store_path", lambda: tmp_path / "t.json")
        templates.save("痛点开场", "{{hook}}\n\n{{body}}", note="爆款结构")
        names = [t["name"] for t in templates.list_templates()]
        assert "痛点开场" in names
        out = templates.render("痛点开场", {"hook": "我受够了", "body": "正文"})
        assert out == "我受够了\n\n正文"

    def test_render_missing_var_fails_closed(self, tmp_path, monkeypatch):
        monkeypatch.setattr(templates, "_store_path", lambda: tmp_path / "t.json")
        templates.save("t", "{{a}} {{b}}")
        with pytest.raises(ValueError, match="缺少变量"):
            templates.render("t", {"a": "1"})

    def test_render_unknown_template(self, tmp_path, monkeypatch):
        monkeypatch.setattr(templates, "_store_path", lambda: tmp_path / "t.json")
        with pytest.raises(KeyError):
            templates.render("nope", {})


# ── 多账号 alias（P1⑭） ────────────────────────────────────────────
