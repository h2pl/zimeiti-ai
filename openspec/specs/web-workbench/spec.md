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

### Requirement: 账号管理页

账号管理页展示每个画像账号：启停状态（可切换）、加密凭证是否存在、登录态
文件是否存在；启停切换调用 governance.platform_state 并即时生效（停用后
发布路由拒绝）。

#### Scenario: 停用账号阻断发布
- **When** 账号被切换为停用
- **Then** real_platform_router 对该账号发布抛「已停用」错误

#### Scenario: 非法账号名切换被拒绝
- **When** toggle 请求的 account 不匹配 `^[A-Za-z0-9_-]+$`
- **Then** 返回 400

### Requirement: 单篇复盘页

复盘页列出指定平台的发布事件与排名；单篇详情展示 read 序列/生命周期/同期
对照证据（数据来自 postmortem 模块，只读）。

#### Scenario: 无发布事件的账号
- **When** 账号无发布事件
- **Then** 复盘列表为空态而非报错

### Requirement: 设置页

设置页查看与修改通知 webhook URL；保存后写入运行时设置文件并即时生效
（下一次 notify 使用新 URL）；非法 URL 被拒绝。

#### Scenario: 保存合法 webhook
- **When** PUT 设置提交 `https://open.feishu.cn/open-apis/bot/v2/hook/xxx`
- **Then** 返回 ok，后续 notify 投递到该 URL（mock 验证）

### Requirement: 运维操作页

运维操作页以技能卡片展示可手动运行的能力（名称/描述/参数表单/运行按钮）；
触发携带参数（账号 + 选题方向）写入标记文件，由常驻网关下一循环消费执行。

#### Scenario: 触发标记被网关消费
- **When** POST /api/ops/trigger 提交 job=hosted_content 写入标记
- **Then** 网关下一循环执行对应任务并清除标记

#### Scenario: 带参数触发托管循环
- **When** 用户在技能卡片填写账号与选题方向并运行
- **Then** 标记文件携带 params，网关消费时该轮托管循环使用指定账号与方向

#### Scenario: 参数白名单
- **When** trigger 提交未知 param 键或非法 account
- **Then** 返回 400，不写标记

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
