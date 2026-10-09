"""第三方/自有项目代码 vendor 区（原样拷贝，不做深度改造）。

门禁约定：ruff/mypy/bandit/coverage 均排除本目录（见 pyproject.toml 与
scripts/check-api.sh），保证 vendor 代码与上游保持一字不差。
- wechat_mp/ : 公众号 API 客户端，来源 E:/Projects/my-tools/wechat-mp-toolkit
- wechatfmt/ : 公众号 Markdown→微信 HTML 排版管线，来源 E:/Projects/my-tools/wechat-mp-manage
"""
