# -*- coding: utf-8 -*-
"""公众号草稿一键生成（逻辑复制自 my-tools/wechat-mp-manage，凭据走 ~/.wechat-mp.json）。

流水线（安全可逆，只建草稿不发布）：
  Markdown → HTML（公众号排版）→ 正文图片上传 → 封面图生成 → 摘要 → thumb 上传 → draft/add

用法（在 apps/api venv 下）:
  python ../skills/shared/scripts/wechat_mp/draft.py <markdown_file> \
      --sub "二级菜单名" [--title 公众号标题] [--series 封面系列名] \
      [--theme ocean] [--author 江小湖] [--digest 摘要] [--out-dir 输出目录]

返回：打印 draft media_id（JSON 行：{"media_id": ..., "cover": ..., "digest": ...}）
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # 使 import wechat_mp 生效

from wechat_mp import WeChatClient  # noqa: E402
from wechat_mp.content_wrapper import wrap_content  # noqa: E402
from wechat_mp.formatting import apply_wechat_styles  # noqa: E402
from wechat_mp.generate_cover_combined import generate_cover_combined as generate_cover  # noqa: E402
from wechat_mp.md2html import convert_md_to_html, wrap_html  # noqa: E402
from wechat_mp.upload_images import upload_local_images  # noqa: E402

DEFAULT_AUTHOR = "江小湖"
DEFAULT_SERIES = "AI Agent 学习+面试指南"
DEFAULT_OUT = Path(__file__).resolve().parents[4] / "outputs" / "wechat-drafts"


def _extract_digest(md_text: str, title: str = "") -> str:
    """从 Markdown 提取摘要（微信限 ~120 字节）：优先标题下引用块，否则第一段。"""
    quote_lines: list[str] = []
    found_title = False
    for line in md_text.split("\n"):
        stripped = line.strip()
        if not found_title:
            if stripped.startswith("# "):
                found_title = True
            continue
        if stripped.startswith(">"):
            quote_lines.append(stripped.lstrip("> ").strip())
        elif quote_lines:
            break
    text = " ".join(q for q in quote_lines if q)
    if not text:
        for line in md_text.split("\n"):
            s = line.strip()
            if s and not s.startswith(("#", ">", "!", "-", "```")):
                text = s
                break
    return text[:54]


def run_draft(
    md_path: Path,
    sub: str,
    title: str = "",
    series: str = DEFAULT_SERIES,
    theme: str = "ocean",
    author: str = DEFAULT_AUTHOR,
    digest: str = "",
    out_dir: Path | None = None,
) -> dict:
    md_text = md_path.read_text(encoding="utf-8-sig")
    if not title:
        m = re.search(r"^#\s+(.*)", md_text, re.MULTILINE)
        title = m.group(1).strip() if m else md_path.stem

    article_dir = (out_dir or DEFAULT_OUT) / md_path.stem
    article_dir.mkdir(parents=True, exist_ok=True)
    client = WeChatClient()

    # Step 1: MD → HTML（内容片段 + 公众号样式 + 本地预览）
    fragment = convert_md_to_html(md_text)
    fragment = apply_wechat_styles(fragment)
    html_path = article_dir / f"{md_path.stem}.html"
    html_path.write_text(wrap_html(fragment, title, show_footer=False), encoding="utf-8")
    print(f"  [OK] HTML: {html_path}")

    # Step 2: 正文图片上传（本地图/SVG→PNG），拼接开场白/结束语/名片
    fragment = upload_local_images(fragment, md_dir=md_path.parent, client=client)
    fragment = wrap_content(fragment, author=author)
    html_path.write_text(wrap_html(fragment, title, show_footer=False), encoding="utf-8")
    print("  [OK] 正文图片与包装完成")

    # Step 3: 封面（拼接 1:1 + 2.35:1，返回裁剪坐标）
    cover_result = generate_cover(
        title=title, sub_series=sub, series=series,
        output_path=article_dir / "cover.png", theme_name=theme,
    )
    if isinstance(cover_result, tuple):
        cover_path, crop_235_1, crop_1_1 = cover_result
    else:
        cover_path, crop_235_1, crop_1_1 = cover_result, "", ""
    print(f"  [OK] 封面: {cover_path}")

    # Step 4: 摘要
    digest = digest or _extract_digest(md_text, title)
    (article_dir / "digest.txt").write_text(digest, encoding="utf-8")
    print(f"  [OK] 摘要: {digest[:40]}…")

    # Step 5: thumb 上传 → 建草稿（幂等：已有 media_id 则更新）
    meta_path = article_dir / "draft_meta.json"
    saved_media_id = None
    if meta_path.exists():
        try:
            saved_media_id = json.loads(meta_path.read_text(encoding="utf-8")).get("media_id")
        except Exception:
            pass

    thumb_media_id = client.upload_thumb(str(cover_path))
    print(f"  [OK] 封面上传: {thumb_media_id}")

    article = {
        "title": title,
        "content": fragment,
        "thumb_media_id": thumb_media_id,
        "digest": digest,
        "author": author,
        "need_open_comment": 1,
        "only_fans_can_comment": 0,
    }
    if crop_235_1:
        article["pic_crop_235_1"] = crop_235_1
    if crop_1_1:
        article["pic_crop_1_1"] = crop_1_1

    if saved_media_id:
        try:
            client.update_draft(saved_media_id, index=0, article=article)
            media_id = saved_media_id
            print(f"  [OK] 草稿已更新: {media_id}")
        except Exception:
            try:
                client.delete_draft(saved_media_id)
            except Exception:
                pass
            media_id = client.add_draft(**article)
            print(f"  [OK] 更新失败回退新建: {media_id}")
    else:
        media_id = client.add_draft(**article)
        print(f"  [OK] 草稿已创建: {media_id}")

    meta_path.write_text(
        json.dumps({"media_id": media_id, "title": title, "author": author,
                    "cover": str(cover_path), "digest": digest},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    # 归因数据源（agent-ops-workflow D2）：草稿创建成功即落发布事实，
    # ops-review 层读 outputs/_analytics/ 做复盘。失败不堵草稿链路。
    try:
        import sys as _sys
        from pathlib import Path as _Path

        _api_dir = _Path(__file__).resolve().parents[3] / "apps" / "api"
        if str(_api_dir) not in _sys.path:
            _sys.path.insert(0, str(_api_dir))
        from zimeiti_api.content.ops_analytics import record_publish

        record_publish(
            platform="wechat-oa",
            content_path=str(md_path.resolve().relative_to(_Path(__file__).resolve().parents[4])),
            media_id=media_id,
            title=title,
        )
        print("  [OK] 归因记录已写入 outputs/_analytics/wechat-oa/")
    except Exception as e:
        print(f"  [!] 归因记录写入失败（无碍）: {e}")
    return {"media_id": media_id, "title": title, "cover": str(cover_path), "digest": digest,
            "html": str(html_path)}


def main() -> None:
    ap = argparse.ArgumentParser(description="公众号草稿一键生成（只建草稿不发布）")
    ap.add_argument("markdown_file")
    ap.add_argument("--sub", required=True, help="封面图二级菜单（如：Agent 实战）")
    ap.add_argument("--title", default="", help="公众号标题（默认取 MD 的 H1）")
    ap.add_argument("--series", default=DEFAULT_SERIES)
    ap.add_argument("--theme", default="ocean")
    ap.add_argument("--author", default=DEFAULT_AUTHOR)
    ap.add_argument("--digest", default="")
    ap.add_argument("--out-dir", default="")
    args = ap.parse_args()
    result = run_draft(
        Path(args.markdown_file), sub=args.sub, title=args.title, series=args.series,
        theme=args.theme, author=args.author, digest=args.digest,
        out_dir=Path(args.out_dir) if args.out_dir else None,
    )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
