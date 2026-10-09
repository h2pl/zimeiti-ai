"""gzh-typesetting-pipeline 验收：公众号封面自动生成（vendor my-tools generate_cover_combined）。"""

from pathlib import Path

from zimeiti_api.creation import GzhDraft


class FakeClient:
    """记录调用的假草稿箱客户端。"""

    def __init__(self):
        self.uploaded: list[str] = []
        self.articles: list[list[dict]] = []

    def upload_permanent_image(self, image_path: str) -> str:
        self.uploaded.append(image_path)
        return f"THUMB_{len(self.uploaded)}"

    def add_draft(self, articles):
        self.articles.append(articles)
        return "MEDIA_OK"

    def draft_count(self) -> int:
        return 1


def _pub(tmp_path: Path):
    from zimeiti_api.platforms import gzh

    return gzh


class TestGzhCoverAutoGenerate:
    def test_cover_auto_generated_with_crop_coords(self, tmp_path, monkeypatch):
        """无显式封面且无缓存：生成拼接封面（900×1283 PNG）→ 上传 thumb → 裁剪坐标随草稿上送。"""
        gzh = _pub(tmp_path)
        out_dir = tmp_path / "out"
        monkeypatch.setattr(gzh, "_DEFAULT_COVER_MEDIA_FILE", tmp_path / "no_cache.txt")
        client = FakeClient()
        draft = GzhDraft(title="测试文章标题", body="正文", summary="摘要")

        result = gzh.publish_gzh_draft(client, draft, cover_output_dir=str(out_dir))

        assert result["readback"] == "verified"
        assert len(client.uploaded) == 1
        cover = Path(client.uploaded[0])
        assert cover.exists() and cover.read_bytes()[:4] == b"\x89PNG"
        # 拼接封面规格：宽 900，高 383+900=1283
        data = cover.read_bytes()
        assert data[16:20] == (900).to_bytes(4, "big")
        assert data[20:24] == (1283).to_bytes(4, "big")
        article = client.articles[0][0]
        assert article["thumb_media_id"] == "THUMB_1"
        assert "pic_crop_235_1" in article and "pic_crop_1_1" in article
        # 封面 media_id 缓存
        assert gzh._DEFAULT_COVER_MEDIA_FILE.exists()

    def test_explicit_cover_path_skips_generation(self, tmp_path, monkeypatch):
        """显式提供封面图：直接上传，不生成拼接封面。"""
        gzh = _pub(tmp_path)
        monkeypatch.setattr(gzh, "_DEFAULT_COVER_MEDIA_FILE", tmp_path / "no_cache.txt")
        client = FakeClient()
        explicit = tmp_path / "explicit.png"
        explicit.write_bytes(b"\x89PNG fake")

        gzh.publish_gzh_draft(
            client,
            GzhDraft(title="t", body="b", summary="s"),
            cover_image_path=str(explicit),
            cover_output_dir=str(tmp_path / "out"),
        )

        assert client.uploaded == [str(explicit)]
        assert "pic_crop_235_1" not in client.articles[0][0]

    def test_cached_media_id_reused_without_upload(self, tmp_path, monkeypatch):
        """已有缓存 media_id：复用且不上传任何图片（现有行为保持）。"""
        gzh = _pub(tmp_path)
        cache = tmp_path / "cache.txt"
        cache.write_text("CACHED_THUMB", encoding="utf-8")
        monkeypatch.setattr(gzh, "_DEFAULT_COVER_MEDIA_FILE", cache)
        client = FakeClient()

        gzh.publish_gzh_draft(
            client,
            GzhDraft(title="t", body="b", summary="s"),
            cover_output_dir=str(tmp_path / "out"),
        )

        assert client.uploaded == []
        assert client.articles[0][0]["thumb_media_id"] == "CACHED_THUMB"

    def test_markdown_body_typeset_to_inline_html(self, tmp_path, monkeypatch):
        """正文排版（前一变更已接入）：Markdown → 内联样式 HTML（回归保护）。"""
        gzh = _pub(tmp_path)
        monkeypatch.setattr(gzh, "_DEFAULT_COVER_MEDIA_FILE", tmp_path / "no_cache.txt")
        client = FakeClient()
        body = "# 标题\n\n```python\nprint(1)\n```\n\n- 列表项\n"

        gzh.publish_gzh_draft(
            client,
            GzhDraft(title="t", body=body, summary="s"),
            cover_output_dir=str(tmp_path / "out"),
        )

        content = client.articles[0][0]["content"]
        assert 'style="' in content
        assert "class=" not in content  # 微信不支持 class
        assert "#272822" in content  # monokai 代码块深色背景

    def test_vendor_provenance_headers(self):
        """vendor 模块标注上游来源（铁律：引用注明出处）。"""
        vendor = Path(__file__).resolve().parents[1] / "src/zimeiti_api/vendor/wechatfmt"
        header = (vendor / "generate_cover_combined.py").read_text(encoding="utf-8")[:400]
        assert "my-tools/wechat-mp-manage" in header
