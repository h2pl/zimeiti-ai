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
