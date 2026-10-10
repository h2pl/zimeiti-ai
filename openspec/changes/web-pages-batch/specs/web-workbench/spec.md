# web-workbench 能力增量（web-pages-batch）

## ADDED Requirements

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

运维操作页展示 agent 工具清单，并提供三个触发按钮：托管循环/数据取数/
校准——以触发标记文件落地，由常驻网关在下一调度循环消费执行。

#### Scenario: 触发标记被网关消费
- **When** POST /api/ops/trigger 提交 job=hosted_content 写入标记
- **Then** 网关下一循环执行对应任务并清除标记
