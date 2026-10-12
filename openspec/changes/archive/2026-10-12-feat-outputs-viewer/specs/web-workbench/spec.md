# web-workbench 能力增量（feat-outputs-viewer）

## ADDED Requirements

### Requirement: 内容库正文查看

`GET /api/outputs/{account}/{slug}` 返回单篇产物全文（选题/方向/合规结论/
两平台草稿全文 + created_at）；`GET /api/outputs/{account}/{slug}/cover.png`
以 FileResponse 返回封面图（存在时）。参数白名单防路径遍历；不存在 404。

#### Scenario: 展开正文
- **When** 用户在内容库展开某条目
- **Then** 页面展示两平台标题正文与封面图（若有）

#### Scenario: 非法 slug 拒绝
- **When** slug 含路径分隔符
- **Then** 返回 400
