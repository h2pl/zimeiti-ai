"""文章内容包装器：结束语、最近文章列表、公众号原生名片

在 formatting 之后调用，为已排版的 HTML 添加首尾内容。
"""

import re

from wechat_mp import load_config
from .link_replacer import load_mapping
from .formatting import ARTICLE_THEMES, _DEFAULT_THEME


def _accent(theme: str | None) -> str:
    t = ARTICLE_THEMES.get(theme, ARTICLE_THEMES[_DEFAULT_THEME])
    return t["accent"]


# ─── 结束语 ────────────────────────────────────────────────────────

def build_closing(author: str, theme: str | None = None) -> str:
    a = _accent(theme)
    return (
        f'<section style="margin:0.5em 0;padding:12px 16px;'
        f'background-color:#fafafa;border-radius:6px;'
        f'border-top:2px solid {a};">'
        f'<p style="margin:0 0 6px 0;font-size:15px;color:#555;line-height:1.7;">'
        f'以上就是本文的全部内容。如果觉得有收获，欢迎<strong style="color:{a};">点赞、在看、转发</strong>，'
        f'这是对 {author} 最大的鼓励。</p>'
        f'<p style="margin:0;font-size:14px;color:#999;line-height:1.6;">'
        f'如有疑问或建议，欢迎在评论区留言交流。</p>'
        f'</section>'
    )


# ─── 最近文章列表 ──────────────────────────────────────────────────

def build_recent_articles(max_count: int = 5, theme: str | None = None) -> str:
    """从本地映射表（article_links.json）读取已发布文章列表"""
    a = _accent(theme)
    mapping = load_mapping()
    if not mapping:
        return ""

    # 只取有标题和 URL 的文章
    articles = [
        {"title": info.get("title", ""), "url": info.get("url", "")}
        for stem, info in mapping.items()
        if info.get("title") and info.get("url")
    ]
    if not articles:
        return ""

    links_html = ""
    for article in articles[:max_count]:
        links_html += (
            '<p style="margin:4px 0;font-size:14px;line-height:1.6;">'
            f'<font color="{a}">•</font> '
            f'<a href="{article["url"]}" style="color:#576b95;text-decoration:none;">{article["title"]}</a>'
            '</p>'
        )

    return (
        '<section style="margin:0.5em 0;padding:12px 16px;'
        'background-color:#f8f8f8;border-radius:6px;">'
        '<p style="margin:0 0 8px 0;font-size:15px;font-weight:bold;color:#333;">'
        '📖 近期文章</p>'
        f'{links_html}'
        '</section>'
    )


# ─── 公众号原生名片 ────────────────────────────────────────────────

def build_mp_card() -> str:
    """生成微信公众号原生名片（mp-common-profile）

    需要在 ~/.wechat-mp.json 中配置 profile 字段：
    {
      "profile": {
        "biz_id": "MzXXXX==",
        "headimg": "https://...",
        "nickname": "公众号名称",
        "alias": "微信号",
        "signature": "功能介绍"
      }
    }

    获取方式：
    1. 在公众号后台新建草稿 → 插入账号名片 → 保存
    2. 预览页面 F12 → 查找 mp-common-profile 标签
    3. 复制 data-id, data-headimg, data-nickname, data-alias, data-signature
    """
    config = load_config()
    profile = config.get("profile", {})

    biz_id = profile.get("biz_id", "")
    if not biz_id:
        return ""

    headimg = profile.get("headimg", "")
    nickname = profile.get("nickname", "")
    alias = profile.get("alias", "")
    signature = profile.get("signature", "")

    return (
        '<section style="margin:0.5em 0;">'
        '<mp-common-profile '
        'class="js_uneditable custom_select_card mp_profile_iframe mp_common_widget" '
        f'data-pluginname="mpprofile" '
        f'data-id="{biz_id}" '
        f'data-headimg="{headimg}" '
        f'data-nickname="{nickname}" '
        f'data-alias="{alias}" '
        f'data-signature="{signature}" '
        'data-from="0" '
        'data-is_biz_ban="0" '
        'contenteditable="false">'
        '</mp-common-profile>'
        '</section>'
    )


# ─── 主入口 ────────────────────────────────────────────────────────

def wrap_content(
    html: str,
    author: str = "江小湖",
    show_recent: bool = True,
    theme: str | None = None,
) -> str:
    """在已排版的 HTML 前后添加结束语、最近文章和公众号名片"""
    parts = []

    # 正文
    parts.append(html)

    # 结束语
    parts.append(build_closing(author, theme=theme))

    # 最近文章列表（从本地映射表读取）
    if show_recent:
        recent = build_recent_articles(theme=theme)
        if recent:
            parts.append(recent)

    # 公众号原生名片
    card = build_mp_card()
    if card:
        parts.append(card)

    return "\n".join(parts)
