# wechat-mp 公众号草稿能力（vendored from my-tools）

逻辑复制自 `my-tools/wechat-mp-toolkit`（API 客户端）与 `my-tools/wechat-mp-manage`（排版流水线），
凭据走 `~/.wechat-mp.json`（已配置 AppID/AppSecret，IP 白名单可用）。

**安全边界：只建草稿（draft/add、draft/update、draft/delete、素材上传），不发布。**

## 用法

```bash
cd apps/api
./.venv/Scripts/python.exe ../skills/shared/scripts/wechat_mp/draft.py <文章.md> \
    --sub "Agent 实战" --title "公众号标题" [--series "AI Agent 学习+面试指南"] \
    [--theme ocean] [--author 江小湖]
```

流水线：Markdown → HTML（公众号排版样式）→ 正文图片上传 → 拼接开场白/结束语/名片 →
封面图生成（1:1 + 2.35:1 裁剪坐标）→ 摘要提取 → thumb 上传 → `draft/add`。

产物落在 `apps/outputs/wechat-drafts/<文章名>/`：`cover.png`、`digest.txt`、
`draft_meta.json`（media_id，重复运行幂等更新）、排版后的 `*.html` 本地预览。

## 模块清单

| 文件 | 来源 | 作用 |
|---|---|---|
| `client.py` / `config.py` | wechat-mp-toolkit | 微信公众号 API 客户端（access_token 缓存、素材/草稿接口） |
| `md2html.py` | wechat-mp-manage | Markdown → 公众号 HTML（mistune + pygments 高亮） |
| `formatting.py` | wechat-mp-manage | 公众号内联样式适配 |
| `content_wrapper.py` | wechat-mp-manage | 开场白/结束语/名片包装 |
| `generate_cover_combined.py` | wechat-mp-manage | 封面图拼接生成（PIL） |
| `upload_images.py` / `trim_images.py` | wechat-mp-manage | 正文图片上传 / SVG→PNG |
| `link_replacer.py` | wechat-mp-manage | 已发布文章链接替换（可选，依赖映射文件） |
| `draft.py` | 本项目 | 一键草稿 CLI（串联上述流水线） |

依赖：`apps/api` 的 `wechat` extra（mistune/pygments/beautifulsoup4），`uv sync --all-extras` 安装。

## 调用方

- `apps/scripts/run_brand_case.py`：「程序员江湖」自动化运营 case（热点→选题→文章→草稿）
- 任何需要把 Markdown 文章转成公众号草稿的流程
