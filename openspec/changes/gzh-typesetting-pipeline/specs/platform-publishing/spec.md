# 平台发布（排版能力增量）

## ADDED Requirements

### Requirement: 公众号正文排版管线
公众号发布时，正文（Markdown）MUST 经排版管线转换为微信兼容 HTML 后再上送草稿箱：样式 MUST 全部内联（微信编辑器不支持 CSS class）、代码块 MUST 语法高亮、列表 MUST 转换为 div 结构（避免微信列表渲染异常）；转换 MUST 复用 my-tools/wechat-mp-manage 上游实现（vendor 引入并标注来源），禁止裸文本或未排版 HTML 直接上送。

#### Scenario: Markdown 正文转微信 HTML
- **GIVEN** 草稿正文为 Markdown（含标题、段落、代码块、列表）
- **WHEN** 公众号发布流程执行
- **THEN** 上送草稿箱的 content 为带内联样式的 HTML：代码块含深色背景与语法高亮、无 class 属性、列表为 div 结构

#### Scenario: 排版来源可审计
- **GIVEN** 排版管线由 my-tools/wechat-mp-manage 引入
- **WHEN** 检查 vendor 代码
- **THEN** 模块头部标注上游来源与改动说明，且与上游保持一字未改

### Requirement: 公众号封面自动生成
公众号发布时，系统 MUST 自动生成封面图（拼接规格：2.35:1 宽封面 + 1:1 方封面，标题取自草稿）并上传为草稿 thumb；未显式提供封面图时 MUST 自动生成而非留空；已上传的封面 media_id MUST 缓存复用以避免重复上传。

#### Scenario: 无显式封面时自动生成
- **GIVEN** 公众号发布流程启动且未提供封面图文件
- **WHEN** 执行发布
- **THEN** 系统生成拼接封面 PNG 并上传为 thumb_media_id，草稿携带该封面

#### Scenario: 封面缓存复用
- **GIVEN** 此前发布已上传过封面并缓存 media_id
- **WHEN** 后续发布未提供新封面图
- **THEN** 复用缓存的 thumb_media_id，不重复上传
