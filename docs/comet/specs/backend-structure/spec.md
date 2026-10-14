# backend-structure 规格

本规格描述 `backend-structure` 能力在归档后的完整行为：zimeiti-ai 后端的代码组织方式（包结构、分层、入口矩阵）。本变更为纯结构重构，运行时行为由 data-storage 等能力规格约束，此处只约束结构本身。

## Requirement: 领域分包结构

后端代码 MUST 位于 `apps/api/src/zimeiti_api/`，按 6 个领域子包组织：`core/`（settings/pg/timeouts/paths 等基础设施）、`governance/`（护栏中间件）、`platforms/`（7 平台登录/发布/取数适配）、`content/`（画像/技能/选题/排期/产物/上传/趋势）、`operations/`（环境安装/任务/模型设置）、`runtime/`（对话链路/agent_runtime/checkpoint）。顶层只允许 `app.py`（组装）与 `serve.py`（启动入口）。

`app.py` MUST 只做组装：创建 FastAPI 实例、注册中间件、include 各域 APIRouter；MUST NOT 包含业务端点实现（端点实现位于对应域模块，各模块导出 APIRouter）。

#### Scenario: 结构落地且 app.py 收敛为组装层

Acceptance: A1

Given 重构完成，
When 检查 `apps/api/src/zimeiti_api/`，
Then 6 个领域子包均存在且有实质模块；app.py 中不存在 `@app.get/post/put/delete` 业务端点定义（仅 app 创建、中间件注册与 `include_router` 调用）。

## Requirement: 单向分层依赖

模块间依赖 MUST 满足单向规则：`runtime → {governance, platforms, content, operations, core}`；`governance → core/platforms`；`content/operations/platforms → core`；`core` MUST NOT import 任何业务包。依赖图中 MUST 无环。

#### Scenario: 分层合规且无环

Acceptance: A6

Given 重构完成，
When 对 src/ 与 tests/ 做 import 静态分析，
Then 不存在 core→业务包的反向依赖；域间依赖方向符合规则；import 图无环（全量 import 成功即无环）。

## Requirement: 行为零变化（回归等价）

重构 MUST 不改变任何运行时行为：与 Easel 上游的 E2E 只读+写路径对比 MUST 保持 55/55 一致；既有单测 MUST 全过（测试镜像归位后）。

#### Scenario: E2E 对比不回退

Acceptance: A2

Given 重构后的服务，
When 运行 `verify_pg_data_layer.py e2e`（自起 zimeiti 与 Easel 双服务）,
Then 55 项对比全部一致。

#### Scenario: 单测等价

Acceptance: A3

Given 重构后的测试目录（tests/ 镜像 6 领域），
When 运行 `pytest tests/`，
Then 既有 12 项单测全部通过。

## Requirement: 入口矩阵全量可用

以下入口 MUST 在重构后全部可用（路径随包名/布局更新）：`serve.py`（API 启动）、`make api`、`apps/scripts/migrate_files_to_pg.py`、`apps/scripts/verify_pg_data_layer.py`、`apps/scripts/verify_openclaw_removal.py`、`apps/scripts/e2e_parity_check.py`、`pytest`。

#### Scenario: 入口矩阵冒烟

Acceptance: A4

Given 重构完成，
When 逐个执行入口矩阵中的每一项，
Then 全部正常执行（启动类入口返回 200；脚本类退出码为 0）。

## Requirement: 旧路径零残留

重构 MUST NOT 保留旧路径兼容垫片：全仓 grep `from easel`、`import easel`、`easel.` 模块引用、`apps/api/easel/` 目录、`name = "easel"` MUST 全部为零。

#### Scenario: 旧路径 grep 为零

Acceptance: A5

Given 重构完成，
When 在仓库内 grep 旧包名/旧目录引用，
Then 零匹配（docs 中记录本次迁移的说明性文字除外，允许出现在变更工件与提交信息中）。
