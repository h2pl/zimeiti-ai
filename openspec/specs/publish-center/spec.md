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
