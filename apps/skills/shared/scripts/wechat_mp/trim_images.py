"""图片预处理脚本（通用版）

处理 Markdown 中引用的本地图片：
- SVG → PNG（透明背景）+ 裁剪 + 补透明边距
- PNG（RGBA）→ 裁剪透明空白 + 补透明边距
- PNG/JPG（RGB）→ 裁剪白色边缘 + 补白色边距

用法:
  python scripts/trim_svg_images.py <markdown_file>
"""

import asyncio
import re
import sys
from pathlib import Path

from PIL import Image
from playwright.async_api import async_playwright


def svg_to_png(svg_path: Path, png_path: Path):
    """SVG → PNG（透明背景）"""
    async def _convert():
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={"width": 800, "height": 520})
            page_html = (
                '<html><body style="margin:0;background:transparent">'
                + svg_path.read_text(encoding="utf-8")
                + "</body></html>"
            )
            await page.set_content(page_html)
            await page.screenshot(path=str(png_path), full_page=False, omit_background=True)
            await browser.close()
    asyncio.run(_convert())


def trim_and_pad(image_path: Path, padding: int = 30, white_threshold: int = 240):
    """裁剪边缘空白 + 补回统一内边距

    - RGBA 图片：裁剪透明空白，补透明边距
    - RGB 图片：裁剪白色边缘，补白色边距
    """
    img = Image.open(image_path)
    data = img.load()
    w, h = img.size

    if img.mode == "RGBA":
        bg_color = (0, 0, 0, 0)

        def is_blank(pixel):
            return pixel[3] < 10
    else:
        img_rgb = img.convert("RGB")
        data = img_rgb.load()
        bg_color = (255, 255, 255)

        def is_blank(pixel):
            return all(c >= white_threshold for c in pixel)

    # 找内容边界
    top = 0
    for y in range(h):
        if all(is_blank(data[x, y]) for x in range(w)):
            top = y + 1
        else:
            break

    bottom = h
    for y in range(h - 1, -1, -1):
        if all(is_blank(data[x, y]) for x in range(w)):
            bottom = y
        else:
            break

    if top == h:
        print(f"    [SKIP] 全空白图片")
        return

    left = 0
    for x in range(w):
        if all(is_blank(data[x, y]) for y in range(top, bottom)):
            left = x + 1
        else:
            break

    right = w
    for x in range(w - 1, -1, -1):
        if all(is_blank(data[x, y]) for y in range(top, bottom)):
            right = x
        else:
            break

    # 裁剪 + 补边距
    if img.mode == "RGBA":
        content = img.crop((left, top, right, bottom))
    else:
        content = img_rgb.crop((left, top, right, bottom))

    new_w = content.width + padding * 2
    new_h = content.height + padding * 2
    new_img = Image.new(img.mode if img.mode == "RGBA" else "RGB", (new_w, new_h), bg_color)
    new_img.paste(content, (padding, padding))
    new_img.save(image_path)
    print(f"    {w}x{h} -> {new_w}x{new_h} (content: {right-left}x{bottom-top}, pad: {padding}px)")


def main():
    if len(sys.argv) < 2:
        print("用法: python trim_svg_images.py <markdown_file>")
        sys.exit(1)

    md_path = Path(sys.argv[1])
    md_dir = md_path.parent
    md_text = md_path.read_text(encoding="utf-8")

    # 匹配所有本地图片引用（HTML img 和 Markdown 语法）
    html_pattern = re.compile(r'src="([^"]+\.(svg|png|jpg|jpeg))"', re.IGNORECASE)
    md_pattern = re.compile(r'!\[[^\]]*\]\(([^)]+\.(svg|png|jpg|jpeg))\)', re.IGNORECASE)

    sources = set()
    for m in html_pattern.finditer(md_text):
        sources.add(m.group(1))
    for m in md_pattern.finditer(md_text):
        sources.add(m.group(1))

    # 过滤远程图片
    sources = sorted(s for s in sources if not s.startswith("http"))

    if not sources:
        print("未找到本地图片引用")
        return

    print(f"找到 {len(sources)} 个图片引用\n")

    new_md_text = md_text
    processed = 0

    for src in sources:
        abs_path = (md_dir / src).resolve()
        if not abs_path.exists():
            print(f"  [WARN] 不存在: {abs_path}")
            continue

        suffix = abs_path.suffix.lower()
        print(f"  {abs_path.name}")

        if suffix == ".svg":
            # SVG → PNG + trim
            png_path = abs_path.with_suffix(".png")
            svg_to_png(abs_path, png_path)
            trim_and_pad(png_path)

            # 替换 MD 引用
            new_src = src.rsplit(".", 1)[0] + ".png"
            new_md_text = new_md_text.replace(src, new_src)

            # 删除 SVG
            abs_path.unlink()
            processed += 1

        elif suffix in (".png", ".jpg", ".jpeg"):
            # 裁剪 + padding
            trim_and_pad(abs_path)
            processed += 1

    if new_md_text != md_text:
        md_path.write_text(new_md_text, encoding="utf-8")
        print(f"\n[OK] MD 已更新，处理了 {processed} 张图片")
    else:
        print(f"\n[OK] 处理了 {processed} 张图片")


if __name__ == "__main__":
    main()
