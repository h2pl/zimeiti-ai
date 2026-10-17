---
comet_change: harness-business-split
---

# harness-business-split：agent harness 与业务代码分层

## Why

依赖测绘（grep 级）显示后端已接近单向依赖，但 harness 与业务仍有真实耦合：

- **harness → business**：3 个文件 7 个符号——`agent_runtime._skills_catalog`
  函数级引 `content.skills.get_skills`；`runtime/chat.py` 模块级引 `content`
  私有符号（`_persona_prefix`/`find_skill`/`_attachment_*`）；`runtime/status.py`
  引 `list_personas`/`get_skills`
- **business → harness**：`automations/scheduler.py` 函数级硬引 `ask_sync`
  （personas 已 DI 化，scheduler 没有）
- **结构错位**：`runtime/chat.py`、`runtime/status.py` 实为 API 路由却住在
  runtime/ 里，让人误以为路由属于 harness
- 后果：改业务（技能目录、画像、附件）要动 harness 装配代码；harness 无法
  独立测试/复用；分层规则只存在于直觉里，没有任何机制守卫

## What Changes

- **新建兄弟包 `zimeiti_harness`**（与 `zimeiti_api` 平级，同 venv）：
  `runtime/`（agent_runtime、model_fallback、exec_tool、pricing、schemas、
  status.py/chai.py 除外）+ `memory/` + `usage.py`
- **依赖倒置**：`zimeiti_harness/contract.py` 定义注入点——技能目录 provider
  由组装层（app.py）注册，harness 不再知道 content 的存在
- **路由归位**：`runtime/chat.py`→`zimeiti_api/chat_router.py`、
  `runtime/status.py`→`zimeiti_api/status_router.py`（对齐 `usage_router.py` 既有惯例）
- **scheduler DI**：`set_ask_sync(fn)` setter，app.py 接线（对齐 personas 范式），
  删除函数级硬 import
- **分层守卫**：确定性测试扫描 `zimeiti_harness/` 源码，assert 无业务域 import
  （允许 `zimeiti_api.core` 共享 infra），随 make check 防回潮
- **配置面**：pyproject packages / mypy / ruff / bandit / Makefile 覆盖率范围同步

## Non-Goals

- **core/ 不动**：paths/pg/settings/timeouts 是共享 infra（无业务逻辑），harness
  允许 import——本次分的是 harness 与业务，不是 harness 与地基
- **core/pg.py 表 schema 混装**（messages/pending/checkpoint 与业务表同文件）：
  记为已知不完美，拆表属于独立变更（牵动迁移，本轮不动）
- **exec_tool 注册表硬编码脚本路径**：数据耦合非 import 耦合，维持现状
- 提示词契约里的业务文案（`_CONTRACT_HEAD`）：文案更新走 contract 文档，
  抽取成配置属过度设计，不动

## Capabilities

### New Capabilities

- `harness-business-split`：harness 与业务代码分属两个包，harness 对业务域的
  import 为零且有确定性测试守卫；业务对 harness 的调用走显式注入点

## Impact

新增 `zimeiti_harness` 包；`zimeiti_api` 内 13 个文件的 import 更新（4 源码 +
9 测试）；app.py 组装点接线；Makefile/pyproject 检查范围更新。运行行为零变化
（纯结构重构），由全量测试 + E2E + 探针证明。
