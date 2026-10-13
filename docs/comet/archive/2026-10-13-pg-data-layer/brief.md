# Outcome

记录型业务数据从文件存储迁移到 PostgreSQL，文档型数据保留文件形态；schema 从第一天预留租户维度（本地版填默认值），为后续双形态（本地部署 + SaaS）共用同一条数据主线。迁移后服务重启不丢对话上下文与 HITL 待答状态，前端既有 CRUD 契约不变。

# Scope

## 迁入 PG（5 项）

- 会话历史：`apps/sessions/<key>.json` → PG（chat_sessions / chat_messages）
- LangGraph checkpoints：`InMemorySaver` → langgraph 标准 PG checkpointer（服务重启后 agent 上下文可恢复）
- HITL pending 问题：`apps/sessions/pending_questions.json` → PG（hitl_pending）
- 选题 ideas：`apps/outputs/_ideas.json` → PG（ideas）
- 排期 schedule：`apps/outputs/_schedule.json` → PG（schedule_items）

配套：`DATABASE_URL` 环境配置；幂等 `setup()` 建表；一次性导入脚本（现有文件数据 → PG，可重复执行）；`/api/ideas`、`/api/schedule`、`/api/chat/last/{id}` 的 HTTP 契约（状态码与响应结构）保持不变。

## 保留文件（文档型/本地临时状态，按用户确认的原则「除非本身就是设计文件形态的数据」）

- 画像 `apps/profiles/*.md`（人写文档，prompt 按文件拼接）
- 技能 `apps/skills/**/SKILL.md`（文档形态）
- 登录标记 `outputs/_login/*.json`、发布状态、`cookies.json`、二维码态（Playwright 登录子进程直写的本地临时状态，重启可弃；Q2 确认留文件）
- 轮次结果缓存 `apps/outputs/_sessions/<key>.json`（SSE 断线续传的「本轮 status/text」：单写者、原地覆盖、随会话删——运行时的状态而非业务记录，与登录标记同类）
- `outputs/` 媒体产物（图片/视频/HTML；PG 只存路径，本变更不引入路径表）

## Source coverage

本变更无外部需求源文档；需求来自本次会话澄清与旧 zimeiti PRD（`comet-integration:docs/prd/zimeiti-ai-prd.md`，技术栈锁定含 Postgres/pgvector）及旧分支 PG 资产（`runtime/checkpoints.py`、`operations/metrics.py`、`core/credentials.py`）。

# Non-goals

- 不做多租户实现（仅 schema 预留 user_id 维度，本地版填固定默认值）
- 不做双写过渡（直接切换 + 一次性导入脚本）
- 不迁画像/技能/媒体产物进 PG
- 不新增会话历史 Web 列表 UI（现有端点契约不变）
- 不引入 ORM（显式 SQL，对齐旧分支 psycopg 惯例）
- 不接 pgvector/RAG（后续变更）

# Acceptance examples

- A1: Given 服务曾在某 session 对话，When 服务重启后用户以同一 session 继续对话，Then agent 上下文从 PG checkpoint 恢复（不重复注入落盘历史、不出现上下文成倍膨胀）
- A2: Given HITL 问题处于待答状态时服务重启，When 用户经审批端点回答问题，Then pending 状态自 PG 恢复且对话正常续流
- A3: Given PG 中已有 ideas/schedule 记录，When 调用 `/api/ideas`、`/api/schedule` 的增删改查，Then 状态码与响应结构与文件版一致
- A4: Given 某 session 刚完成一轮对话，When 调用 `/api/chat/last/{session_id}`，Then 返回与迁移前一致的轮次结果结构（status/text/at）——该缓存为运行时的状态，保留文件形态（见 Scope「保留文件」）
- A5: Given 存在旧文件数据（sessions/*.json、_ideas.json、_schedule.json、pending_questions.json），When 运行一次性导入脚本，Then 数据进入 PG 且脚本可重复执行（幂等，不产生重复记录）
- A6: Given `DATABASE_URL` 未配置或 PG 不可达，When 启动服务，Then 服务 fail-fast 退出并打印明确提示（指出缺少的配置与排查方向），不静默启动后丢数据
- A7: Given 本变更新建的全部表，When 检查 schema，Then 每张表都带 user_id 维度（本地版默认值固定），为多租户预留
- A8: Given 本变更完成后，When 使用画像/技能/登录态相关端点，Then 行为不回退（仍走文件，与迁移前一致）

# Constraints and invariants

- 平台凭证加密存储、不落明文不入日志的既有约束不变（本变更不触碰凭证链路）
- 迁移不得破坏既有 E2E 对比结果（`apps/scripts/e2e_parity_check.py` 49 项只读 + 写路径）
- Windows 环境：psycopg 异步路径需 `WindowsSelectorEventLoopPolicy`（旧 zimeiti 踩坑惯例）

# Decisions

- D1 技术栈：psycopg3 + 显式 SQL（零 ORM，对齐旧分支 `checkpoints.py`/`metrics.py` 惯例）；checkpoint 用 langgraph 官方 PG checkpointer
- D2 schema：所有新表带 `user_id TEXT NOT NULL DEFAULT 'local'`，Phase 3 多租户化时填值而非改表
- D3 迁移策略：直接切换 + 一次性导入脚本（当前文件数据基本为空，导入成本低）
- D4 会话历史保留策略：无限期保留，删除经既有 `DELETE /api/session/{key}`（与文件版行为一致），不引入 TTL
- D5 PG 连接：新建专用库，库名 `zimeiti-ai`；默认连接串 `postgresql://zimeiti:zimeiti_dev@localhost:5432/zimeiti-ai`（角色/口令沿用旧 zimeiti 默认值；Build 第一步验证角色与库存在性，缺失则创建并记录）
- D6 缺库行为（Q3）：fail-fast——启动时校验 `DATABASE_URL` 与连通性，缺失/不可达即退出并打印明确提示
- D7 登录标记/发布状态/cookies/二维码态（Q2）：保留文件形态，不进 PG

# Open questions

（无——Q1/Q2/Q3 均已确认，决策记入 D5/D6/D7）
