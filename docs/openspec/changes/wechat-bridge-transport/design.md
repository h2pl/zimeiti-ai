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
