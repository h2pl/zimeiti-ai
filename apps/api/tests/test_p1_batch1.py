"""P1 批次 1 验收：单篇复盘 / DNA 载体与注入 / 模板沉淀 / 多账号 alias。"""

import pytest

from zimeiti_api import dna, postmortem, templates

# ── 单篇复盘（P1⑨） ────────────────────────────────────────────────


class TestPostmortem:
    @pytest.fixture
    def seeded(self, metrics_db):
        db = metrics_db
        for i, (title, vals) in enumerate(
            [("爆文", [100, 400, 500]), ("扑文", [10, 12, 12]), ("新文", [30])]
        ):
            db.record_event(
                platform="xhs-main",
                title=title,
                source_folder=f"f{i}",
                publish_date=f"2026-10-0{i + 1}",
                profile="xhs-main",
                topic_direction="AI 提效",
            )
            eid = [e for e in db.list_events("xhs-main") if e["title"] == title][0]["id"]
            for j, v in enumerate(vals):
                db.record_snapshot(
                    eid,
                    "xhs-main",
                    "read",
                    v,
                    source="creator-center",
                    captured_at=f"2026-10-09T10:0{j}:00",
                )
        return db

    def test_note_evidence(self, seeded):
        ev = postmortem.note_evidence(seeded, "xhs-main", "爆文")
        assert ev["read_series"] == [100.0, 400.0, 500.0]
        assert ev["lifecycle"] == "稳增型"  # 终值/首值 = 5 ≥ 1.5
        assert ev["peer_mean"] is not None and ev["vs_peers"] is not None

    def test_note_not_found(self, seeded):
        assert postmortem.note_evidence(seeded, "xhs-main", "不存在") is None

    def test_render_note_has_disclaimer(self, seeded):
        md = postmortem.render_note(postmortem.note_evidence(seeded, "xhs-main", "扑文"))
        assert "关联性不等于因果性" in md

    def test_formula_ranking(self, seeded):
        ev = postmortem.top_formula(seeded, "xhs-main")
        assert ev["top"][0]["title"] == "爆文"
        assert ev["top"][0]["read_latest"] == 500.0
        md = postmortem.render_formula(ev)
        assert "样本 3 < 5" in md  # 可信度提示

    def test_formula_insufficient_sample_note(self, seeded):
        ev = postmortem.top_formula(seeded, "xhs-main")
        assert ev["sample"] < 5  # 提示语覆盖在 render 中


# ── DNA 载体（P1⑩） ────────────────────────────────────────────────


class TestDna:
    def test_inject_when_absent(self, monkeypatch, tmp_path):
        monkeypatch.setattr(dna, "dna_path", lambda a: tmp_path / "dna" / f"{a}.dna.md")
        assert dna.inject_dna("CTX", "xhs-main") == "CTX"

    def test_inject_when_present(self, monkeypatch, tmp_path):
        f = tmp_path / "dna" / "xhs-main.dna.md"
        f.parent.mkdir(parents=True)
        f.write_text("## 语气\n克制不吹", encoding="utf-8")
        monkeypatch.setattr(dna, "dna_path", lambda a: f)
        out = dna.inject_dna("CTX", "xhs-main")
        assert "风格 DNA" in out and "克制不吹" in out
        assert out.startswith("CTX")

    def test_creation_prompt_injects_dna(self, monkeypatch, tmp_path):
        from zimeiti_api.creation import build_creation_prompt
        from zimeiti_api.topics import select_topic

        f = tmp_path / "dna" / "xhs-main.dna.md"
        f.parent.mkdir(parents=True)
        f.write_text("## 结构套路\n痛点开场", encoding="utf-8")
        monkeypatch.setattr(dna, "dna_path", lambda a: f)
        profile = {
            "account": "xhs-main",
            "positioning": "AI 工具分享",
            "style": "口语化",
            "audience": "效率工具爱好者",
            "content_focus": "图文",
            "boundary": "不承诺收益",
            "platform_rules": "标题≤20字",
            "preferences": "选题需结合定位",
        }
        prompt = build_creation_prompt(
            select_topic({"title": "t", "reason": "r", "direction": "d"}), profile
        )
        assert "痛点开场" in prompt

    def test_suggest_reads_reports(self, monkeypatch, tmp_path):
        monkeypatch.setattr("zimeiti_api.config.DATA_DIR", str(tmp_path))
        evals = tmp_path / "metrics" / "evals"
        evals.mkdir(parents=True)
        (evals / "xhs-main-all-2026-10-10.eval.md").write_text(
            "- 点赞数：低于均值 0.5x\n- 粉丝数：正常\n", encoding="utf-8"
        )
        suggestions = dna.suggest_from_reports("xhs-main")
        assert len(suggestions) == 1 and "（校准）" in suggestions[0]


# ── 模板沉淀（P1⑫） ────────────────────────────────────────────────


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


class TestAlias:
    def test_resolve_without_mapping(self, tmp_path, monkeypatch):
        monkeypatch.setattr("zimeiti_api.credentials_alias.alias_path", lambda: tmp_path / "a.json")
        from zimeiti_api import credentials_alias

        assert credentials_alias.resolve("xhs-main") == "xhs-main"

    def test_alias_roundtrip(self, tmp_path, monkeypatch):
        from zimeiti_api import credentials_alias

        monkeypatch.setattr("zimeiti_api.credentials_alias.alias_path", lambda: tmp_path / "a.json")
        credentials_alias.set_alias("主号", "xhs-main")
        assert credentials_alias.resolve("主号") == "xhs-main"
        assert credentials_alias.resolve("gzh-main") == "gzh-main"

    def test_corrupt_map_fails_open_identity(self, tmp_path, monkeypatch):
        from zimeiti_api import credentials_alias

        f = tmp_path / "a.json"
        f.write_text("{broken", encoding="utf-8")
        monkeypatch.setattr("zimeiti_api.credentials_alias.alias_path", lambda: f)
        assert credentials_alias.resolve("xhs-main") == "xhs-main"


# ── gzh 排版主题化（P1⑬） ──────────────────────────────────────────


class TestThemes:
    def test_apply_theme_replaces_accent(self):
        from zimeiti_api.themes import apply_theme

        html = '<blockquote style="border-left: 3px solid #2563EB; background-color: #EFF4FF;">'
        themed = apply_theme(html, "sakura")
        assert "#EC4899" in themed and "#FDF2F8" in themed
        assert "#2563EB" not in themed

    def test_default_theme_noop(self):
        from zimeiti_api.themes import apply_theme

        html = "color: #2563EB"
        assert apply_theme(html, "default") == html

    def test_unknown_theme_falls_back_to_default(self):
        from zimeiti_api.themes import apply_theme

        html = "color: #2563EB"
        assert apply_theme(html, "不存在") == html

    def test_gzh_publish_uses_theme(self, monkeypatch):
        """发布管线按 env 主题出稿（端到端冒烟）。"""
        import os

        from zimeiti_api.platforms import gzh

        monkeypatch.setenv("ZIMEITI_GZH_THEME", "sakura")
        html = gzh.apply_theme("<p style='color: #2563EB'>x</p>", os.environ["ZIMEITI_GZH_THEME"])
        assert "#EC4899" in html
