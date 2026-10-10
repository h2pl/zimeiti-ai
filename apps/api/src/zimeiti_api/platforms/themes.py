"""gzh 排版主题化（P1⑬）。

参考: Easel gzh-design（主题组件库/自定义主题）——vendor wechatfmt 输出内联
样式（微信不支持 class），主题层在 vendor 之外做**色板替换**后处理：
accent/accent_bg hex 替换，保持 vendor 上游一字不差（宪法：vendor 不改动）。

预设主题：default（vendor 原生科技蓝）/ sakura 樱花粉 / forest 森林绿 /
sunset 暖橙。platforms.gzh.publish_gzh_draft 可经 profile 偏好选择主题。
"""

import re

# vendor 默认 accent（科技蓝）→ 主题色板
_VENDOR_ACCENT = "#2563EB"
_VENDOR_ACCENT_BG = "#EFF4FF"

THEMES: dict[str, dict[str, str]] = {
    "default": {},
    "sakura": {"accent": "#EC4899", "accent_bg": "#FDF2F8"},
    "forest": {"accent": "#059669", "accent_bg": "#ECFDF5"},
    "sunset": {"accent": "#EA580C", "accent_bg": "#FFF7ED"},
}


def apply_theme(html: str, theme: str = "default") -> str:
    """按主题替换 vendor 输出的强调色。未知主题名 fail-closed 用 default。"""
    palette = THEMES.get(theme) or THEMES["default"]
    if not palette:
        return html
    out = html
    if "accent" in palette:
        out = re.sub(re.escape(_VENDOR_ACCENT), palette["accent"], out, flags=re.IGNORECASE)
    if "accent_bg" in palette:
        out = re.sub(re.escape(_VENDOR_ACCENT_BG), palette["accent_bg"], out, flags=re.IGNORECASE)
    return out
