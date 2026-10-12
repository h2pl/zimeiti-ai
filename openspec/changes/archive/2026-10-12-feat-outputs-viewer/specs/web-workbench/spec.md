# web-workbench 能力增量（feat-outputs-viewer）

## ADDED Requirements

### Requirement: 内容正文查看器

OutputsPage 支持点开单篇产物查看：标题、账号、创建时间、合规结论、双平台
草稿正文（markdown 渲染）。数据来自 `GET /api/outputs/{account}/{slug}`
（只读，account/slug 经白名单校验，非法输入 400，不存在 404）。

#### Scenario: 查看已有草稿正文
- **When** 点击内容库某一行
- **Then** 查看器渲染该 slug 的 xhs/gzh 双平台正文（markdown 转 HTML 经 DOMPurify 消毒）

#### Scenario: 非法 slug 被拒绝
- **When** GET /api/outputs/xhs-main/..%2Fetc
- **Then** 返回 400 或 404，不返回任何文件内容
