# Comet Design Handoff

- Change: wechat-bridge-scaffold
- Phase: design
- Mode: compact
- Context hash: 7c4133c40d42a5c779083297da22f2288cbdb9961fcd8c4a2f799c4248fa6246

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## docs/openspec/changes/wechat-bridge-scaffold/proposal.md

- Source: docs/openspec/changes/wechat-bridge-scaffold/proposal.md
- Lines: 1-60
- SHA256: 54fd4471432ab9aa3f391498365feb3f5f5534f80f4e7d3fba4898103de483d8

```md
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

```

## docs/openspec/changes/wechat-bridge-scaffold/design.md

- Source: docs/openspec/changes/wechat-bridge-scaffold/design.md
- Lines: 1-64
- SHA256: d7ba493149e7a2253dad1ffd69a065e779451e3d573f956ecdb275641ef0acc7

```md
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

```

## docs/openspec/changes/wechat-bridge-scaffold/tasks.md

- Source: docs/openspec/changes/wechat-bridge-scaffold/tasks.md
- Lines: 1-20
- SHA256: 3519f5c3322b64af805daad3647e66f4a53d5eee4bef554ec427d63562e8b381

```md
---
comet_change: wechat-bridge-scaffold
---

# Tasks：wechat-bridge-scaffold

## 1. Vendor 与合规

- [ ] 1.1 vendor/openclaw-weixin（dist 原样 + LICENSE）+ NOTICE（来源/版本/MIT/未改动声明）+ 版本 pin 记录 <!-- comet-task:bc756bab-1908-4cce-87f6-e97d7ceb27b2 -->
- [ ] 1.2 scripts/verify_wechat_vendor.py：vendor 哈希校验 + 合规三件套断言 + openclaw 引擎依赖扫描；接入 make check <!-- comet-task:9e708b3c-0497-4d36-a1a9-dce383eb519e -->

## 2. Shim 与宿主骨架

- [ ] 2.1 shim/openclaw（account-id + config-mutation 两个 helper）+ package.json exports 解析 <!-- comet-task:cf17caf2-ce7f-477e-b0ae-dea97ce75be8 -->
- [ ] 2.2 src/login.js（二维码登录+轮询+落盘）/ transport.js（可注入）/ bridge.js（骨架）/ sessions.js / index.js（CLI） <!-- comet-task:7cb5757a-a6ee-442e-8cdb-4cf8bbff0bdd -->

## 3. 验证与文档

- [ ] 3.1 node:test 单测（shim 两 helper / 登录流程假 transport / 状态自检 / CLI 退出码） <!-- comet-task:0e8880c1-c04b-4129-b159-15a49ee93259 -->
- [ ] 3.2 make check 全绿（含新 vendor 守卫）+ README 部署章节（Node 前提） <!-- comet-task:f0110dca-80e2-4f8e-a0ad-04b981a9e7ab -->

```

## docs/openspec/changes/wechat-bridge-scaffold/.openspec.yaml

- Source: docs/openspec/changes/wechat-bridge-scaffold/.openspec.yaml
- Lines: 1-2
- SHA256: dc08c29816def5c12ac71497ed005c1c0d6d779aa76f03fa6cd1d3ed38d91ec9

```md
schema: spec-driven
created: 2026-10-18

```

## docs/openspec/changes/wechat-bridge-scaffold/specs/wechat-bridge-scaffold/spec.md

- Source: docs/openspec/changes/wechat-bridge-scaffold/specs/wechat-bridge-scaffold/spec.md
- Lines: 1-49
- SHA256: a472ab09057a538ac5441f6d3fa8772f44fc3ca968dc29bdf327095fbb3737d4

```md
# wechat-bridge-scaffold 规格草案

## Purpose

合规地 vendor 腾讯官方 ilink 微信协议码，并提供不依赖 openclaw 的 Node 宿主
骨架，使「扫码登录 + 长轮询收 + 发送」能力可在 zimeiti 部署中独立运行。

## ADDED Requirements

### Requirement: 协议码合规 vendor

`apps/wechat/vendor/openclaw-weixin/` SHALL 原样收录 `@tencent-weixin/openclaw-weixin`
的 MIT 协议码，MUST NOT 修改其源码；仓库 MUST 含 NOTICE 记录来源、版本、许可与
「未改动」声明；`make check` MUST 断言 LICENSE/NOTICE 存在且 vendor 文件与上游
tarball 内容哈希一致（防偷偷改动）。

#### Scenario: 合规三件套
- **WHEN** 检查 `apps/wechat/`
- **THEN** 存在 `vendor/openclaw-weixin/LICENSE`、`NOTICE`，且 NOTICE 含包名、
  版本号、MIT 声明与「未改动」说明

#### Scenario: 防篡改
- **WHEN** 任何人修改了 vendor 内任一协议码文件
- **THEN** `make check` 的 vendor 完整性断言失败（哈希不一致）

### Requirement: 零 openclaw 依赖

宿主与 shim MUST NOT 依赖 openclaw 引擎：不得安装 `openclaw` 包、不得 import
其 gateway/配置系统；对 `openclaw/plugin-sdk/*` 的引用 MUST 由本地 shim 满足。
`make check` MUST 有断言扫描 `apps/wechat/`（vendor 除外）无 openclaw 引擎依赖。

#### Scenario: 依赖面
- **WHEN** 检查 `apps/wechat/package.json` 与全部源码 import
- **THEN** dependencies 不含 `openclaw`；源码 import 的 `openclaw/plugin-sdk/*`
  全部经 shim 的 exports 映射解析

### Requirement: 宿主骨架可用

CLI SHALL 提供 `login`（终端二维码 + 扫码轮询，落盘登录态）、`status`（登录态
与配置自检）、`version`（协议码版本）；长轮询与发送封装 MUST 以可注入的
transport 实现（单测不触网）。

#### Scenario: 状态自检
- **WHEN** 未登录时执行 `node src/index.js status`
- **THEN** 输出「未登录」并给出 `login` 指引，退出码非 0

#### Scenario: 登录态落盘
- **WHEN** 完成一次登录流程（单测以假 transport 驱动）
- **THEN** 登录态写入 `apps/wechat/state/`（gitignore），`status` 识别为已登录

```
