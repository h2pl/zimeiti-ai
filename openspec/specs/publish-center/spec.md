# publish-center Specification

## Purpose
TBD - created by archiving change web-chat-publish. Update Purpose after archive.

## Requirements

### Requirement: 草稿排期入队

发布中心可将内容库草稿入发布队列：入队复用 publish_queue（同键重复入队
被拒绝）；入队后由既有审批/网关链路消费。

#### Scenario: 重复入队被拒绝
- **When** 同一 source_folder+publish_date 已在队列
- **Then** 返回已存在错误，队列不产生重复条目

#### Scenario: 空内容库账号
- **When** 账号无草稿产物
- **Then** 返回空列表而非报错

### Requirement: 发布前预检

入队前可对草稿执行约束预检：逐平台返回违规列表（复用 governance.preflight），
存在违规时入队按钮禁用（fail-closed）。

#### Scenario: 违规草稿禁止入队
- **When** 草稿标题超过平台限制
- **Then** 预检返回该违规项，前端禁用入队按钮并展示违规明细

### Requirement: 定时排期

入队可指定未来运行时间（datetime-local）；过去时间或非法时间被拒绝（400）。

#### Scenario: 定时入队
- **When** 指定明天的 run_at 入队
- **Then** 队列条目 run_at 为该时间，状态 pending

### Requirement: 队列取消

pending 条目可取消（状态转 cancelled 终态）；终态条目取消返回 409；
不存在返回 404。

#### Scenario: 取消 pending 条目
- **When** 对 pending 条目发起取消
- **Then** 状态转为 cancelled，队列页徽章更新
