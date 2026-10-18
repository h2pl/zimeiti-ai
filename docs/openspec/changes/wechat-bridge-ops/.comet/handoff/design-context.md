# Comet Design Handoff

- Change: wechat-bridge-ops
- Phase: design
- Mode: compact
- Context hash: a584989e4f607966cf395bf86e44689c7e57834a7ae985004ff19081ec175aa4

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## docs/openspec/changes/wechat-bridge-ops/proposal.md

- Source: docs/openspec/changes/wechat-bridge-ops/proposal.md
- Lines: 1-47
- SHA256: 6fb72703db40b2620efa542f272d1df59d70bf714687c69625c6ee5f165747f1

```md
---
comet_change: wechat-bridge-ops
---

# wechat-bridge-ops：群聊/@触发、多账号、开机自启

## Why

批次 ①②③ 让桥「能对话、能收发媒体」，但仍是**开发态**：只能一个账号、只能
私聊、Ctrl+C 停了就没了。要作为日常生产力工具还差三块：

1. **群聊**：运营场景常在群里@机器人（取证：vendor 协议层无群处理——群语义属
   宿主职责，由我们定；ilink 群消息的字段名无法从 vendor 证实，按常见约定实现
   + 环境变量可配 + 联调校准）
2. **多账号**：一个桥跑多个微信（如主号 + 小号分流）
3. **开机自启**：launchd/systemd 单元 + 安装脚本，7×24 常驻

## What Changes

- `apps/wechat/src/group.js`：群消息判定（`room_id`/`group_id`/`chat_type`，
  字段名可配）+ @提及检测（bot id/名称，可配）+ 群会话前缀 `wxg-`
- dispatcher 接线：群消息**默认仅在@bot 时响应**（防骚扰）；@检测字段名可配；
  非@群消息静默跳过（不计错误）
- `index.js start`：遍历所有已登录账号，各起一个 bridge（多账号并行）；
  `status` 展示全部账号
- `apps/wechat/services/`：systemd 单元 + launchd plist 模板 + `install-service.sh`
  （自动选平台、填路径、enable+start）
- 探针扩展：群消息@/非@、多账号遍历、单文件内容校验

## Non-Goals

- 群内多人身份管理（按群共享会话，不按人拆分）
- Windows 服务（sc.exe/schtasks）——Linux/macOS 优先，Windows 用「启动项」
  说明文档
- 真机联调字段校准（需真实群消息样本，README 记录方法）

## Capabilities

### New Capabilities

- `wechat-bridge-ops`：桥具备群聊响应（默认@触发）、多账号并行与开机自驻能力，
  可从开发态转为日常常驻工具

## Impact

`apps/wechat/src/` 新增 `group.js` 与 dispatcher/index 接线；新增
`services/` 模板与安装脚本；零新第三方依赖；Python 侧零改动。

```

## docs/openspec/changes/wechat-bridge-ops/design.md

- Source: docs/openspec/changes/wechat-bridge-ops/design.md
- Lines: 1-65
- SHA256: e320160f29f77f2c7625d47129d28a12607ff335d1ddc25624ecf10ffd947de5

```md
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

```

## docs/openspec/changes/wechat-bridge-ops/tasks.md

- Source: docs/openspec/changes/wechat-bridge-ops/tasks.md
- Lines: 1-19
- SHA256: 942dd978421f7f9e64913f3025fca6296de96082c58c5fb9cdc8b1ed60c832f0

```md
---
comet_change: wechat-bridge-ops
---

# Tasks：wechat-bridge-ops

## 1. 群聊与多账号

- [ ] 1.1 group.js：isGroupMessage/isBotMentioned/groupKey/stripMention（字段名全可配）+ dispatcher 接线（非@静默） <!-- comet-task:431e8b3c-928f-4683-bb0e-9ddb851c9f06 -->
- [ ] 1.2 index.js start 多账号并行（单账号隔离）+ status 全账号展示 <!-- comet-task:477fa86b-934f-4dec-a02c-c99fe223e6f4 -->

## 2. 开机自启

- [ ] 2.1 services/：systemd 单元 + launchd plist 模板 + install-service.sh（平台判别/填路径/enable+start） <!-- comet-task:4d34bbf0-d08c-4442-888c-a9469a813fee -->
- [ ] 2.2 Python 校验测试（单元内容关键项）+ README 联调校准说明 <!-- comet-task:a295ac6e-65ba-4c0f-ad66-c3649fa4ef71 -->

## 3. 验证

- [ ] 3.1 node:test（群判定/@检测/前缀/非@静默/多账号遍历）+ 探针扩展 + make check 全绿 <!-- comet-task:5fa39c2c-0526-4811-85d3-c8271229f645 -->

```

## docs/openspec/changes/wechat-bridge-ops/.openspec.yaml

- Source: docs/openspec/changes/wechat-bridge-ops/.openspec.yaml
- Lines: 1-2
- SHA256: b552ab6519df8f66b705724100f565c5cd842bc9389aeaa177da9cec3d02a685

```md
schema: spec-driven
created: 2026-10-19

```

## docs/openspec/changes/wechat-bridge-ops/specs/wechat-bridge-ops/spec.md

- Source: docs/openspec/changes/wechat-bridge-ops/specs/wechat-bridge-ops/spec.md
- Lines: 1-47
- SHA256: b400526f8383c810986a1f1ad07c39865f606773942c48c3bf9fcaf6aa072cf5

```md
# wechat-bridge-ops 规格草案

## Purpose

桥从开发态转为常驻工具：群聊@触发、多账号并行、开机自启。

## ADDED Requirements

### Requirement: 群消息默认@触发

系统 SHALL 识别群消息（字段名可配：`room_id`/`group_id`/`chat_type`），且群内
MUST 默认仅在检测到@bot（bot id 或名称，可配）时才响应；非@群消息 MUST 静默
跳过（不回复、不报错）。

#### Scenario: 群内@bot
- **WHEN** 群消息文本包含 bot 的 id/名称（或服务端已置 at 标记）
- **THEN** 照常进入 agent，会话 id 为 `wxg-<roomId>` 形态

#### Scenario: 群内未@
- **WHEN** 群消息未包含@标记
- **THEN** 不回复、不计失败、不进 agent

#### Scenario: 私聊不受影响
- **WHEN** 私聊消息（无群字段）
- **THEN** 与现行为完全一致（无需@）

### Requirement: 多账号并行

`start` SHALL 为每个已登录账号各起一个桥实例并行运行；单账号失败 MUST NOT
影响其他账号；`status` SHALL 列出全部账号及其连通性。

#### Scenario: 两个账号
- **WHEN** 登录了两个微信账号后执行 `start`
- **THEN** 两个桥并行运行；`status` 展示两个账号

### Requirement: 开机自启

仓库 SHALL 提供 systemd 与 launchd 单元模板及安装脚本；安装后重启机器桥
MUST 自动恢复运行。Windows SHALL 有文档化的替代方案说明。

#### Scenario: Linux 安装
- **WHEN** 在 Linux 执行 `services/install-service.sh`
- **THEN** 生成并启用单元，`systemctl --user status zimeiti-wechat` 显示 active

#### Scenario: macOS 安装
- **WHEN** 在 macOS 执行同一脚本
- **THEN** 生成并 load plist，`launchctl list` 含 zimeiti-wechat

```
