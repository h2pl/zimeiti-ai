# Context

零代码仓库起步。需求与验收基准见 `docs/prd/zimeiti-ai-prd.md`（A1-A6）；宪法红线见 `.specify/memory/constitution.md`（发布 HITL / 凭证安全 / 风控护栏 / 合规闸门）。技术栈已在知识库锁定：LangGraph + deepagents + LiteLLM + MCP + FastAPI + Next.js + Playwright + Postgres/pgvector。

# Goals / Non-Goals

- Goals：可运行的最小闭环（选题→图文创作→双平台发布），托管循环骨架，工程结构为后续 capability 留好落点
- Non-Goals：短视频、获客侧、归因回流、多租户/计费完整实现、CI 流水线

# Decisions

## D0：Agent 引擎 = deepagents（用户确认 2026-10-08）

选型 `deepagents>=0.7.6,<0.8`（LangChain 官方，LangGraph 底座），本地参考 `E:/Projects/deepagents`（0.1.57 monorepo）。

- 关键用法（源码证据）：`create_deep_agent(model, tools, interrupt_on, checkpointer, subagents, middleware, backend)`（libs/deepagents/deepagents/graph.py:268）；HITL 用 `interrupt_on={"publish": True}`（官方集成测试 libs/deepagents/tests/integration_tests/test_hitl.py：中断→get_state 读 interrupts→同 thread_id `Command(resume=decisions)` 恢复，决策 approve/reject/edit/respond）；持久化传 `AsyncPostgresSaver`（官方 Postgres 集成测试先例）；子代理声明式定义、独立上下文隔离（subagents.py）
- 模型接入：DeepSeek 走 `langchain-deepseek`（`deepseek:` provider）；百炼走 ChatOpenAI + DashScope 兼容 base_url
- 已否决备选：OpenClaw（格式级深耦合+patch 税+单实例天花板，Easel 10 项版本对抗证据）；dsh（架构契合但 TS 栈切换+v0.1 preview 破坏性变更风险）；OpenAI/Claude Agent SDK（模型家族锁死，与国内模型约束冲突）；裸 LangGraph（HITL/子代理样板代码多）
- 参考范例：examples/content-builder-agent/（与本品同构的内容生成 agent）

## D1：单仓库四目录布局
`apps/api`（FastAPI + LangGraph）、`apps/web`（Next.js）、`packages/skills`（SKILL.md+scripts）、`mcp/`。理由：知识库技术栈的自然映射；skill/MCP 与业务代码边界清晰。备选「先只建 backend」被否——迁移成本高于一次建对。

## D2：Python 工具链 uv，Node 工具链 pnpm（用户确认 2026-10-08）
与团队既有实践一致；uv 锁定 Python 3.12（本机默认 3.14.8，但 deepagents 依赖链对 3.14 的 wheel 覆盖不全，3.12 为兼容性最佳选择；uv 多版本共存，`uv python pin 3.12`）。

## D3：发布 HITL 用 deepagents interrupt_on 实现（修订）
发布工具注册进 `interrupt_on={"publish": {...}}`，执行前自动中断；审批请求（含工具参数）经 API 呈现给用户，确认后以 `Command(resume=[{"type":"approve"}])` 恢复（拒绝则 `reject` 回填理由）。中断态存于 Postgres checkpointer（D4），24h 托管与 Web 对话共用同一 thread 语义。理由：官方原生特性（非自组装），支持 approve/reject/edit/respond 四种决策与按参数条件的审批谓词。

## D4：Postgres + pgvector 真库起步（用户确认有 Docker 2026-10-08）
`docker-compose.yml` 提供 Postgres（含 pgvector 扩展），LangGraph checkpointer 直连。理由：中断恢复（A5 断点恢复场景）依赖持久化，stub 方案行为有差异；生产同构避免二次迁移。选 Postgres 而非 SQLite 的依据：① langgraph-checkpoint-postgres 为官方一等支持，SQLite saver 存在单写者锁问题（托管循环与 Web 审批并发互阻）；② pgvector 为画像语义检索/归因分析预留向量能力，免引入独立向量库；③ 商业化目标库即 Postgres，真库起步免迁移。

## D5：发布执行器为确定性 Python 脚本 + 读回对账
发布/读回实现为独立可测试的脚本层（借鉴 Easel：四档 outcome + 绝不冒报成功），agent 只负责编排与决策。频控/白名单在执行器入口强制（fail-closed）。

## D6：凭证加密存储（用户确认 2026-10-08）
平台 Cookie/Token 经对称加密（主密钥来自环境变量，生产迁 KMS）后落库/落文件，日志脱敏为强制约定。

## D7：合规审查为系统级闸门
出站内容审查实现为独立模块，创作→审批链路强制经过；命中规则即阻断（fail-closed），不做 prompt 级软约束。

# Risks / Trade-offs

- 小红书/公众号无官方发布 API，Playwright 自动化存在风控风险 → 频控+读回对账+小流量验证；选择器失效需持续维护
- 双形态并行（工作台+托管）前端成本高于单形态 → 首版 Web 仅做审批与状态查看的最小界面
- deepagents 与 LangGraph 版本耦合 → 锁定版本，隔离适配层

# Open Questions

- 账号画像文件的具体 schema（字段级）在实现任务中细化，原则见 `account-profile` spec
