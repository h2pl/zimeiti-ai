# Comet Design Handoff

- Change: real-account-verification
- Phase: design
- Mode: compact
- Context hash: 2e3801ca721a623a678a2a4e2f21e670bdd3955a8a346d073aa332bdfc9e3f24

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## openspec/changes/real-account-verification/proposal.md

- Source: openspec/changes/real-account-verification/proposal.md
- Lines: 1-27
- SHA256: 907fd85bbaa957ce99c1175cc4f88fa6db08e4325d9e8e84e043253ba7282e8d

```md
# Why

变更 mvp-scaffold（已归档）以「代码完成 + mock 验证」收口，将真账号验收义务移交至本变更（用户决策 2026-10-09，见归档验证报告）。当前发布链路存在两处已知限制：① publish 工具挂的是占位平台钩子（恒返回 submitted）；② 读回对账恒返回 unverified（W1）。产品要第一次「真的」发出内容并可信地知道结果，必须完成真实平台接线与真账号验收。需求来源：`docs/prd/zimeiti-ai-prd.md`（验收 A3/A4/A6）+ 主规格 `openspec/specs/platform-publishing/spec.md`。

# What Changes

- 发布工具接线真实平台调用：公众号走已验证的草稿箱 API 客户端（my-tools 移植，token 冒烟已通过）；小红书走 Playwright 扫码登录 + 发布 + 读回
- 修复 W1：读回对账从「恒 unverified」改为真实三档判定（gzh 读草稿列表；xhs 读创作者中心笔记列表）
- 新增小红书登录态管理：首跑扫码一次，storage_state 持久化（config.LOGIN_STATE_PATH 已就位），发布复用
- 真账号小流量走查 PRD 验收 A3/A4/A6（频控压至日限 1-2 篇，仅测试号，全程审计留痕）

# Capabilities

## Modified Capabilities

- `platform-publishing`：发布结果读回对账落地真实判定（MODIFIED）；新增小红书登录态管理（原为隐含实现，现行为契约化）

## Added Capabilities

（无）

# Impact

- `apps/api/src/zimeiti_api/tools.py`（发布工具按账号路由真实平台调用）
- `apps/api/src/zimeiti_api/platforms/xhs.py`（登录流程 + 读回实现）/ `gzh.py`（读回对账接入）
- 平台风控面：真账号首次自动化发布——频控压至日限 1-2、低流量、全程审计；失败即停
- 无数据库 schema 变更；无 API 面变更

```

## openspec/changes/real-account-verification/design.md

- Source: openspec/changes/real-account-verification/design.md
- Lines: 1-41
- SHA256: b949a507ac5d0081cc31a2f218c1a50c868ea331ef4634513467b0e38e082735

```md
---
comet_change: real-account-verification
role: technical-design
canonical_spec: openspec
---

# Context

mvp-scaffold 已交付最小闭环骨架（主规格 5 capability），但发布链路有两处占位：平台调用钩子（default_platform_call 返回 submitted）与读回对账（恒 unverified，W1）。本变更完成真实接线与真账号验收（验收义务自 mvp-scaffold 拆分移交）。基础设施已就位：公众号凭据有效（token 冒烟通过）、小红书登录态路径 config.LOGIN_STATE_PATH、频控/白名单执行器、审计体系。

# Goals / Non-Goals

- Goals：publish 工具按账号路由真实平台调用；读回对账真实三档判定；小红书扫码登录持久化；真账号小流量完成 A3/A4/A6
- Non-Goals：群发（认证订阅号无 API 权限，草稿箱即止）；评论/私信互动；多账号矩阵；封面图自动生成

# Decisions

## D1：平台路由器（账号前缀路由）
发布工具内按账号名路由：`gzh-*` → GzhClient 草稿箱 API（读回=草稿列表）；`xhs-*` → XhsPublisher（读回=创作者中心笔记列表）。占位钩子 default_platform_call 保留为单测兜底，生产路径不再触达。

## D2：W1 修复——读回三档真实判定
gzh：draft/count + draft/list 匹配标题；xhs：创作者中心页解析笔记标题列表。接口异常/解析失败 → unverified + 审计异常详情（观测层 fail-open，发布动作本身仍 fail-closed）。

## D3：小红书扫码登录流程
无登录态时启动有头浏览器至登录页 → 人工扫码 → 检测登录成功（跳转创作者中心）→ storage_state 持久化至 config.LOGIN_STATE_PATH。发布复用登录态；检测未登录即中止引导重扫（spec 新增 requirement）。

## D4：验收频控配置
走查期 PublishExecutor daily_limit=2（xhs/gzh 各一），走查完成后按需回调。全程发布/读回动作进审计。

## D5：测试策略
单元：平台路由器（账号→平台映射）、读回解析（mock 页面/响应）。集成：mock 平台（httpx monkeypatch + FakePage）回归既有行为。真账号走查为验收步骤，不进自动化测试套件。

# Risks / Trade-offs

- 小红书无官方 API：选择器失效风险集中管理在 SELECTORS；首次发布可能触发平台新设备验证 → 中止并人工处理
- 扫码登录需要用户在场：验收前准备清单写明
- gzh 草稿箱 API 要求 thumb_media_id → 无封面时先上传平台默认封面图一次并复用其 media_id

# Open Questions

（无——范围/技术路径已在 Open 确认）

```

## openspec/changes/real-account-verification/tasks.md

- Source: openspec/changes/real-account-verification/tasks.md
- Lines: 1-21
- SHA256: 74463ac92693c9d78461947a90a36095cbc7bf33b3a3b21eb2db204439592862

```md
# Tasks

## 1. 真实平台接线

- [ ] 1.1 平台路由器：按账号名前缀路由 gzh/xhs 平台调用；验证：单测断言 gzh-main→GzhClient、xhs-main→XhsPublisher
- [ ] 1.2 公众号读回对账：draft/count+list 匹配标题 → 三档；验证：单测（mock 响应）三档各一
- [ ] 1.3 小红书发布+读回：创作者中心笔记列表解析 → 三档；验证：FakePage 单测
- [ ] 1.4 小红书扫码登录流程（storage_state 持久化/复用/失效引导）；验证：FakePage 单测流程断言
- [ ] 1.5 W1 回归：占位钩子仅保留单测路径，生产路径不再触达；验证：grep + 单测

## 2. 端到端与真账号验收

- [ ] 2.1 全量测试回归（现有 32 + 新增）；验证：check-api.sh 全绿
- [ ] 2.2 真账号走查 A3：gzh 草稿箱上传 + 读回 verified（日限内）；验证：审计+平台截图
- [ ] 2.3 真账号走查 A3：xhs 扫码登录 + 发布 + 读回 verified；验证：同上
- [ ] 2.4 真账号走查 A4：人为制造读回失败场景 → unverified 留痕；验证：审计记录
- [ ] 2.5 走查 A6：频控边界验证（日限 2 篇后第三篇被拒）；验证：审计记录

## 3. 收尾

- [ ] 3.1 测试报告与缺陷记录更新（verify report 增补）；验证：文档存在且与证据一致

```

## openspec/changes/real-account-verification/.openspec.yaml

- Source: openspec/changes/real-account-verification/.openspec.yaml
- Lines: 1-2
- SHA256: 8ba8273010ceb66cd0ab320b2f49de179fac6fd6f648317c2cc129442eea7dc0

```md
schema: spec-driven
created: 2026-10-09

```

## openspec/changes/real-account-verification/specs/platform-publishing/spec.md

- Source: openspec/changes/real-account-verification/specs/platform-publishing/spec.md
- Lines: 1-34
- SHA256: 71d799d1362658d7c7407664247716294f44f06aa8102c3b461f1d6d63629ecf

```md
## MODIFIED Requirements

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

## ADDED Requirements

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

```
