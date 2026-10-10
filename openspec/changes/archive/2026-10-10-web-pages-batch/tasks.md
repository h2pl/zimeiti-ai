# 任务：web-pages-batch

## 1. 后端

- [x] T1 `core/settings.py`：get/set 运行时设置（notify webhook 即时生效）+ 测试 <!-- comet-task:4a306e12-d7cd-4134-95c9-30f3bfffec55 -->
- [x] T2 `operations/workbench.py` 增 `accounts_detail()`（启停/凭证/登录态聚合） <!-- comet-task:3bfedc0c-56c2-457a-bf40-77626101efc8 -->
      + toggle 端点 + 测试
- [x] T3 复盘端点：`GET /api/postmortems/{platform}` 与 `/{title}`（复用 <!-- comet-task:0b464dbd-6a4f-4b9a-b03c-43941886c761 -->
      postmortem 模块）+ 测试
- [x] T4 运维触发：`POST /api/ops/trigger`（标记文件）+ 网关消费 + 测试 <!-- comet-task:6e8cc7a4-a0b5-476a-b7a3-7e6e10a57bbf -->
- [x] T5 `GET /api/tools`（tool_catalog）+ 测试 <!-- comet-task:46c85b03-c7ca-45e0-88e3-3512f1c39e51 -->

## 2. 前端

- [x] T6 AccountsPage（账号卡片：启停切换/凭证/登录态状态） <!-- comet-task:8c659f29-663c-406d-b4fa-9b09346a483b -->
- [x] T7 BreakdownPage（复盘列表+单篇详情，marked+dompurify 渲染） <!-- comet-task:c5071631-fd58-4ddd-89c6-b086ab114d10 -->
- [x] T8 SkillPage（运维触发三按钮+agent 工具清单） <!-- comet-task:c06040e7-9b12-4cc6-9478-4e83ddad7880 -->
- [x] T9 SettingsPage（webhook 配置表单） <!-- comet-task:076e178c-37d4-42ad-8ee5-bdfbdd9e13d0 -->

## 3. 验证

- [x] T10 make check 全绿 + pnpm build <!-- comet-task:e5c21f02-9253-45ab-bd8f-1f8609ef3bd0 -->
- [x] T11 端点冒烟 + spec 场景核对 <!-- comet-task:8d67c767-6208-406c-a152-ac4529e329cb -->
