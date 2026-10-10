# web-workbench Specification

## Purpose
TBD - created by archiving change web-workbench. Update Purpose after archive.

## Requirements

### Requirement: 侧边栏路由导航

工作台提供侧边栏导航，覆盖全部页面；直接访问子路径可渲染对应页面。

#### Scenario: 未审批时访问概览
- **When** 用户访问 `/`
- **Then** 概览页渲染，显示待审批数、账号启停状态、今日发布数与最近日志

### Requirement: 审批中心

审批中心页展示待审批项（确认/拒绝）与 agent 提问卡（选项按钮+自定义回答），
行为与既有 API 一致。

#### Scenario: 多轮双闸门审批
- **When** 恢复执行命中下一个中断并重登记 pending
- **Then** 审批中心在 5s 轮询内出现新待审批卡片

### Requirement: 画像查看与编辑

画像页列出全部账号；可查看与编辑指定账号画像；PUT 提交经 validate_profile
校验，非法输入返回 400 且不落盘。

#### Scenario: 非法画像编辑被拒绝
- **When** PUT `/api/profiles/{account}` 提交缺少必填字段的画像
- **Then** 返回 400，`profiles/<account>/profile.yaml` 内容不变

### Requirement: 趋势基线归一化

趋势页展示指定账号的账号级指标均值/最新值/归一化倍率，数据来自校准证据引擎
（只读）。

#### Scenario: 无数据账号展示降级提示
- **When** 账号无任何快照
- **Then** 趋势页展示「无数据」而非零值

### Requirement: 内容库

内容库页列出指定账号已发布的草稿产物（slug、标题、合规结论、创建时间），
只读。

#### Scenario: 空内容库
- **When** 账号无产物目录
- **Then** 内容库页展示空态而非报错
