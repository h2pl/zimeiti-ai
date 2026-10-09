# platform-publishing Specification

## Purpose
TBD - created by archiving change mvp-scaffold. Update Purpose after archive.

## Requirements

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
系统 SHALL 在发布后读回平台侧真实状态进行对账，结果 MUST 标记为 verified（已核实成功）/ unverified（未核实）/ failed（失败）之一；MUST NOT 在未核实的情况下标记成功。真实判定：公众号以草稿列表含目标稿件为 verified 依据；小红书以创作者中心笔记列表含目标标题为 verified 依据；读回接口异常时 MUST 返回 unverified 并记录审计。

#### Scenario: 公众号发布读回 verified
- **GIVEN** 草稿已通过公众号 API 上传草稿箱
- **WHEN** 读回草稿列表
- **THEN** 若列表含目标稿件则标记 verified

#### Scenario: 小红书发布读回 verified
- **GIVEN** 已通过浏览器自动化完成小红书发布
- **WHEN** 读回创作者中心笔记列表
- **THEN** 若列表含目标标题则标记 verified

#### Scenario: 读回异常返回 unverified
- **GIVEN** 读回接口超时或异常
- **WHEN** 查询发布结果
- **THEN** 状态为 unverified 且审计记录含异常信息

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

### Requirement: 小红书登录态管理
系统 SHALL 支持小红书登录态的一次性扫码获取与持久化复用：登录页打开后等待人工扫码，成功后 storage_state MUST 经加密存储路径持久化；发布时 MUST 复用持久化登录态，失效时 MUST 引导重新扫码而非伪造登录。

#### Scenario: 首跑扫码登录
- **GIVEN** 本机无小红书登录态
- **WHEN** 发布流程启动
- **THEN** 打开登录页等待扫码，成功后登录态持久化并可复用

#### Scenario: 登录态失效引导重扫
- **GIVEN** 持久化登录态已失效
- **WHEN** 发布流程检测到未登录
- **THEN** 流程中止并提示重新扫码，MUST NOT 尝试伪造登录
