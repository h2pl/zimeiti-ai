---
comet_change: wechat-bridge-scaffold
---

# wechat-bridge-scaffold：微信通道桥——vendor 协议码 + 薄宿主骨架

## Why

用户要「像 xiaobei 那样在微信里跟 agent 对话」，但明确**不引入 openclaw**。

可行性取证（npm 拆包 + 源码审读，结论决定性）：

| 事实 | 证据 |
|---|---|
| 微信协议能力来自 `@tencent-weixin/openclaw-weixin`（npm 公开，2.4.10，**MIT，Tencent 官方**） | `npm view` + 包内 `LICENSE` |
| 协议形态：**ilink bot API**——`ilink/bot/getupdates`（长轮询收）+ `ilink/bot/sendmessage`（发）+ getconfig/sendtyping/notifystart/notifystop | `dist/src/api/api.js` 导出面 |
| 登录：`startWeixinLoginWithQr` + `waitForWeixinLogin`（二维码 + 扫码轮询） | `dist/src/auth/login-qr.js` |
| **协议核心零 openclaw 依赖**：`api.js` 与 `login-qr.js` 无任何 `openclaw/plugin-sdk` import；仅 `accounts.js`（登录态落盘）依赖 2 个 helper（`normalizeAccountId`/`mutateConfigFile`，各几行） | grep 逐个文件验证 |
| openclaw 本体（npm 2026.10.4）仅为**构建期类型**与宿主装配所需；运行时只需要协议函数 | peerDependencies + dist 引用面 |

**因此可以不引入 openclaw 引擎**：vendor 其 MIT 协议码，写一个本地 shim 提供那 2 个
helper，薄宿主直接驱动协议函数。

## What Changes

- 新目录 `apps/wechat/`（Node，**纯 JS 运行、零构建**——vendor 的是 dist）：
  - `vendor/openclaw-weixin/`：腾讯 MIT 协议码（**原样 vendor**，含 LICENSE 与
    NOTICE，版本 pin 记录；不允许改动协议码）
  - `shim/openclaw/`：本地 shim 包，`package.json` `exports` 提供
    `./plugin-sdk/*` 子路径，实现账号 id 规范化与配置文件读写（账户登录态落盘用）
  - `src/login.js`：扫码登录封装（vendor `login-qr.js` + 终端二维码 + 轮询）
  - `src/sessions.js`：微信用户 ↔ zimeiti 会话映射（本地 JSON 落盘，二期接 PG）
  - `src/bridge.js`：宿主骨架（长轮询循环、消息分发钩子、发送封装）——
    **本期只到「能收能发」的骨架**，真正桥接 zimeiti 是变更 ②
  - `src/index.js`：CLI 入口 `node src/index.js <login|start|status|version>`
- 许可证合规：`apps/wechat/NOTICE`（MIT 全文 + Tencent 版权 + 版本 pin + 改动说明
  「未改动协议码，仅 vendor」）；`make check` 增加合规断言（LICENSE/NOTICE 存在、
  vendor 文件与上游 tarball 哈希一致）
- Node 运行时要求写入 README（部署面多一个 Node 进程；Python 主服务零改动）

## Non-Goals

- **不引入 openclaw**（引擎/gateway/配置系统全部不要）——这是本变更的硬约束
- **不实现消息桥接**（微信→zimeiti→微信的完整回路）：`wechat-bridge-transport`
- 媒体（图片/语音）收发、群聊、多账号 allowlist：后续变更
- 不修改任何 Python 侧代码（零端点新增，verify 路由守卫不受影响）

## Capabilities

### New Capabilities

- `wechat-bridge-scaffold`：以合规方式 vendor 腾讯官方 ilink 协议码，并提供
  可独立运行的 Node 宿主骨架（扫码登录 + 长轮询 + 发送封装 + CLI），
  不依赖 openclaw

## Impact

新增 `apps/wechat/`（Node 包，自带 package.json，**不进 Python venv**）；
Makefile 增加 Node 侧检查（license 合规 + vendor 完整性）；README 部署章节
说明 Node 前提。Python 侧零改动。
