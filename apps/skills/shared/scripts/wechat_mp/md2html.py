"""Markdown → 原始 HTML 转换（基于 mistune + Pygments）

将 Markdown 源文件转换为标准 HTML，代码块使用 Pygments 语法高亮。
mistune 的自定义 renderer 可以在转换阶段直接处理代码块，
避免 markdown 库先转义再二次处理导致的 HTML 标签错乱问题。
"""

import re
from pathlib import Path

import mistune
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, guess_lexer, TextLexer


# Pygments 内联样式格式化器（微信公众号不支持 class，必须内联）
_pygments_formatter = HtmlFormatter(
    style="monokai",
    noclasses=True,       # 内联样式，不生成 class
    nowrap=True,          # 不外裹 <pre>，由外层 section 控制布局
    lineseparator="\n",   # 真正的换行符，不用 <br>
)


def _highlight_code(code: str, lang: str = "") -> str:
    """用 Pygments 对代码做语法高亮，返回内联样式的 HTML 片段"""
    try:
        if lang:
            lexer = get_lexer_by_name(lang, stripall=True)
        else:
            lexer = guess_lexer(code)
    except Exception:
        lexer = TextLexer(stripall=True)

    highlighted = highlight(code, lexer, _pygments_formatter)
    # Pygments noclasses+nowrap 模式输出 <div class="highlight"><pre>...</pre></div>
    # 提取 <pre> 内部内容
    m = re.search(r'<pre[^>]*>(.*?)</pre>', highlighted, re.DOTALL)
    if m:
        return m.group(1)
    return highlighted


class WeChatRenderer(mistune.HTMLRenderer):
    """自定义 mistune renderer，代码块使用 Pygments 高亮"""

    def block_code(self, code, info=None, **kwargs):
        """代码块：Pygments 语法高亮 + 深色背景容器"""
        lang = (info or "").strip().split()[0] if info else ""
        highlighted = _highlight_code(code, lang)
        return (
            f'<div style="background:#272822;border-radius:6px;padding:14px 16px;'
            f'margin:0.5em 0;font-size:13px;font-family:\'SF Mono\',Consolas,Monaco,\'Courier New\',monospace;'
            f'line-height:1.7;color:#f8f8f2;">'
            f'<pre style="margin:0;white-space:pre;word-break:break-all;overflow-x:auto;'
            f'font-family:inherit;font-size:inherit;color:inherit;line-height:inherit;">{highlighted}</pre></div>'
            f'<div style="height:12px;"></div>'
        )

    def codespan(self, code):
        """行内代码：深色背景 + 金色文字"""
        return (
            f'<code style="background-color: #282c34; padding: 2px 6px; border-radius: 3px; '
            f"font-size: 13px; font-family: Consolas, Monaco, 'Courier New', monospace; "
            f'color: #e5c07b;">{code}</code>'
        )


# 创建 mistune markdown 实例
# escape=False: 允许 HTML 标签原样通过（图片预处理插入的 <section> 等）
_md = mistune.create_markdown(
    renderer=WeChatRenderer(),
    plugins=["table"],
    escape=False,
)


def _preprocess_image_blocks(md_text: str) -> str:
    """预处理图片+注释块，统一转为单行 <div> HTML

    注意：必须用 <div> 而非 <section>，因为 mistune 只识别 <div> 为 block-level HTML，
    <section> 会被当作 inline HTML 包裹在 <p> 中导致转义。
    """
    def replace_block(m):
        inner = m.group(1)
        img_match = re.search(r'<img\s+([^>]*?)/?>', inner)
        if not img_match:
            return m.group(0)
        img_tag = img_match.group(0)
        src_match = re.search(r'src="([^"]+)"', img_tag)
        alt_match = re.search(r'alt="([^"]+)"', img_tag)
        src = src_match.group(1) if src_match else ''
        alt = alt_match.group(1) if alt_match else ''
        em_match = re.search(r'<em>(.*?)</em>', inner, re.DOTALL)
        caption = em_match.group(1).strip() if em_match else ''
        styled_img = f'<img src="{src}" alt="{alt}" style="width:100%;height:auto;border-radius:4px;display:block;">'
        if caption:
            return (
                f'<div style="text-align:center;margin:0.5em 0;">'
                f'{styled_img}'
                f'<p style="text-align:center;font-size:12px;color:#999;margin:4px 0 0 0;line-height:1.4;">'
                f'{caption}</p></div>'
            )
        return f'<div style="text-align:center;margin:0.5em 0;">{styled_img}</div>'

    md_text = re.sub(
        r'<p\s+align="center">\s*(.*?)\s*</p>',
        replace_block,
        md_text,
        flags=re.DOTALL
    )
    return md_text


def convert_md_to_html(md_text: str) -> str:
    """将 Markdown 转换为原始 HTML（代码块已含 Pygments 高亮）"""

    # 预处理：去掉目录部分（公众号不支持锚点跳转）
    md_text = re.sub(
        r'^##\s+目录\s*\n(?:[ ]*-[^\n]*\n?)+',
        '',
        md_text,
        flags=re.MULTILINE
    )

    # 预处理：去掉 H1 标题（公众号自带标题显示）
    md_text = re.sub(r'^#[^\n]+\n\n?', '', md_text, count=1)

    # 预处理：去掉标题下方的摘要引用块（已单独提取为微信草稿摘要）
    md_text = re.sub(
        r'^(?:>[^\n]*\n)+\n?',
        '',
        md_text
    )

    # 预处理：参考链接 → 参考文章，去掉外链 URL 只保留名称
    # 公众号不支持外链跳转，[文本](url) → 文本
    md_text = re.sub(r'^##\s+参考链接', '## 参考文章', md_text, flags=re.MULTILINE)
    # 将"参考文章"节内的外部链接替换为纯文本
    def _strip_ref_links(m):
        section = m.group(0)
        section = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', section)
        return section
    md_text = re.sub(
        r'## 参考文章\s*\n(?:.*\n?)*',
        _strip_ref_links,
        md_text,
        flags=re.MULTILINE
    )

    # 不再预处理图片块，改为渲染后处理
    html = _md(md_text)

    # 后处理：修复被 <p> 包裹的图片+注释块
    # mistune 会把 <p align="center">...</p> 中的 HTML 转义，
    # 需要还原为正确的图片展示块
    html = _fix_image_blocks(html)

    return html


def _fix_image_blocks(html: str) -> str:
    """修复 mistune 转义的图片+注释块

    mistune 会把 <p align="center">...</p> 块转义为 &lt;p...&gt;...，
    需要还原为正确的居中图片展示 HTML。
    """
    import html as html_mod

    def replace_escaped(m):
        content = m.group(1)
        # 还原 HTML 实体
        content = html_mod.unescape(content)

        img_match = re.search(r'<img\s+([^>]*?)/?>', content)
        if not img_match:
            return m.group(0)
        img_tag = img_match.group(0)
        src_match = re.search(r'src="([^"]+)"', img_tag)
        alt_match = re.search(r'alt="([^"]+)"', img_tag)
        src = src_match.group(1) if src_match else ''
        alt = alt_match.group(1) if alt_match else ''
        em_match = re.search(r'<em>(.*?)</em>', content, re.DOTALL)
        caption = em_match.group(1).strip() if em_match else ''
        styled_img = f'<img src="{src}" alt="{alt}" style="width:100%;height:auto;border-radius:4px;display:block;">'
        if caption:
            return (
                f'<section style="text-align:center;margin:0.5em 0;">'
                f'{styled_img}'
                f'<p style="text-align:center;font-size:12px;color:#999;margin:4px 0 0 0;line-height:1.4;">'
                f'{caption}</p></section>'
            )
        return f'<section style="text-align:center;margin:0.5em 0;">{styled_img}</section>'

    # 匹配任何包含转义 HTML 标签的 <p> 块（如 &lt;div, &lt;section, &lt;p align 等）
    html = re.sub(
        r'<p>(&lt;[a-z][^>]*&gt;.*?)</p>',
        replace_escaped,
        html,
        flags=re.DOTALL
    )

    return html


def wrap_html(content: str, title: str, show_footer: bool = True) -> str:
    """将转换后的内容包装在完整的 HTML 页面中（用于本地预览）"""
    footer = ""
    if show_footer:
        footer = """
        <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0 10px 0;">
        <p style="text-align: center; font-size: 13px; color: #999; margin: 10px 0 0 0;">&mdash; 全文完 &mdash;</p>"""
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>{title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Helvetica Neue", "Microsoft YaHei", sans-serif;
            background: #f5f5f5;
            padding: 0;
        }}
        .article-container {{
            max-width: 680px;
            margin: 0 auto;
            background: #ffffff;
            padding: 30px 24px;
            min-height: 100vh;
        }}
        @media (max-width: 480px) {{
            .article-container {{
                padding: 20px 16px;
            }}
        }}
    </style>
</head>
<body>
    <div class="article-container">
        <div id="article-content">
            {content}
        </div>{footer}
    </div>
</body>
</html>"""


def convert_file(md_path: str | Path, output_dir: str | Path | None = None, show_footer: bool = True) -> Path:
    """转换 Markdown 文件为完整 HTML 页面（用于本地预览）

    Args:
        md_path: Markdown 文件路径
        output_dir: 输出目录（默认为 articles/<stem>/）
        show_footer: 是否显示"全文完"页脚

    Returns:
        生成的 HTML 文件路径
    """
    md_path = Path(md_path)
    md_text = md_path.read_text(encoding="utf-8-sig")

    title_match = re.search(r'^#\s+(.*)', md_text, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else md_path.stem

    content_html = convert_md_to_html(md_text)
    full_html = wrap_html(content_html, title, show_footer=show_footer)

    if output_dir is None:
        output_dir = Path(__file__).parent.parent.parent.parent / "articles" / md_path.stem
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{md_path.stem}.html"
    output_path.write_text(full_html, encoding='utf-8')

    return output_path
