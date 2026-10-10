"""多账号 alias 验收（P1⑭，xiaobei accounts.json 对标）。"""


class TestAlias:
    def test_resolve_without_mapping(self, tmp_path, monkeypatch):
        monkeypatch.setattr("zimeiti_api.core.alias.alias_path", lambda: tmp_path / "a.json")
        from zimeiti_api.core import alias as credentials_alias

        assert credentials_alias.resolve("xhs-main") == "xhs-main"

    def test_alias_roundtrip(self, tmp_path, monkeypatch):
        from zimeiti_api.core import alias as credentials_alias

        monkeypatch.setattr("zimeiti_api.core.alias.alias_path", lambda: tmp_path / "a.json")
        credentials_alias.set_alias("主号", "xhs-main")
        assert credentials_alias.resolve("主号") == "xhs-main"
        assert credentials_alias.resolve("gzh-main") == "gzh-main"

    def test_corrupt_map_fails_open_identity(self, tmp_path, monkeypatch):
        from zimeiti_api.core import alias as credentials_alias

        f = tmp_path / "a.json"
        f.write_text("{broken", encoding="utf-8")
        monkeypatch.setattr("zimeiti_api.core.alias.alias_path", lambda: f)
        assert credentials_alias.resolve("xhs-main") == "xhs-main"


# ── gzh 排版主题化（P1⑬） ──────────────────────────────────────────
