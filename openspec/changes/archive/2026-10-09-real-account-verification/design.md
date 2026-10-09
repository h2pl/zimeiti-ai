---
comet_change: real-account-verification
role: technical-design
canonical_spec: openspec
archived-with: 2026-10-09-real-account-verification
status: final
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
