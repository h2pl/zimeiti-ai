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

### Requirement: 公众号正文排版管线
公众号发布时，正文（Markdown）MUST 经排版管线转换为微信兼容 HTML 后再上送草稿箱：样式 MUST 全部内联（微信编辑器不支持 CSS class）、代码块 MUST 语法高亮、列表 MUST 转换为 div 结构（避免微信列表渲染异常）；转换 MUST 复用 my-tools/wechat-mp-manage 上游实现（vendor 引入并标注来源），禁止裸文本或未排版 HTML 直接上送。

#### Scenario: Markdown 正文转微信 HTML
- **GIVEN** 草稿正文为 Markdown（含标题、段落、代码块、列表）
- **WHEN** 公众号发布流程执行
- **THEN** 上送草稿箱的 content 为带内联样式的 HTML：代码块含深色背景与语法高亮、无 class 属性、列表为 div 结构

#### Scenario: 排版来源可审计
- **GIVEN** 排版管线由 my-tools/wechat-mp-manage 引入
- **WHEN** 检查 vendor 代码
- **THEN** 模块头部标注上游来源与改动说明，且与上游保持一字未改

### Requirement: 公众号封面自动生成
公众号发布时，系统 MUST 自动生成封面图（拼接规格：2.35:1 宽封面 + 1:1 方封面，标题取自草稿）并上传为草稿 thumb；未显式提供封面图时 MUST 自动生成而非留空；已上传的封面 media_id MUST 缓存复用以避免重复上传。

#### Scenario: 无显式封面时自动生成
- **GIVEN** 公众号发布流程启动且未提供封面图文件
- **WHEN** 执行发布
- **THEN** 系统生成拼接封面 PNG 并上传为 thumb_media_id，草稿携带该封面

#### Scenario: 封面缓存复用
- **GIVEN** 此前发布已上传过封面并缓存 media_id
- **WHEN** 后续发布未提供新封面图
- **THEN** 复用缓存的 thumb_media_id，不重复上传
