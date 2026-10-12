# web-workbench 能力增量（feat-accounts-crud）

## ADDED Requirements

### Requirement: 账号创建

`POST /api/accounts` 创建账号：account 白名单 + 不存在校验（409）+ 画像数据
validate_profile（400）；成功创建 profile.yaml 并启用。前端提供新建表单。

#### Scenario: 创建合法账号
- **When** POST 合法画像数据
- **Then** profile.yaml 生成、账号出现在列表且为启用态

#### Scenario: 重复创建被拒绝
- **When** POST 已存在的 account
- **Then** 返回 409，原画像不变

### Requirement: 账号删除

`DELETE /api/accounts/{account}`：删除 profile.yaml + platform_state 记录 +
凭证文件（避免孤儿凭证），全程审计（account_deleted）；不存在 404。前端
删除按钮需二次确认。

#### Scenario: 删除账号清理凭证
- **When** 删除带 .sealed 凭证的账号
- **Then** 画像文件与凭证文件均消失，审计记录 account_deleted
