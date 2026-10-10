"""风格 DNA 载体与注入验收（P1⑩，xiaobei style-dna 对标）。"""

from zimeiti_api.content import dna


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
        from zimeiti_api.content.creation import build_creation_prompt
        from zimeiti_api.content.topics import select_topic

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
