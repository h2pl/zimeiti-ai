# account-profile Specification

## Purpose
TBD - created by archiving change mvp-scaffold. Update Purpose after archive.

## Requirements

### Requirement: 账号画像配置
系统 SHALL 支持为每个平台账号维护一份画像配置，包含定位、内容风格、受众描述、平台规则与偏好红线五类信息；配置 MUST 以人可读的文件形式存储并可版本化。

#### Scenario: 读取画像驱动创作
- **GIVEN** 已为某账号配置完整画像
- **WHEN** 创作流程引用该账号
- **THEN** 创作上下文中包含该画像的全部维度信息

### Requirement: 多账号隔离
系统 MUST 支持多账号并存（首版：小红书 + 公众号各一），账号间配置与产物 MUST 相互隔离，一次创作/发布任务 MUST 只绑定单一账号。

#### Scenario: 并存账号互不污染
- **GIVEN** 已配置两个账号的画像
- **WHEN** 为账号 A 执行创作任务
- **THEN** 产物与上下文中不出现账号 B 的画像内容
