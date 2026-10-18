# Comet Design Handoff

- Change: wechat-bridge-transport
- Phase: design
- Mode: compact
- Context hash: 070ba40aa5c35347f08a01d7fc0c0751774c0d8fb2c3496cf0ba38aedac0c576

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## docs/openspec/changes/wechat-bridge-transport/proposal.md

- Source: docs/openspec/changes/wechat-bridge-transport/proposal.md
- Lines: 1-54
- SHA256: 14a8fa042d6173b00ebc94e303168a9b472973f02fd3f8c1af35fe147c3e8606

```md
---
comet_change: wechat-bridge-transport
---

# wechat-bridge-transport：微信消息 ↔ zimeiti agent 桥接

## Why

`wechat-bridge-scaffold` 已交付合规 vendor 的 ilink 协议码与宿主骨架（扫码登录 /
长轮询 / 发送 / 会话映射 / CLI），但 `start` 是占位——**消息还到不了 agent**。
本变更补上最后一环：微信里说一句话 → zimeiti agent 回复 → 回到微信。

设计原则（用户已确认）：**openclaw 只做传输的角色由本桥承担，agent 永远是
zimeiti**——不引入 openclaw、不在 Node 侧跑任何 LLM；凭据、技能、护栏、记忆
全部留在 Python 服务端。

## What Changes

- `apps/wechat/src/zimeiti-client.js`：zimeiti HTTP 客户端（fetch，Node ≥18 自带）：
  - `chat({ sessionId, message })`：POST `/api/chat/stream`，读 SSE 收全文
    （token 累积、activity 转 typing 指示、error 透传）
  - `ping()`：GET `/api/status` 连通性自检
- `apps/wechat/src/index.js` 的 `start` 命令落地：
  - 登录态加载（无登录态给出 login 指引并不退出码 1）
  - 长轮询循环（① 的 bridge 骨架）+ **onMessage 钩子**：
    1. 指令识别（「新会话」→ resetSession 重建；其余照常）
    2. sessionFor(wechatUserId) 拿 zimeiti 会话
    3. zimeiti-client.chat 拿回复（先发 typing 指示，长耗时时微信侧有反馈）
    4. sendMessage 回发（超过 4000 字按协议 textChunkLimit 分段）
  - 每用户串行（同一微信用户的会话锁，防并发写乱上下文）
- 错误处理：zimeiti 不可达 → 微信里如实告知「后端暂时不可达，稍后再试」
  （不静默丢弃）；LLM 错误帧 → 如实透传
- 探针 `apps/scripts/probe_wechat_bridge.py`：真实服务 + 假 ilink transport
  跑通「入站 → zimeiti（mock LLM）→ 回发」全链路，**不消耗 token**

## Non-Goals

- **不在 Node 侧持有任何模型凭据**（key 全在 Python 服务端）
- 媒体（图片/语音文件）收发：后续变更
- 群聊/@触发：后续变更（当前只处理私聊 direct）
- 多微信账号同时在线：当前单账号（scaffold 已支持多账号存储，本期跑单实例）

## Capabilities

### New Capabilities

- `wechat-bridge-transport`：微信私聊消息经长轮询进入 zimeiti agent，回复经
  ilink 回到微信；会话按微信用户稳定映射；后端不可达时如实告知用户

## Impact

`apps/wechat/src/` 新增客户端与 start 命令实现；Python 侧零改动（只消费既有
`/api/chat/stream` 与 `/api/status`）；新增探针脚本接入 make verify 之外的手动
验证（探针需 mock，不进 make check 计时）。

```

## docs/openspec/changes/wechat-bridge-transport/design.md

- Source: docs/openspec/changes/wechat-bridge-transport/design.md
- Lines: 1-76
- SHA256: 55632b4e44e26c1d2e58004c9626a3f76022d353d6c6cef6f7a1a96bce7b4390

```md
---
comet_change: wechat-bridge-transport
role: technical-design
canonical_spec: openspec
status: final
---

# 设计：wechat-bridge-transport

## 高层方案

```
apps/wechat/src/
  zimeiti-client.js   fetch 客户端（零三方依赖）
                      chat({sessionId,message}) → SSE 读全文
                        token 累积；activity → onProgress 回调（桥转 typing）；
                        error 帧 → throw 带摘要
                      ping() → /api/status
  dispatcher.js       入站分发：指令识别 → 会话锁 → chat → 分段回发
                      （每用户 Promise 链锁；错误翻译成用户可读中文）
  index.js            start 命令：登录态 → bridge.start({ onMessage })
```

消息流：

```
微信 → ilink getUpdates（长轮询）
     → dispatcher.handle(msg)
         ├─ 「新会话」→ sessions.resetSession → 回复「已开新会话」
         ├─ 其余 → sessions.sessionFor(userId)
         │        → transport.typing（先给反馈）
         │        → zimeiti-client.chat(session, text)
         │        → 分段 sendMessage（≤4000/段）
         └─ 失败 → 如实中文提示
```

## 关键决策

### D1：零三方依赖客户端
Node ≥18 的 `fetch` + `ReadableStream` 读 SSE。不引 axios/eventsource——
部署面最小，且与 CLI 探针的 Python 客户端同契约（都读 `event:`/`data:` 帧）。

### D2：每用户 Promise 链锁
同一微信用户的消息进同一条 Promise 链（`tail = tail.then(...)`），天然串行且
不失帧；不同用户各一条链，互不阻塞。比互斥锁实现简单，无需引入库。

### D3：typing 指示先行
ilink 有 `sendtyping`。LLM 首 token 常要数秒——先发 typing，微信侧显示
「正在输入」，避免用户以为没反应。这是 xiaobei 体验的关键细节（openclaw 侧
对应 `sendTyping`）。

### D4：错误如实翻译（对齐项目诚实原则）
- 连接失败 → 「zimeiti 后端暂时不可达，请稍后再试」
- error 帧 → 透传摘要（如「❌ 后端代码已变更——请重启后端」）
- 绝不静默丢弃、绝不假装成功

### D5：分段上限 4000
协议码 `outbound.textChunkLimit = 4000`（channel.js 自述）。按字符切分，
在换行/句号边界优先（找不到就硬切，保证不丢内容）。

### D6：探针用假 transport + mock zimeiti
探针起真实 zimeiti 服务（mock LLM，零 token）+ 假 ilink transport 注入 bridge，
断言「入站 → 会话 id 正确 → 回复内容回发」。真扫码真微信的联调留人工
（README 写明步骤）。

## 风险与对策

- **风险**：SSE 中途断流 → 客户端设超时（默认 180s，环境变量可调）；
  断流时把已收到的部分作为回复发出并附注「（回复不完整）」——不丢用户已等到的内容
- **风险**：微信用户狂发 → 每用户串行天然限速；另加「处理中」短回复防重复触发
- **风险**：会话映射文件并发写 → scaffold 的 mutateConfigFile 式串行队列沿用
  （sessions.js 同目录文件，加锁）

## Open Questions

无。

```

## docs/openspec/changes/wechat-bridge-transport/tasks.md

- Source: docs/openspec/changes/wechat-bridge-transport/tasks.md
- Lines: 1-20
- SHA256: f5d5252fef4ee8a538eaa9fda5293d9ff2573217eb8afacc554b66c51c63af65

```md
---
comet_change: wechat-bridge-transport
---

# Tasks：wechat-bridge-transport

## 1. 客户端与分发

- [ ] 1.1 zimeiti-client.js：chat（SSE 读全文 + activity 回调 + error 透传 + 超时）+ ping；单测（本地 SSE 服务器） <!-- comet-task:7e88209f-d4b3-4a30-b580-41a836fd7ee8 -->
- [ ] 1.2 dispatcher.js：指令识别 + 每用户串行锁 + typing 先行 + 分段回发 + 错误如实翻译 <!-- comet-task:756a784d-fb9e-4448-b178-06c64b81e7e3 -->

## 2. start 命令与探针

- [ ] 2.1 index.js start 落地（登录态检查 → bridge 装配 onMessage → 状态展示） <!-- comet-task:30205772-cef0-4b9a-bd5e-ed31461efcc4 -->
- [ ] 2.2 探针 probe_wechat_bridge.py：真实 zimeiti（mock LLM）+ 假 ilink transport，断言闭环与会话 id；README 联调步骤 <!-- comet-task:05fe5e6c-7f72-4fe7-a4b8-d3c4d9664554 -->

## 3. 验证

- [ ] 3.1 node:test 全量（客户端/分发/锁/分段/错误路径）+ make check 全绿 <!-- comet-task:7c765405-98a6-4a05-9fe1-b9f73e701619 -->
- [ ] 3.2 探针 PASS + CLI status 展示连通性 <!-- comet-task:7028d90f-6209-461e-a62a-58e937b5c675 -->

```

## docs/openspec/changes/wechat-bridge-transport/.openspec.yaml

- Source: docs/openspec/changes/wechat-bridge-transport/.openspec.yaml
- Lines: 1-2
- SHA256: dc08c29816def5c12ac71497ed005c1c0d6d779aa76f03fa6cd1d3ed38d91ec9

```md
schema: spec-driven
created: 2026-10-18

```

## docs/openspec/changes/wechat-bridge-transport/specs/wechat-bridge-transport/spec.md

- Source: docs/openspec/changes/wechat-bridge-transport/specs/wechat-bridge-transport/spec.md
- Lines: 1-57
- SHA256: 6eb68160e77ed1fcabe3a8db8ed34f64c05d837b99cc2a02c968ddeb376ba63e

```md
# wechat-bridge-transport 规格草案

## Purpose

把微信私聊消息桥到 zimeiti agent 并把回复发回微信——openclaw 的「传输」角色
由本桥承担，agent 永远是 zimeiti（无 openclaw、Node 侧无凭据）。

## ADDED Requirements

### Requirement: 入站消息到 agent

桥 MUST 将每条私聊文本消息送到 zimeiti：以该微信用户的稳定映射会话 id 调
`POST /api/chat/stream`，读取 SSE 直至 `[DONE]` 累积完整回复，再经 ilink
发回该用户。MUST NOT 在 Node 侧读取或存储任何模型凭据。

#### Scenario: 一句话闭环
- **WHEN** 微信用户发「你好」，zimeiti 返回「你好呀」
- **THEN** 该用户收到「你好呀」；会话 id 为 `wx-<userId>` 形态且跨消息稳定

#### Scenario: 长回复分段
- **WHEN** 回复超过 4000 字符
- **THEN** 按协议上限分段发送，内容不丢不重

### Requirement: 会话指令

系统 MUST 支持「新会话」指令：解绑该用户的会话映射，下一条消息起用新会话。
其余文本 MUST 原样进入 agent（不拦截、不改写）。

#### Scenario: 新会话
- **WHEN** 用户发送「新会话」随后发送「继续上面的话题」
- **THEN** 后者进入一个**全新**的 zimeiti 会话（不含此前上下文）

### Requirement: 故障如实告知

zimeiti 不可达或返回错误帧时，系统 MUST 给用户可行动的中文提示
（「后端暂时不可达」/错误摘要），MUST NOT 静默丢弃消息。

#### Scenario: 后端不可达
- **WHEN** zimeiti 服务停止时用户发消息
- **THEN** 用户收到「zimeiti 后端暂时不可达，请稍后再试」；桥继续运行不退出

#### Scenario: 后端错误帧
- **WHEN** `/api/chat/stream` 返回 error 帧（如 LLM 故障）
- **THEN** 用户收到该错误的如实摘要（不假装成功）

### Requirement: 并发与状态

同一微信用户的连续消息 MUST 串行处理（会话锁）；不同用户 MUST 互不阻塞。
`status` 命令 MUST 展示桥与 zimeiti 的连通性。

#### Scenario: 同用户串行
- **WHEN** 同一用户连发两条消息
- **THEN** 第二条在第一轮回复完成后才开始处理（上下文不乱）

#### Scenario: 不同用户并行
- **WHEN** 两个用户同时发消息
- **THEN** 两轮处理互不等待（各自独立锁）

```
