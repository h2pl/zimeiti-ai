"""图片上传模块

将 HTML 中的本地图片上传到微信公众号，替换为微信 CDN URL。
支持 SVG 自动转 PNG（通过 playwright），上传前自动裁剪边缘空白。
"""

import asyncio
import re
import shutil
import tempfile
from pathlib import Path

from wechat_mp import WeChatClient


def _ensure_svg_size(svg: str) -> str:
    """仅含 viewBox、无 width/height 的 SVG 在浏览器中会被容器撑满。

    从 viewBox 补上 width/height，使其按自身尺寸渲染，避免截图被缩放。
    """
    m = re.search(r"<svg\b([^>]*)>", svg)
    if not m:
        return svg
    attrs = m.group(1)
    if "width=" in attrs and "height=" in attrs:
        return svg
    vb = re.search(
        r'viewBox="([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)"', attrs
    )
    if not vb:
        return svg
    w, h = vb.group(3), vb.group(4)
    new_tag = f'<svg width="{w}" height="{h}"{attrs}>'
    return svg[: m.start()] + new_tag + svg[m.end():]


def _svg_to_png(svg_path: Path, png_path: Path) -> bool:
    """将 SVG 文件转换为 PNG

    Args:
        svg_path: SVG 文件路径
        png_path: 输出 PNG 路径

    Returns:
        转换是否成功
    """
    try:
        from playwright.async_api import async_playwright

        async def _convert():
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page(viewport={"width": 1200, "height": 1200})
                svg_content = _ensure_svg_size(svg_path.read_text(encoding="utf-8"))
                page_html = (
                    '<html><body style="margin:0;background:transparent">'
                    + svg_content + "</body></html>"
                )
                await page.set_content(page_html)
                # 强制 SVG 按自身尺寸渲染
                await page.add_style_tag(
                    content="svg{width:auto!important;height:auto!important;max-width:none!important;display:block}"
                )
                # 直接对 svg 元素本身截图，彻底避免视口裁切/缩放
                svg_el = page.locator("svg")
                await svg_el.screenshot(path=str(png_path))
                # 兼容修复：Windows + Python 3.14 下 browser.close() 可能挂起。
                # 截图已完成，close 加超时保护，超时则跳过（进程退出时自动清理）。
                try:
                    await asyncio.wait_for(browser.close(), timeout=5)
                except asyncio.TimeoutError:
                    pass

        asyncio.run(_convert())
        return True
    except ImportError:
        print("  [FAIL] 需要 playwright: pip install playwright && playwright install chromium")
        return False
    except Exception as e:
        print(f"  [FAIL] SVG 转换失败: {e}")
        return False


def upload_local_images(html: str, md_dir: Path, client: WeChatClient) -> str:
    """将 HTML 中的本地图片上传到微信，替换为微信 CDN URL

    遍历 HTML 中所有 <img src="..."> 标签：
    - 跳过远程 URL（http/https）
    - SVG 自动转 PNG 后上传
    - JPG/PNG 直接上传
    - 上传成功后替换 src 为微信 URL

    Args:
        html: HTML 内容
        md_dir: Markdown 文件所在目录（用于解析相对路径）
        client: WeChatClient 实例

    Returns:
        替换后的 HTML
    """
    img_pattern = re.compile(r'<img[^>]*src="([^"]+)"', re.IGNORECASE)
    tmpdir = Path(tempfile.mkdtemp())
    replacements = {}
    try:
        for m in img_pattern.finditer(html):
            src = m.group(1)
            if src.startswith("http"):
                continue

            abs_path = (md_dir / src).resolve()
            if not abs_path.exists():
                print(f"  [WARN] 图片不存在: {abs_path}")
                continue

            # SVG → PNG
            if abs_path.suffix.lower() == ".svg":
                png_path = tmpdir / (abs_path.stem + ".png")
                print(f"  [SVG→PNG] {abs_path.name}")
                if not _svg_to_png(abs_path, png_path):
                    continue
            else:
                # JPG/PNG 直接使用
                png_path = abs_path

            # 上传到微信
            try:
                result = client.upload_image(str(png_path))
                replacements[src] = result["url"]
                print(f"  [UPLOAD] {png_path.name} -> OK")
            except Exception as e:
                print(f"  [FAIL] 上传失败: {e}")

        # 替换图片路径
        for orig_src, wechat_url in replacements.items():
            html = html.replace(f'"{orig_src}"', f'"{wechat_url}"')

    finally:
        if tmpdir.exists():
            shutil.rmtree(tmpdir, ignore_errors=True)

    return html
