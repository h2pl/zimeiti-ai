# 任务：web-pages-batch

## 1. 后端

- [ ] T1 `core/settings.py`：get/set 运行时设置（notify webhook 即时生效）+ 测试
- [ ] T2 `operations/workbench.py` 增 `accounts_detail()`（启停/凭证/登录态聚合）
      + toggle 端点 + 测试
- [ ] T3 复盘端点：`GET /api/postmortems/{platform}` 与 `/{title}`（复用
      postmortem 模块）+ 测试
- [ ] T4 运维触发：`POST /api/ops/trigger`（标记文件）+ 网关消费 + 测试
- [ ] T5 `GET /api/tools`（tool_catalog）+ 测试

## 2. 前端

- [ ] T6 AccountsPage（账号卡片：启停切换/凭证/登录态状态）
- [ ] T7 BreakdownPage（复盘列表+单篇详情，marked+dompurify 渲染）
- [ ] T8 SkillPage（运维触发三按钮+agent 工具清单）
- [ ] T9 SettingsPage（webhook 配置表单）

## 3. 验证

- [ ] T10 make check 全绿 + pnpm build
- [ ] T11 端点冒烟 + spec 场景核对
