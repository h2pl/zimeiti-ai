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
