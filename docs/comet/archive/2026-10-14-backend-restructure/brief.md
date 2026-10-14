# Outcome

把 Phase 1 的 Easel 逐字复制后端（单文件 3200 行 `app.py` + `easel/` 平铺包）重构为旧 zimeiti 已规范化的领域分层结构（参照 `comet-integration` 分支 arch-restructure 设计）：包名 `easel` → `zimeiti_api`，6 个领域子包 + 单向分层，`app.py` 收敛为薄组装层。纯结构重构：**行为、API 契约、前端契约零变化**，以既有 E2E 55/55 与单测等价为验收。

# Scope

## 目标结构（对齐旧设计 D1，按当前代码 inventory 调整）

```
apps/api/src/zimeiti_api/          # 注意：从 apps/api/easel/ 迁到 src/ 布局（对齐旧设计）
├── app.py                          # FastAPI 组装：建 app、注册中间件、include 各域 APIRouter
├── serve.py                        # 启动入口（原样移动）
├── core/       settings（env/代理/模型路径锚点）pg timeouts paths
├── governance/ guard（local_write_guard 护栏中间件）
├── platforms/  login publish analytics accounts（7 平台适配）+ wechat
├── content/    profiles persona skills ideas schedule outputs upload trends
├── operations/ env（安装/任务）settings_models（模型设置）
└── runtime/    chat（SSE/非流式/stop/question/skill/session）agent_runtime checkpoints
apps/api/tests/ → 镜像同构 tests/{core,governance,platforms,content,operations,runtime}
```

分层依赖规则（单向，对齐旧设计 D2）：`runtime → {governance, platforms, content, operations, core}`；`governance → core/platforms`；`content/operations/platforms → core`；`core` 不依赖业务包。`app.py` 只组装。

## 入口矩阵全量更新（不留旧路径垫片，对齐旧设计 D3）

- 包名 `easel` → `zimeiti_api`：全部 import（src/ tests/ scripts/）、`pyproject.toml`（name easel→zimeiti-api、packages.find）、`pytest.ini`、`Makefile`（serve 路径）、`apps/scripts/*.py`（migrate_files_to_pg / verify_pg_data_layer / verify_openclaw_removal / e2e_parity_check 中引用处）、删除 `easel.egg-info`
- `src/` 布局：`apps/api/easel/` → `apps/api/src/zimeiti_api/`（对齐旧设计 `apps/api/src/zimeiti_api/`；uvicorn 入口 `zimeiti_api.app:app` 或 serve.py）

## 保留不动

- `apps/skills/`（含 vendor 技能与 shared 脚本——契约：一字不动）
- `apps/web/`（前端）
- `docs/openspec/`（Classic 归档规格）
- 全部 HTTP 契约（路径/方法/状态码/响应结构）

# Non-goals

- 不做任何行为变更/API 契约变更（前端无感）
- 不引入路由框架变更外的依赖（用 FastAPI 原生 APIRouter）
- 不给旧路径留兼容垫片（一次性切干净）
- 不动 vendor 技能目录
- 不新增功能（纯移动+拆分）

# Acceptance examples

- A1: Given 重构完成，When 检查 `apps/api/src/zimeiti_api/` 结构，Then 6 个领域子包存在且 `app.py` 只含组装代码（建 app/中间件/include routers），业务端点定义在各域模块
- A2: Given 重构后的服务，When 运行 `verify_pg_data_layer.py e2e`（自起双服务 55 项对比），Then 与 Easel 上游全部一致（55/55）——行为零变化
- A3: Given 重构后的代码，When 运行 `pytest tests/`，Then 既有 12 项单测全过（测试镜像归位后）
- A4: Given 入口矩阵，When 逐个执行（serve.py 启动、make api、migrate_files_to_pg、verify_pg_data_layer、verify_openclaw_removal、e2e_parity_check、pytest），Then 全部可用
- A5: Given 重构完成，When 全仓 grep 旧路径（`from easel`、`import easel`、`easel.`、`apps/api/easel/`、`name = "easel"`），Then 零残留
- A6: Given 分层规则，When 做 import 静态检查（域间依赖），Then 无环且方向合规（core 不 import 业务包；反向依赖为零）

# Constraints and invariants

- 重构期间服务停机（先杀 :8000/:7860 进程，防 Windows 文件锁——旧 arch-restructure 的 Risk 教训）
- 每次大批移动后立刻全量 import 检查 + 单测，坏就地修，不带病前进
- 提交粒度：按「骨架移动 → 导入重写 → 入口矩阵 → 测试归位 → 回归」多提交，便于回滚

# Decisions

- D1 布局对齐旧 arch-restructure 设计（6 领域 + src/ 布局 + zimeiti_api 包名），按当前代码 inventory 调整模块清单
- D2 app.py 拆分用 FastAPI APIRouter（各域模块导出 router，app.py include）——标准 FastAPI 组装模式，非新依赖
- D3 测试镜像同构（旧设计 D4）：tests/{core,governance,platforms,content,operations,runtime}
- D4 验收策略（旧设计 D5 同款）：tdd_mode=direct——纯重构以「测试集合等价 + E2E 55/55 + 入口矩阵冒烟 + 旧路径 grep 零」为验收，不新增测试
- D5 网关/调度等多进程入口本分支不存在，入口矩阵=serve.py + Makefile + apps/scripts 全部脚本 + pytest
