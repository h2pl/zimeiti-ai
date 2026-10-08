## ADDED Requirements

### Requirement: 发布前人工审批
任何对外发布动作 MUST 在执行前获得用户显式确认；未经确认的发布任务 MUST 处于等待审批状态且不产生平台侧副作用。

#### Scenario: 未审批不发布
- **GIVEN** 存在待发布草稿
- **WHEN** 用户未确认发布
- **THEN** 不发生任何平台侧发布动作

#### Scenario: 确认后发布
- **GIVEN** 用户已确认发布某草稿
- **WHEN** 发布流程执行
- **THEN** 内容发布到目标平台（小红书/公众号）

### Requirement: 发布结果读回对账
系统 SHALL 在发布后读回平台侧状态进行对账，结果 MUST 标记为 verified（已核实成功）/ unverified（未核实）/ failed（失败）之一；MUST NOT 在未核实的情况下标记成功。

#### Scenario: 未核实不报成功
- **GIVEN** 发布动作已执行但读回对账失败
- **WHEN** 查询发布结果
- **THEN** 状态为 unverified 而非 verified

### Requirement: 平台风控护栏
发布操作 MUST 内置频控（单账号单位时间发布上限）与操作白名单；系统 MUST NOT 伪造登录态或绕过平台风控机制。凭证 MUST 加密存储。

#### Scenario: 超频控被拒
- **GIVEN** 某账号在时间窗内已达到发布频控上限
- **WHEN** 新的发布任务触发
- **THEN** 任务被拒绝并提示等待，不产生平台侧动作
