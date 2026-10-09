"""微信公众号排版管线（vendor 自 my-tools/wechat-mp-manage）。

来源：
- md2html.py    ← E:/Projects/my-tools/wechat-mp-manage/src/wechat_mp_manage/article_manage/md2html.py
- formatting.py ← E:/Projects/my-tools/wechat-mp-manage/src/wechat_mp_manage/article_manage/formatting.py

上游未改动（mistune+Pygments 代码高亮、内联样式、列表转 div 等踩坑结晶）。
未移植：封面生成/结束语/名片/链接映射（依赖 my-tools 个人系列配置，按需再移植）。
"""
from .formatting import apply_wechat_styles
from .md2html import convert_md_to_html, convert_file, wrap_html

__all__ = ["apply_wechat_styles", "convert_file", "convert_md_to_html", "wrap_html"]
