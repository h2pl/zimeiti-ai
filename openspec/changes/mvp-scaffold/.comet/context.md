# Comet Design Handoff

- Change: mvp-scaffold
- Phase: design
- Mode: compact
- Context hash: 5fdd4c13be9b263a1203739c9df32349fda8cdf1eca6174f41991801a79dc857

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## openspec/changes/mvp-scaffold/proposal.md

- Source: openspec/changes/mvp-scaffold/proposal.md
- Lines: 1-32
- SHA256: 02351b57f1d0278be924eafee2db41c67649b90f05ed93e8cce05259ba183cf6

```md
# Why

自媒体内容运营（选题→写文案→多平台发布→互动）每周占用大量重复劳动，现有方式是零散工具（ChatGPT 写文案 + 平台后台手动发），链路不打通、无沉淀、无自动化。LLM 能力、skills/MCP 生态与两个可参考的开源项目（Easel、xiaobei）均已成熟，现在具备用 agent 替代执行的条件。需求详情见 `docs/prd/zimeiti-ai-prd.md`（北极星指标：每周运营时间节省）。

# What Changes

- 新建 zimeiti-ai 最小闭环骨架：**选题 → 图文创作 → 双平台（小红书 + 公众号）发布**，含发布前人工审批（HITL）与发布结果读回对账
- 建立单仓库四目录工程结构：`apps/api`（后端服务与 agent 运行时）、`apps/web`（工作台/审批界面）、`packages/skills`、`mcp/`（占位）
- 建立账号画像机制（小红书 + 公众号两账号的定位/风格/受众配置，驱动创作）
- 建立托管循环骨架：定时/事件触发的最小自治执行图（执行状态持久化、断点可恢复），审批点外自动运行
- 建立基础设施：docker-compose（Postgres + pgvector）、凭证加密存储设施

# Capabilities

## New Capabilities

- `account-profile`: 账号画像的配置、存储与创作时注入——定位/风格/受众/平台规则/偏好红线，作为个性化创作的依据
- `topic-discovery`: 选题辅助——热点/竞品信息输入 → 产出选题卡（含推荐理由），由人工挑选进入创作
- `content-creation`: 图文创作——基于选定选题与账号画像，产出小红书笔记草稿与公众号文章草稿（含封面文案），风格符合画像
- `platform-publishing`: 平台发布——发布前 HITL 审批、自动化发布到小红书与公众号、读回对账（verified/unverified/failed 档位，未核实不报成功）
- `hosted-loop`: 托管循环——定时/事件触发的最小自治执行图，审批点自动阻断等待人工确认，状态可恢复

## Modified Capabilities

（无——首版新建，尚无既有 capability）

# Impact

- 全新代码库：`apps/api`、`apps/web`、`packages/skills`、`mcp/`、`docker-compose.yml`
- 外部依赖：Playwright + Chromium（平台发布自动化）、Postgres + pgvector、LLM 网关（LiteLLM，含百炼/DeepSeek 等国内可达 provider）
- 平台风控面：小红书/公众号自动化发布属风控敏感操作，实现必须内置宪法原则 III 的护栏（频控/白名单/禁伪造登录态）与原则 I 的发布前 HITL
- 不影响：无既有系统（首个变更）

```

## openspec/changes/mvp-scaffold/design.md

- Source: openspec/changes/mvp-scaffold/design.md
- Lines: 1-89
- SHA256: 6fb8f70d853d0878b77b75283343dc94fa45501d37c26666b50b659ef70e42fe

[TRUNCATED]

```md
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
与团队既有实践一致；uv 锁定 Python 3.12（本机默认 3.14.8，但 deepagents 依赖链对 3.14 的 wheel 覆盖不全，3.12 为兼容性最佳选择；uv 多版本共存，`uv python pin 3.12`）。

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


```

Full source: openspec/changes/mvp-scaffold/design.md

## openspec/changes/mvp-scaffold/tasks.md

- Source: openspec/changes/mvp-scaffold/tasks.md
- Lines: 1-49
- SHA256: cb9457f059fbe3c1ba43e691d4d5d376d5a6aa2245a1bea2fa9a4c1e474518f9

```md
# Tasks

## 1. 工程骨架

- [ ] 1.1 初始化单仓库四目录（apps/api、apps/web、packages/skills、mcp/）与根 README；验证：目录结构与本文档一致，README 存在
- [ ] 1.2 apps/api 用 uv 初始化并锁定 Python 3.12 与 LangGraph/deepagents/LiteLLM/FastAPI 版本；验证：`uv sync` 成功且 `uv run python -c "import langgraph, fastapi"` 无报错
- [ ] 1.3 编写 docker-compose.yml（Postgres + pgvector + 健康检查）；验证：`docker compose up -d` 后健康检查通过，`psql` 可连
- [ ] 1.4 FastAPI 应用工厂与 `/health` 端点；验证：`uv run uvicorn` 启动后 `GET /health` 返回 200

## 2. LangGraph 主干与托管循环（hosted-loop）

- [ ] 2.1 Postgres checkpointer 接入与连接管理；验证：写入一条检查点后能在数据库中查到对应记录
- [ ] 2.2 最小执行图（选题→创作→审批 interrupt→发布）编排；验证：本地触发图执行能走到审批中断点
- [ ] 2.3 托管触发器（定时/事件入口）与断点恢复；验证：kill 进程后重启，循环从持久化状态继续且已完成节点不重复执行
- [ ] 2.4 执行审计记录（动作/时间/结果）写入与查询接口；验证：执行一轮后审计查询接口返回完整动作列表

## 3. 账号画像（account-profile）

- [ ] 3.1 画像文件 schema 与加载/校验；验证：示例画像通过校验，缺字段画像被拒绝并提示缺失项
- [ ] 3.2 创作上下文注入与多账号隔离；验证：账号 A 创作任务的上下文不含账号 B 的画像内容（测试断言）

## 4. 选题（topic-discovery）

- [ ] 4.1 选题卡产出（信息源输入→结构化选题卡）；验证：给定测试输入产出 ≥3 张含标题/理由/方向的选题卡
- [ ] 4.2 人工挑选接口；验证：未挑选状态下创作流程不被触发（测试断言）

## 5. 图文创作（content-creation）

- [ ] 5.1 小红书笔记草稿生成（deepagents 创作段）；验证：给定选题+画像产出含标题/正文/标签/封面文案的草稿制品
- [ ] 5.2 公众号文章草稿生成；验证：产出含标题/正文/摘要的草稿制品
- [ ] 5.3 合规审查闸门（fail-closed）接入创作→审批链路；验证：构造命中规则的草稿被标记阻断且不可进入可发布状态（测试断言）

## 6. 平台发布（platform-publishing）

- [ ] 6.1 发布执行器框架（确定性脚本 + 频控/白名单入口强制）；验证：超频控任务被拒绝且无平台侧调用（测试断言）
- [ ] 6.2 小红书发布脚本 + 读回对账；验证：测试账号小流量发布后读回状态，返回 verified/unverified/failed 之一
- [ ] 6.3 公众号发布脚本（草稿箱/发布）+ 读回对账；验证：同上
- [ ] 6.4 凭证加密存储模块；验证：加密落库后明文不出现在存储与日志中（测试断言）

## 7. Web 最小界面（apps/web）

- [ ] 7.1 Next.js 初始化与审批列表/状态查看页；验证：`pnpm dev` 打开页面可见待审批项与发布状态
- [ ] 7.2 审批确认动作对接执行图 resume；验证：界面确认后执行图从 interrupt 处继续

## 8. 验证与收尾

- [ ] 8.1 单元与集成测试全量通过（执行器/频控/合规闸门/图执行/interrupt-resume/对账）；验证：测试套件全绿
- [ ] 8.2 PRD 验收 A1-A6 逐条核验（测试账号小流量）；验证：每条场景有执行证据记录
- [ ] 8.3 测试报告与缺陷记录（test-summary / defect-log）；验证：两份文档存在且与 8.1/8.2 证据一致

```

## openspec/changes/mvp-scaffold/.openspec.yaml

- Source: openspec/changes/mvp-scaffold/.openspec.yaml
- Lines: 1-2
- SHA256: ec3a1b167d0ccdb9f7a3f8f370ba8038feb637051c90a0b3fbcc5e9cef45d7a5

```md
schema: spec-driven
created: 2026-10-08

```

## openspec/changes/mvp-scaffold/specs/account-profile/spec.md

- Source: openspec/changes/mvp-scaffold/specs/account-profile/spec.md
- Lines: 1-17
- SHA256: 3e37089b898a8771df1208037954d875c364217e78625b019d65f122ac5ded4e

```md
## ADDED Requirements

### Requirement: 账号画像配置
系统 SHALL 支持为每个平台账号维护一份画像配置，包含定位、内容风格、受众描述、平台规则与偏好红线五类信息；配置 MUST 以人可读的文件形式存储并可版本化。

#### Scenario: 读取画像驱动创作
- **GIVEN** 已为某账号配置完整画像
- **WHEN** 创作流程引用该账号
- **THEN** 创作上下文中包含该画像的全部维度信息

### Requirement: 多账号隔离
系统 MUST 支持多账号并存（首版：小红书 + 公众号各一），账号间配置与产物 MUST 相互隔离，一次创作/发布任务 MUST 只绑定单一账号。

#### Scenario: 并存账号互不污染
- **GIVEN** 已配置两个账号的画像
- **WHEN** 为账号 A 执行创作任务
- **THEN** 产物与上下文中不出现账号 B 的画像内容

```

## openspec/changes/mvp-scaffold/specs/content-creation/spec.md

- Source: openspec/changes/mvp-scaffold/specs/content-creation/spec.md
- Lines: 1-22
- SHA256: 47e4594c9149335d6d9d05f33600ea7f815ec51e508cd2e6080dfb009fdacdd8

```md
## ADDED Requirements

### Requirement: 图文草稿产出
系统 SHALL 基于选定选题与账号画像产出内容草稿：小红书账号产出笔记草稿（标题 + 正文 + 标签建议 + 封面文案），公众号账号产出文章草稿（标题 + 正文 + 摘要）。草稿 MUST 保存为可编辑、可追溯来源选题的制品。

#### Scenario: 产出双平台草稿
- **GIVEN** 用户已选定某选题
- **WHEN** 触发图文创作
- **THEN** 产出与所选平台匹配的草稿制品，内容风格符合账号画像

#### Scenario: 草稿可追溯
- **GIVEN** 创作流程完成
- **WHEN** 查看任一草稿制品
- **THEN** 能追溯到其来源选题与所用账号画像

### Requirement: 出站合规审查
草稿在提交人工审批前 MUST 通过系统级合规审查；命中违规的内容 MUST 被标记并阻断进入发布流程。

#### Scenario: 违规内容被阻断
- **GIVEN** 生成的草稿命中合规规则
- **WHEN** 提交审批
- **THEN** 该草稿被标记阻断，不进入可发布状态

```

## openspec/changes/mvp-scaffold/specs/hosted-loop/spec.md

- Source: openspec/changes/mvp-scaffold/specs/hosted-loop/spec.md
- Lines: 1-22
- SHA256: 24018536dc8a69eec93542cf0765f2204a9fa21d7f1f0d3c845b65a1649d3465

```md
## ADDED Requirements

### Requirement: 托管循环骨架
系统 SHALL 支持以定时/事件方式触发最小自治循环（选题→创作→等待审批），审批点 MUST 自动阻断等待人工确认；循环执行状态 MUST 持久化，进程重启后 MUST 可从断点恢复。

#### Scenario: 审批点自动阻断
- **GIVEN** 托管循环运行至发布审批节点
- **WHEN** 无人确认
- **THEN** 循环在该节点持久化等待，不执行发布

#### Scenario: 断点恢复
- **GIVEN** 托管循环在执行中被中断
- **WHEN** 进程重启并恢复循环
- **THEN** 从中断前的持久化状态继续执行，已完成步骤不重复执行

### Requirement: 执行审计
托管循环的每次自动动作 MUST 留存审计记录（触发时间、动作、结果），供用户事后查看。

#### Scenario: 审计可查
- **GIVEN** 托管循环执行过若干自动动作
- **WHEN** 用户查看执行历史
- **THEN** 每个动作的时间、类型与结果可查

```

## openspec/changes/mvp-scaffold/specs/platform-publishing/spec.md

- Source: openspec/changes/mvp-scaffold/specs/platform-publishing/spec.md
- Lines: 1-30
- SHA256: 2db04139dc54db0f155c4eb801d59ee5135a1a454f28caaea67897b9a7224e6f

```md
## ADDED Requirements

### Requirement: 发布前人工审批
任何对外发布动作 MUST 在执行前获得用户显式确认；未经确认的发布任务 MUST 处于等待审批状态且不产生平台侧副作用。

#### Scenario: 未审批不发布
- **GIVEN** 存在待发布草稿
- **WHEN** 用户未确认发布
- **THEN** 不发生任何平台侧发布动作

#### Scenario: 确认后发布
- **GIVEN** 用户已确认发布某草稿
- **WHEN** 发布流程执行
- **THEN** 内容发布到目标平台（小红书/公众号）

### Requirement: 发布结果读回对账
系统 SHALL 在发布后读回平台侧状态进行对账，结果 MUST 标记为 verified（已核实成功）/ unverified（未核实）/ failed（失败）之一；MUST NOT 在未核实的情况下标记成功。

#### Scenario: 未核实不报成功
- **GIVEN** 发布动作已执行但读回对账失败
- **WHEN** 查询发布结果
- **THEN** 状态为 unverified 而非 verified

### Requirement: 平台风控护栏
发布操作 MUST 内置频控（单账号单位时间发布上限）与操作白名单；系统 MUST NOT 伪造登录态或绕过平台风控机制。凭证 MUST 加密存储。

#### Scenario: 超频控被拒
- **GIVEN** 某账号在时间窗内已达到发布频控上限
- **WHEN** 新的发布任务触发
- **THEN** 任务被拒绝并提示等待，不产生平台侧动作

```

## openspec/changes/mvp-scaffold/specs/topic-discovery/spec.md

- Source: openspec/changes/mvp-scaffold/specs/topic-discovery/spec.md
- Lines: 1-17
- SHA256: 1d14fe6a8016a7d44d483763ac08a420a353ede859d7d8fb4e125d50e61de8b7

```md
## ADDED Requirements

### Requirement: 选题卡产出
系统 SHALL 基于账号画像与输入信息源（热点/竞品/用户指定方向）产出选题卡，每张选题卡 MUST 包含选题标题、推荐理由与内容方向建议，并以人工可挑选的形式呈现。

#### Scenario: 产出选题卡
- **GIVEN** 账号画像已配置且信息源可用
- **WHEN** 触发选题流程
- **THEN** 产出至少 3 张选题卡，每张含标题、推荐理由与方向建议

### Requirement: 人工挑选进入创作
选题卡 MUST 由人工挑选确认后方可进入创作流程，系统 MUST NOT 自动选定选题直接创作。

#### Scenario: 未挑选不创作
- **GIVEN** 系统已产出选题卡
- **WHEN** 用户未挑选任何选题
- **THEN** 创作流程不被触发

```
