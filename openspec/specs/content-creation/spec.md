# content-creation Specification

## Purpose
TBD - created by archiving change mvp-scaffold. Update Purpose after archive.

## Requirements

### Requirement: 图文草稿产出
系统 SHALL 基于选定选题与账号画像产出内容草稿：小红书账号产出笔记草稿（标题 + 正文 + 标签建议 + 封面文案），公众号账号产出文章草稿（标题 + 正文 + 摘要）。草稿 MUST 保存为可编辑、可追溯来源选题的制品。

#### Scenario: 产出双平台草稿
- **GIVEN** 用户已选定某选题
- **WHEN** 触发图文创作
- **THEN** 产出与所选平台匹配的草稿制品，内容风格符合账号画像

#### Scenario: 草稿可追溯
- **GIVEN** 创作流程完成
- **WHEN** 查看任一草稿制品
- **THEN** 能追溯到其来源选题与所用账号画像

### Requirement: 出站合规审查
草稿在提交人工审批前 MUST 通过系统级合规审查；命中违规的内容 MUST 被标记并阻断进入发布流程。

#### Scenario: 违规内容被阻断
- **GIVEN** 生成的草稿命中合规规则
- **WHEN** 提交审批
- **THEN** 该草稿被标记阻断，不进入可发布状态
