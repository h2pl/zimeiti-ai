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
