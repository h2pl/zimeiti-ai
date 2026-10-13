---
comet_change: phase1-deepagents-runtime
role: technical-design
canonical_spec: openspec
archived-with: 2026-10-13-phase1-deepagents-runtime
status: final
---

## Context

`apps/api` 已复制 Easel 后端并跑通 `/api/status`（phase1-easel-api-copy）。对话链路当前依赖 OpenClaw 网关：`/api/chat/stream` 的 supervisor 有 HTTP 网关与 CLI spawn 两条路径，均依赖 OpenClaw 进程（本环境无）。OpenClaw 依赖清单见 `phase1-easel-api-copy/openclaw-dependencies.md`。

可复用资产：旧 zimeiti 后端（comet-integration 分支）已有验证过的 deepagents 集成——`create_deep_agent` + `interrupt_on={"ask_human": True}` + `Command(resume={"decisions":[...]})` HITL 恢复。

前端 SSE 契约（app.py forward 循环）：token/thinking/activity/question/error/done 帧，question 的 data 为 JSON 字符串；done 携带 sessionKey；客户端断开经 CLIENT_DONE 哨兵。

## Goals / Non-Goals

**Goals:**

- 对话链路改由 deepagents 进程内运行时承载，去除对 OpenClaw 进程的运行时依赖
- HITL 问题卡内联、可恢复、SSE 不断开
- 无模型配置时优雅降级

**Non-Goals:**

- 不实现选题/创作/发布等业务工具（阶段二/三）
- 不迁移 `/api/settings/models*`、`/api/settings/local-agents`、`/api/skills` 等 OpenClaw 配置面端点（保持现状，后续变更处理）
- 不删除 OpenClaw 模块文件（保留回退能力）

## Decisions

### 决策 1：接缝式替换，而非重写 app.py

- **选择**：在 `api_chat_stream` supervisor 顶部按 `ZIMEITI_RUNTIME` 环境变量分支；问答题两端点在运行时模式下前置短路
- **理由**：4419 行 app.py 的 CLI/HTTP 双路径与断线恢复机制已验证；接缝替换保留全部基础设施（event_path 落盘、client_q 转发、/api/chat/last）
- **备选**：重写对话端点 → 丢失断线恢复/心跳/停止等细节，否决

### 决策 2：会话历史落盘 + InMemorySaver checkpointer

- **选择**：消息历史按 session 落盘 JSON；langgraph checkpointer 用进程内 InMemorySaver（thread_id=session_key）
- **理由**：历史必须跨重启保留（PRD 体验）；HITL resume 依赖 checkpointer，进程内够用（中断期间 SSE 不断开，回答即时恢复）
- **备选**：SqliteSaver 持久 checkpoint → 中断恢复跨重启，但 ask_human 中断本就要求人在线，否决（后续可升级）

### 决策 3：中断期间保持 SSE 连接

- **选择**：ask_human 中断时发 question 帧但不发 done，连接保持；答案经 `/api/chat/question/answer` 触发 Command(resume)，续流 token 走原队列
- **理由**：与 Easel 交互一致（问题卡内联、回答后继续输出）；避免前端轮询
- **备选**：断开连接由前端恢复 → 交互割裂，否决

### 决策 4：模型经环境变量注入

- **选择**：`ChatOpenAI`（langchain-openai），ZIMEITI_MODEL / OPENAI_API_KEY / OPENAI_BASE_URL；未配置 key 时 error 帧降级
- **理由**：OpenAI 兼容端点覆盖面最广（含 LiteLLM/各类网关）；无 key 的环境仍可验证链路与降级路径
- **备选**：绑定特定厂商 SDK → 锁死生态，否决

## Risks / Trade-offs

- **[风险] 无模型 key 的环境无法验证真实 token 流** → 缓解：降级路径实测通过；配置 key 后同一链路即产出 token
- **[风险] InMemorySaver 重启后中断态丢失** → 缓解：ask_human 场景要求人在线；跨重启恢复列为后续增强
- **[权衡] OpenClaw 模块保留**：接缝开关提供回退；删除留待解耦验证稳定后

## Test Strategy

1. 导入与启动：`import app` 成功、服务起得来
2. 降级路径：无 key 时 POST /api/chat/stream 返回 activity/error/done 帧（HTTP 200）
3. 配置 key 后：token 流式输出、工具活动帧、done 落盘（/api/chat/last 可取回）
4. HITL：构造触发 ask_human 的对话 → question 帧 → answer 端点恢复 → 续流

## Migration Plan

1. 新增 `easel/agent_runtime.py`
2. app.py 三接缝
3. 安装 langchain-openai，重启验证
4. 回退：`ZIMEITI_RUNTIME=openclaw` 环境变量即回原路径；或丢弃分支

## Open Questions

- 无（业务工具接入归阶段二）
