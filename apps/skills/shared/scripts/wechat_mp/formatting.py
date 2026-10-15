"""微信公众号富文本格式化

为 HTML 元素应用微信兼容的内联样式。
微信公众号编辑器不支持 CSS class，只能接受内联样式。

排版原则：
  - 紧凑不拥挤：减少无意义留白，靠视觉层级而非间距区分内容
  - 信息密度优先：公众号阅读场景下，一屏看到更多内容
  - 层级靠样式区分：颜色、背景、边框比纯留白更有效
"""

import re

from bs4 import BeautifulSoup

ARTICLE_THEMES = {
    "sunset": {
        "accent": "#FF9650", "bg_light": "#FFF0E5",
        "bg_lighter": "#FFF5EB", "table_text": "#C07130",
    },
    "ocean": {
        "accent": "#2563EB", "bg_light": "#E8F0FE",
        "bg_lighter": "#EFF4FF", "table_text": "#1A4A9A",
    },
    "midnight": {
        "accent": "#A080E0", "bg_light": "#F0E8FF",
        "bg_lighter": "#F5F0FF", "table_text": "#7050B0",
    },
    "forest": {
        "accent": "#46DC96", "bg_light": "#E8F5EC",
        "bg_lighter": "#EEF8F0", "table_text": "#1A8A4A",
    },
    "aurora": {
        "accent": "#5EEAD4", "bg_light": "#E8FCF8",
        "bg_lighter": "#F0FDFA", "table_text": "#0D9488",
    },
}

_DEFAULT_THEME = "ocean"


def _theme_val(key: str, theme: str | None) -> str:
    t = ARTICLE_THEMES.get(theme, ARTICLE_THEMES[_DEFAULT_THEME])
    return t[key]


def _s(theme: str | None, key: str) -> str:
    return _theme_val(key, theme)


def _style_img(attrs: str) -> str:
    """为 <img> 标签应用全宽样式，确保图片清晰可见"""
    # 如果已有 style，注入关键样式；否则新增
    if 'style="' in attrs:
        # 替换 max-width 为 width:100%，确保撑满
        attrs = re.sub(r'max-width:\s*100%', 'width:100%', attrs)
        if 'width:' not in attrs:
            attrs = attrs.replace('style="', 'style="width:100%;')
        if 'display:' not in attrs:
            attrs = attrs.replace('style="', 'style="display:block;')
    else:
        attrs += ' style="width:100%;height:auto;display:block;"'
    return f'<img {attrs}>'


def _convert_lists_to_divs(raw_html: str, theme: str | None = None) -> str:
    """将所有 <ul>/<ol>/<li> 转换为 <div>，避免微信自动识别为列表并渲染多余黑点。"""
    a = _s(theme, "accent")

    soup = BeautifulSoup(raw_html, "html.parser")

    def _process_list(list_tag, depth: int = 0) -> str:
        parts = []
        item_idx = 1
        for li in list_tag.find_all("li", recursive=False):
            # 分离当前 <li> 的直接文本/行内内容与嵌套列表
            content = []
            nested_lists = []
            for child in li.children:
                if getattr(child, "name", None) in ("ul", "ol"):
                    nested_lists.append(child)
                else:
                    content.append(str(child))

            content_html = "".join(content).strip()
            # 去掉 mistune 在 <li> 里可能包裹的 <p>
            content_html = re.sub(r"<p[^>]*>(.*?)</p>", r"\1", content_html, flags=re.DOTALL)
            # 清理 .md 链接
            content_html = re.sub(r'<a\s+href="[^"]*\.md[^"]*"[^>]*>(.*?)</a>', r'\1', content_html)

            if list_tag.name == "ul":
                prefix = f'<span style="color:{a}">•</span> '
            else:
                prefix = f"{item_idx}. "
                item_idx += 1

            margin_left = f"{depth * 1.2:.1f}em"
            parts.append(
                f'<div style="margin:0.5em 0; margin-left:{margin_left}; '
                f'font-size:16px; line-height:1.75; color:#3f3f3f; letter-spacing:0.5px;">'
                f'{prefix}{content_html}</div>'
            )

            for nested in nested_lists:
                parts.append(_process_list(nested, depth + 1))

        return "\n".join(parts)

    # 只处理最外层列表；嵌套列表由递归自然处理，避免被重复替换
    for list_tag in soup.find_all(["ul", "ol"]):
        if list_tag.find_parent(["ul", "ol"]) is not None:
            continue
        replacement = BeautifulSoup(_process_list(list_tag, depth=0), "html.parser")
        list_tag.replace_with(replacement)

    return str(soup)


def apply_wechat_styles(raw_html: str, theme: str | None = None) -> str:
    """为 HTML 内容应用微信公众号兼容的内联样式"""
    a = _s(theme, "accent")
    bg = _s(theme, "bg_light")
    bg2 = _s(theme, "bg_lighter")
    tt = _s(theme, "table_text")

    # 移除以 # 开头的锚点链接，仅保留文字
    raw_html = re.sub(
        r'<a\s+href="#[^"]*"[^>]*>(.*?)</a>',
        r'\1',
        raw_html
    )

    # 移除所有 target="_blank"
    raw_html = re.sub(r'\s+target="_blank"', '', raw_html)

    # H1：居中标题
    raw_html = re.sub(
        r'<h1[^>]*>(.*?)</h1>',
        r'<section style="text-align: center; margin: 0.5em 0; font-size: 22px; font-weight: bold; color: #1a1a1a;">\1</section>',
        raw_html
    )

    # H2：纯色背景 + 左色条
    raw_html = re.sub(
        r'<h2[^>]*>(.*?)</h2>',
        f'<section style="margin: 0.5em 0; padding: 6px 12px; font-size: 18px; font-weight: bold; color: #1a1a1a; background-color: {bg}; border-left: 4px solid {a}; border-radius: 0 4px 4px 0;">\\1</section>',
        raw_html
    )

    # H3：加粗 + accent 色
    raw_html = re.sub(
        r'<h3[^>]*>(.*?)</h3>',
        f'<section style="margin: 0.5em 0; font-size: 17px; font-weight: bold; color: {a};">\\1</section>',
        raw_html
    )

    # H4-H6
    raw_html = re.sub(
        r'<h[4-6][^>]*>(.*?)</h[4-6]>',
        r'<section style="margin: 0.5em 0; font-size: 16px; font-weight: bold; color: #555;">\1</section>',
        raw_html
    )

    # 段落：16px 正文
    raw_html = re.sub(
        r'<p>(.*?)</p>',
        r'<p style="margin: 0.5em 0; line-height: 1.8; font-size: 16px; color: #3f3f3f; letter-spacing: 0.5px;">\1</p>',
        raw_html,
        flags=re.DOTALL
    )

    # 图片：全宽显示
    raw_html = re.sub(
        r'<img\s+([^>]*?)>',
        lambda m: _style_img(m.group(1)),
        raw_html
    )

    # 代码块和行内代码已由 mistune renderer 处理，无需再处理

    # 表格：浅色表头，紧凑行距
    def replace_table(m):
        content = m.group(1)
        content = re.sub(r'<th>(.*?)</th>', f'<th style="background-color: {bg}; color: {tt}; padding: 7px 10px; text-align: left; font-weight: 600; white-space: nowrap; font-size: 14px;">\\1</th>', content)
        content = re.sub(r'<td>(.*?)</td>', r'<td style="padding: 6px 10px; border-bottom: 1px solid #f0f0f0; color: #333; font-size: 14px;">\1</td>', content)
        content = re.sub(r'<tr>', r'<tr>', content)
        return f'<div style="overflow-x: auto; margin: 0.5em 0; border: 1px solid #e8e8e8; border-radius: 4px;"><table style="width: 100%; border-collapse: collapse; font-size: 14px; min-width: 500px;">{content}</table></div>'

    raw_html = re.sub(
        r'<table>(.*?)</table>',
        replace_table,
        raw_html,
        flags=re.DOTALL
    )

    # 引用：浅色背景 + 左色条，文本样式与正文一致
    def replace_blockquote(m):
        content = m.group(1)
        content = re.sub(
            r'<p[^>]*>',
            '<p style="margin: 0; line-height: 1.8; font-size: 16px; color: #3f3f3f; letter-spacing: 0.5px;">',
            content
        )
        content = re.sub(r'<br\s*/?>', '', content)
        return f'<blockquote style="margin: 0.5em 0; padding: 8px 14px; background-color: {bg2}; border-left: 3px solid {a}; color: #3f3f3f; font-size: 16px; line-height: 1.8; letter-spacing: 0.5px; border-radius: 0 4px 4px 0;">{content}</blockquote>'

    raw_html = re.sub(
        r'<blockquote>(.*?)</blockquote>',
        replace_blockquote,
        raw_html,
        flags=re.DOTALL
    )

    # 列表：转换为 <div>，避免微信触发列表渲染并产生多余黑点
    raw_html = _convert_lists_to_divs(raw_html, theme=theme)

    # 链接
    raw_html = re.sub(
        r'<a\s+href="(.*?)">(.*?)</a>',
        f'<a href="\\1" style="color: {a}; text-decoration: none;">\\2</a>',
        raw_html
    )

    # 水平线
    raw_html = re.sub(
        r'<hr\s*/?>',
        r'<hr style="border: none; border-top: 1px solid #e8e8e8; margin: 0 0 16px;">',
        raw_html
    )

    # 注意：不再移除内部 .md 链接。
    # 已发布的文章在 replace_md_links 阶段已换成 http(s) URL，不会命中此处；
    # 未发布的相对 .md 链接（如指向下一篇/未发章节）予以保留，
    # 供发布后在公众号编辑器手工回填（见 PUBLISHING.md §1.7）。

    # 移除引用块内多余的 <br>
    raw_html = re.sub(
        r'(<blockquote[^>]*>.*?)<br\s*/?>(.*?</blockquote>)',
        r'\1\2',
        raw_html,
        flags=re.DOTALL
    )

    return raw_html
