# data-storage 规格

本规格描述 `data-storage` 能力在归档后的完整行为：记录型业务数据存储于 PostgreSQL，文档型数据保留文件形态，连接配置缺省走新建库 `zimeiti-ai`，schema 预留多租户维度。

## Requirement: 记录型数据存储于 PostgreSQL

系统 MUST 将以下记录型数据存储于 PostgreSQL（经 `DATABASE_URL` 连接），不再以文件为主存储：

- 会话历史（chat_sessions / chat_messages）：每条消息含 role、内容、时间戳，按 session 可查
- LangGraph checkpoints：agent 状态经 langgraph 官方 PG checkpointer 持久化，服务重启后可恢复
- HITL pending 问题（hitl_pending）：待答问题、选项、创建时间，带 TTL 惰性清理语义（与文件版一致：超 30 分钟未答自动失效）
- 选题（ideas）与排期（schedule_items）：字段与文件版 JSON 结构一致

系统 MUST 提供幂等 `setup()`：重复执行建表不报错、不丢数据。所有表 MUST 带 `user_id TEXT NOT NULL DEFAULT 'local'` 列（见「多租户维度预留」）。

#### Scenario: 服务重启后会话上下文恢复

Acceptance: A1

Given 服务曾在某 session 与用户对话且产生了 agent checkpoint，
When 服务重启后用户以同一 session 继续对话，
Then agent 上下文自 PG checkpoint 恢复，且不把落盘历史重复注入导致上下文成倍膨胀。

#### Scenario: HITL 待答状态跨重启恢复

Acceptance: A2

Given 某 session 存在处于待答状态的 HITL 问题，
When 服务重启后用户经审批端点提交答案，
Then pending 状态自 PG 恢复，对话在同一 SSE 连接续流完成，问题被标记为已解决。

#### Scenario: 会话删除清尽全部状态

Given 某 session 有历史消息、checkpoint 与 pending 条目，
When 调用 `DELETE /api/session/{session_key}`，
Then PG 中该 session 的消息、checkpoint 与 pending 条目全部删除，同 key 再聊不复活旧上下文。

## Requirement: 文档型数据保留文件形态

以下数据 MUST 继续保持文件存储，不进入 PostgreSQL：

- 账号画像 `apps/profiles/*.md`（人写文档，prompt 按文件顺序拼接注入）
- 技能 `apps/skills/**/SKILL.md` 及其资源（文档形态）
- 登录标记 `outputs/_login/*.json`、发布状态文件、`cookies.json`、登录二维码态（Playwright 登录子进程直写的本地临时状态，重启可弃）
- 轮次结果缓存 `apps/outputs/_sessions/<key>.json`（SSE 断线续传的本轮 status/text：单写者、原地覆盖、随会话删，是运行时的状态而非业务记录）
- `outputs/` 下的媒体产物（图片/视频/HTML）

#### Scenario: 文档型数据行为不回退

Acceptance: A8

Given 迁移完成后的服务，
When 使用画像列表/详情、技能列表/详情、登录状态、发布状态相关端点，
Then 行为与迁移前一致（仍读文件），E2E 只读对比（`apps/scripts/e2e_parity_check.py`）不出现回归。

## Requirement: 连接配置与 fail-fast

系统 MUST 从环境变量 `DATABASE_URL` 读取 PostgreSQL 连接串，缺省值
`postgresql://zimeiti:zimeiti_dev@localhost:5432/zimeiti-ai`（专用库 `zimeiti-ai`，角色/口令沿用旧 zimeiti 默认值）。`DATABASE_URL` 可由 `.env` 提供（经既有 dotenv 加载路径）。

服务启动时 MUST 校验配置存在且数据库可达：未配置或不可达时 MUST 立即退出并打印明确提示（指出缺少的配置项与排查方向），不得静默启动后在写路径上丢数据。

#### Scenario: 缺库时 fail-fast

Acceptance: A6

Given 环境中 `DATABASE_URL` 未配置或指向不可达的数据库，
When 启动 API 服务，
Then 进程退出，输出包含缺失配置项名称与排查方向的明确错误信息。

## Requirement: 多租户维度预留

本变更新建的全部表 MUST 带 `user_id` 列（`TEXT NOT NULL DEFAULT 'local'`）。本地部署版全部数据使用默认值；Phase 3 多租户化时通过填值扩展，不得改表结构。查询路径 MUST 按当前用户维度过滤（本地版即默认值），为 SaaS 形态预留隔离点。

#### Scenario: schema 租户维度预留

Acceptance: A7

Given 迁移完成，
When 检查 PostgreSQL 中本变更新建的表，
Then 每张表都存在 `user_id` 列且默认值为 `local`，现有查询均按该维度过滤。

## Requirement: 一次性导入既有文件数据

系统 MUST 提供一次性导入脚本，把既有文件数据（`apps/sessions/*.json`、`apps/outputs/_ideas.json`、`apps/outputs/_schedule.json`、`apps/sessions/pending_questions.json`）写入 PostgreSQL。脚本 MUST 幂等：重复执行不产生重复记录（以自然键去重），已导入数据跳过。导入失败时 MUST 报告具体文件与原因，不得静默跳过。

#### Scenario: 导入脚本幂等可重跑

Acceptance: A5

Given 存在旧文件数据且首次导入已完成，
When 再次运行导入脚本，
Then 不产生重复记录，已存在数据跳过，脚本报告跳过/导入计数。

## Requirement: HTTP 契约保持不变

存储从文件切换到 PostgreSQL 不得改变既有前端契约：`/api/ideas`、`/api/schedule`（增删改查）与 `/api/chat/last/{session_id}` 的状态码与响应结构 MUST 与文件版一致。既有 `apps/scripts/e2e_parity_check.py` 的只读对比（49 项）与写路径（schedule/ideas 增改删）MUST 保持全绿。

#### Scenario: ideas/schedule CRUD 契约不变

Acceptance: A3

Given PG 中已有 ideas/schedule 记录，
When 调用 `/api/ideas`、`/api/schedule` 的增删改查，
Then 状态码与响应结构与文件版一致。

#### Scenario: 会话历史读取契约不变

Acceptance: A4

Given 某 session 刚完成一轮对话（轮次结果缓存已写盘），
When 调用 `/api/chat/last/{session_id}`，
Then 返回与迁移前一致的轮次结果结构（status/text/at）——该缓存按「文档型数据保留文件形态」保留文件，不随本变更迁移。
