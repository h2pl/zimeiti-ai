---
comet_change: mvp-scaffold
role: technical-design
canonical_spec: openspec
---


# Architecture（双形态拓扑，T1 已确认）

```
                 ┌────────── 同一套 agent 资产 ──────────┐
                 │ create_deep_agent(                    │
                 │   tools=[选题,创作,合规闸门,发布],       │
                 │   subagents=[创作者(隔离上下文)],        │
                 │   interrupt_on={"publish": ...},       │
                 │   checkpointer=AsyncPostgresSaver)     │
                 └──────────────┬────────────────────────┘
                                │
      ┌─────────────────────────┴──────────────────────┐
      ▼ 工作台形态（学 Easel）                           ▼ 托管形态（学 xiaobei）
  用户 Web/对话逐环节驱动：                          定时/事件触发的自治循环：
  手动给方向→出选题卡→人挑选→                        自动选题→task 委派创作 subagent→
  人改稿/触发创作/审稿→发布仍过 HITL                  发布审批 interrupt 阻断等确认；
  （交互式会话，主 agent 直操工具）                    状态持久化、断点恢复、审计留痕
```
差别只在「谁触发」与「interrupt 等待的介质」；工具、subagent、审批配置完全共用。

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
与团队既有实践一致；uv + pnpm。环境实测修正（2026-10-08）：本机 uv 受管 Python 目录损坏（os error 448 不受信装入点），3.12 不可用；实测 3.14.8 下 deepagents/LangGraph/FastAPI/psycopg/litellm 全依赖可安装可导入，开发机采用 3.14.8（.python-version 指向系统 pythoncore 解释器）；CI/生产仍以 3.12 为目标版本，待受信环境验证。

## D3：发布 HITL 用 deepagents interrupt_on 实现（修订）
发布工具注册进 `interrupt_on={"publish": {...}}`，执行前自动中断；审批请求（含工具参数）经 API 呈现给用户，确认后以 `Command(resume=[{"type":"approve"}])` 恢复（拒绝则 `reject` 回填理由）。中断态存于 Postgres checkpointer（D4），24h 托管与 Web 对话共用同一 thread 语义。理由：官方原生特性（非自组装），支持 approve/reject/edit/respond 四种决策与按参数条件的审批谓词。

## D4：Postgres + pgvector 真库起步（用户确认有 Docker 2026-10-08）
`docker-compose.yml` 提供 Postgres（含 pgvector 扩展），LangGraph checkpointer 直连。理由：中断恢复（A5 断点恢复场景）依赖持久化，stub 方案行为有差异；生产同构避免二次迁移。选 Postgres 而非 SQLite 的依据：① langgraph-checkpoint-postgres 为官方一等支持，SQLite saver 存在单写者锁问题（托管循环与 Web 审批并发互阻）；② pgvector 为画像语义检索/归因分析预留向量能力，免引入独立向量库；③ 商业化目标库即 Postgres，真库起步免迁移。

## D5：发布执行器为确定性 Python 脚本 + 读回对账
发布/读回实现为独立可测试的脚本层（借鉴 Easel：四档 outcome + 绝不冒报成功），agent 只负责编排与决策。频控/白名单在执行器入口强制（fail-closed）。

## D6：凭证加密存储（用户确认 2026-10-08）
平台 Cookie/Token 经对称加密（主密钥来自环境变量，生产迁 KMS）后落库/落文件，日志脱敏为强制约定。

## D8：选题信源 = 公益热搜 API + 手动方向（T2 已确认）
双通道：聚合热搜 API（Easel 同款公益源，无 SLA 风险已记录，商业阶段换自建）+ 用户手动指定方向。人工挑选后方可进入创作。

## D9：审批通知 = 仅 Web 审批页（T3 已确认）
首版待审批项通过 apps/web 查看/确认，无 IM/邮件推送。推送能力进 ROADMAP。

## D7：合规审查为系统级闸门
出站内容审查实现为独立模块，创作→审批链路强制经过；命中规则即阻断（fail-closed），不做 prompt 级软约束。

# Test Strategy

- 单元（pytest）：合规闸门规则、频控/白名单、读回对账分档、画像加载校验
- 集成：deepagents 图执行 + interrupt/resume，AsyncPostgresSaver 真库（docker 起）
- 验收：PRD A1-A6 真实账号小流量走查，证据记录进 test-summary

# Risks / Trade-offs

- 小红书/公众号无官方发布 API，Playwright 自动化存在风控风险 → 频控+读回对账+小流量验证；选择器失效需持续维护
- 双形态并行（工作台+托管）前端成本高于单形态 → 首版 Web 仅做审批与状态查看的最小界面
- deepagents 与 LangGraph 版本耦合 → 锁定版本，隔离适配层

# Open Questions

- 账号画像文件的具体 schema（字段级）在实现任务中细化，原则见 `account-profile` spec
