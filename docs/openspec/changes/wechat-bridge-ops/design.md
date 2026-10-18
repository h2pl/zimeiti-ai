---
comet_change: wechat-bridge-ops
role: technical-design
canonical_spec: openspec
status: final
---

# 设计：wechat-bridge-ops

## 高层方案

```
apps/wechat/src/group.js
  isGroupMessage(msg)      room_id / group_id / chat_type=group 任一命中（字段名可配）
  isBotMentioned(msg, bot) 文本含 bot id/名称，或服务端 at 标记
                          （at_users/mentioned_users/is_at_me，可配）
  groupKey(msg)            'wxg-' + roomId（群会话前缀，防与私聊混）
  stripMention(text, bot)  去掉@前缀，给 agent 干净文本

dispatcher._process：isGroup && !isBotMentioned → 静默 return（不回复不计错）

index.js start：loadAccounts() 遍历 → 每账号一个 WechatBridge+Dispatcher，
Promise.allSettled 并行；单账号崩溃隔离（try/catch 包住每实例的 start）
status：逐账号输出 + zimeiti 连通性

services/
  zimeiti-wechat.service   systemd --user 单元（模板，install 脚本填路径）
  com.zimeiti.wechat.plist launchd 模板
  install-service.sh       平台判别 → 生成 → enable/load → start
```

## 关键决策

### D1：群字段名可配（证据不足时诚实）
vendor 协议层无群处理，ilink 群消息真实字段名**无法从代码证实**。取最常见约定
（`room_id`/`group_id`/`chat_type`），全部可用 `WECHAT_GROUP_*_FIELD` 环境变量
覆盖；README 写明联调校准方法（打日志看真实字段后改一处配置）。比硬编码更诚实。

### D2：群内默认@触发，防骚扰
群是公开场景——不@就响应等于机器人插话。默认需@（bot id 或昵称），可配
`WECHAT_GROUP_REQUIRE_MENTION=false` 关闭（私密小群场景）。

### D3：多账号 = 多桥实例，不共桥
每个账号独立 WechatBridge（独立长轮询/游标/停机），互不影响；共享 zimeiti 客户端。
`Promise.allSettled` 保证一个账号崩不拖死其余；每实例包 try/catch + 重启退避。

### D4：服务单元用 --user（systemd）与 LaunchAgents（launchd）
免 root、随用户会话生命周期，契合「本地个人工具」定位。Restart=always /
KeepAlive=true 保证崩溃自恢复。

### D5：Windows 用文档而非服务
桥是 Node 进程，Windows 服务包装（sc.exe/node-windows）成本高收益低——
README 给「任务计划程序」与「启动文件夹」两条路，够用且零依赖。

## 风险与对策

- **风险**：群字段名猜错 → 群消息不被识别（按私聊处理）→ 配置化 + 联调校准；
  识别但@检测失效 → 默认要求@，最坏是「群里不响应」而非「乱响应」（安全侧失效）
- **风险**：多账号 token 轮换频繁 → 每账号独立实例天然隔离
- **风险**：服务自启时 zimeiti 未就绪 → 单元加 `ExecStartPre` 等待
  `/api/status` 200（curl 重试循环）

## Open Questions

无。
