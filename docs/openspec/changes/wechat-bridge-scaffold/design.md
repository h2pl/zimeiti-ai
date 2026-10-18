---
comet_change: wechat-bridge-scaffold
role: technical-design
canonical_spec: openspec
status: final
---

# 设计：wechat-bridge-scaffold

## 高层方案

```
apps/wechat/                        （Node 包，纯 JS 运行零构建；不进 Python venv）
  package.json                      dependencies 仅 qrcode-terminal（vendor 需要）；
                                    "openclaw" 解析到本地 shim（file:./shim/openclaw）
  NOTICE / vendor/openclaw-weixin/   腾讯 MIT 协议码原样收录 + 合规三件套
  shim/openclaw/                    本地包：exports 提供 ./plugin-sdk/*
    plugin-sdk/account-id.js        normalizeAccountId（小写+去空白+限长）
    plugin-sdk/config-mutation.js   mutateConfigFile（读-改-原子写 JSON）
  src/
    config.js                       路径与常量（state 目录、上游版本 pin）
    login.js                        登录：vendor login-qr 的 start/wait + 终端二维码
    transport.js                    ilink 长轮询/发送的薄封装（可注入，单测不触网）
    bridge.js                       宿主骨架：轮询循环 + 分发钩子（本期不接 zimeiti）
    sessions.js                     微信 id ↔ zimeiti 会话映射（JSON 落盘）
    index.js                        CLI：login / status / version
  test/                             node:test 单测（不触网，假 transport）
```

## 关键决策

### D1：vendor dist 而非 TS 源码
vendor 的是 npm 包内 **dist/（编译后 JS）**：运行时零构建、不引入 TS 工具链；
TS 源码不进仓（体积与构建面）。NOTICE 记录版本 pin，`make check` 用
**内容哈希**校验 vendor 与上游 tarball 一致（防篡改 + 防漂移）。

### D2：shim 只实现真正用到的 2 个 helper
取证显示协议函数（`api.js`/`login-qr.js`）**零 SDK 依赖**；只有 `accounts.js`
（登录态落盘）用 `normalizeAccountId` + `mutateConfigFile`。shim 就实现这两个
（其余 SDK 子路径不提供——import 不到即说明有人越界，fail-fast 比宽容好）。

### D3：transport 可注入
长轮询/发送全部走 `transport.js` 的薄封装并接受注入对象——单测用假 transport
驱动登录/轮询/发送全流程，**不触网、不扫码**。真实运行才接 ilink。

### D4：登录态落盘在 apps/wechat/state/（gitignore）
与 xiaobei 的「程序/数据分离」原则一致：协议码与代码是程序，登录态/会话映射是
数据。目录进 `.gitignore`，README 说明备份面。

### D5：CLI 而非 daemon（本期）
本期只做 `login/status/version` 三个命令；常驻轮询在变更 ② 随桥接一起做
（`start` 命令）。避免本期交付一个「能连微信但不回话」的半成品进程。

## 风险与对策

- **风险**：上游插件升级破坏 shim 假设（新版本多 import SDK 子路径）→ NOTICE
  记录 pin 版本；`make check` 哈希校验会在升级时显式失败，强制人工复核
- **风险**：vendor 被无意修改 → 同哈希校验拦截
- **风险**：Node 版本差异 → package.json `engines: node>=18`；只用稳定 API
- **风险**：协议码许可变化（MIT 现可放心）→ NOTICE 固定记录许可全文

## Open Questions

无。
