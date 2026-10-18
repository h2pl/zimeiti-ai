# Comet Design Handoff

- Change: wechat-bridge-media
- Phase: design
- Mode: compact
- Context hash: c73ce4ee70c99e8720abb51765854c15b977f492b09724ed21a905186b7b787a

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## docs/openspec/changes/wechat-bridge-media/proposal.md

- Source: docs/openspec/changes/wechat-bridge-media/proposal.md
- Lines: 1-52
- SHA256: e208420462a9ae02823402a1ccb3dc0bf37cf55c1e071db8d221fbca8ccce30d

```md
---
comet_change: wechat-bridge-media
---

# wechat-bridge-media：微信媒体（图片/文件/视频）收发

## Why

桥接闭环已通（文本），但自媒体运营的核心资产是**图**——用户会发参考图，
agent 的产出（海报/图文）也要能发到微信。取证结论：vendor 协议码的媒体链路
**完整且零 openclaw SDK 依赖**——

- 发送：`messaging/send-media.js` 的 `sendWeixinMediaFile`（按 MIME 路由
  image/video/file：`cdn/upload.js` 上传 + `messaging/send.js` 发消息）
- 接收：入站消息 `item_list[]`（TEXT=1/IMAGE=2/VOICE=3/FILE=4/VIDEO=5），
  图片经 `cdn/pic-decrypt.js` 的 `downloadAndDecryptBuffer`（AES-ECB）解密
- 全链路 import 面已逐个审读（send/upload/mime/inbound/quote-store/state-dir/
  partial-quote）——**无一处引 openclaw/plugin-sdk**

## What Changes

- `apps/wechat/src/media.js`：
  - `extractMediaItems(msg)`：从 `item_list` 提取媒体项（type + 下载参数）
  - `saveInboundMedia(items, {downloadMedia, dir})`：下载解密落盘
    `state/media/<date>/<msgId>-<idx>.<ext>`（下载器可注入）
  - `parseMediaDirectives(text)`：解析 agent 回复中的 `MEDIA:<path|url>` 行
    （与 openclaw 生态同一约定——vendor channel.js 的 prompt 就教 agent 用这个格式）
- dispatcher 接线：
  - **发送**：回复含 MEDIA: 指令 → `sendWeixinMediaFile`（可注入，默认惰性
    import vendor）；文本部分照常发送
  - **接收**：入站含媒体 → 落盘 → 喂给 agent 的文本附注
    「用户发送了图片，已保存到 <path>」；回发确认
- 语音（VOICE）：落盘 + 如实标注「语音消息（silk 格式，暂不支持转码）」——
  **不假装能听懂**

## Non-Goals

- **语音转文本**（silk→mp3→ASR）：需 ffmpeg 与 ASR 凭据，后续变更
- 视频/文件的 agent 侧理解（只落盘与透传路径）
- 媒体内容的模型多模态输入（zimeiti 对话目前是文本契约）

## Capabilities

### New Capabilities

- `wechat-bridge-media`：微信与 agent 之间可收发图片/文件/视频——入站媒体
  落盘并告知 agent 路径，agent 回复经 `MEDIA:` 指令回发媒体

## Impact

`apps/wechat/src/` 新增 `media.js` 与 dispatcher 接线；零新第三方依赖；
Python 侧零改动。

```

## docs/openspec/changes/wechat-bridge-media/design.md

- Source: docs/openspec/changes/wechat-bridge-media/design.md
- Lines: 1-64
- SHA256: 12580a059aa3c28523773f5b2086892c2d67e8844171e4fa2241fa3f0b839362

```md
---
comet_change: wechat-bridge-media
role: technical-design
canonical_spec: openspec
status: final
---

# 设计：wechat-bridge-media

## 高层方案

```
apps/wechat/src/media.js
  extractMediaItems(msg)         item_list → [{type, msgId, idx, download}]
                                 download = {fullUrl?, encryptedQueryParam?, aesKeyBase64?, cdnBaseUrl?}
  saveInboundMedia(items, {downloadMedia, dir})
                                 → [{type, path, ok, error}]（下载器注入）
  parseMediaDirectives(text)     → {text: 去掉 MEDIA: 行的文本, media: [ref]}
                                 MEDIA: 必须独占一行（vendor 约定）

dispatcher 接线
  入站：extractMediaItems → saveInboundMedia（默认 vendor pic-decrypt 惰性加载）
        → agent 文本 = 原文 + 附注（类型/路径/ silk 提示）
  出站：parseMediaDirectives(reply) → 先发文本 → 逐个 sendWeixinMediaFile
        （默认 vendor send-media 惰性加载，可注入）
```

## 关键决策

### D1：MEDIA: 指令采用 openclaw 同款约定
vendor `channel.js` 的系统提示就要求 agent「MEDIA: 标签独占一行」——沿用同一
约定，未来若迁移到 openclaw 宿主无需改 agent 行为。解析严格：行首 `MEDIA:`，
前后空白容忍，其余形态不认（防误把正文当路径）。

### D2：下载/上传全部可注入
`downloadMedia(item)` 与 `sendMedia({filePath, to, text})` 两个注入点，默认值
惰性 import vendor（真实环境），测试注入 fake（零网络）。这与 scaffold 的
transport 注入同一范式。

### D3：入站媒体「落盘 + 告知路径」，不假装理解
zimeiti 对话是文本契约，不看图。桥的职责是把媒体变成 agent 可引用的**路径
事实」——后续多模态是 zimeiti 侧的独立演进，桥不必等它。

### D4：语音如实标注
silk 是微信私有格式，转码需 ffmpeg + ASR。当前落盘并附注「暂不支持转码」——
诚实优先，绝不谎称已转文本（与项目「不可得则如实」原则一致）。

### D5：失败隔离
单个媒体下载/发送失败不影响同轮其他媒体与文本（try/catch 逐项），失败项给
用户如实提示。

## 风险与对策

- **风险**：ilink 的 item_list 字段名与文档不符（vendor 是唯一权威）→
  `extractMediaItems` 只认 `type` 数值 + 常见的 media 字段名集合，未知形态
  原样保留 download 参数交由 vendor 函数尝试；单测用 vendor 真实字段名固化
- **风险**：MEDIA: 路径含空格/中文 → 整行剩余部分作为路径（不 split），
  `file://` 前缀剥离
- **风险**：远程 URL 下载大文件 → 沿用 vendor `downloadRemoteImageToTemp`
  （已有大小/超时约束）

## Open Questions

无。

```

## docs/openspec/changes/wechat-bridge-media/tasks.md

- Source: docs/openspec/changes/wechat-bridge-media/tasks.md
- Lines: 1-15
- SHA256: eedbff7b085b5ddca85ef83af68f8f2b8d42c56994aebef3ddaea9621b36b198

```md
---
comet_change: wechat-bridge-media
---

# Tasks：wechat-bridge-media

## 1. 媒体模块

- [ ] 1.1 media.js：extractMediaItems / saveInboundMedia（下载器注入）/ parseMediaDirectives（独占行约定） <!-- comet-task:1c0abb3d-6b4b-492d-a715-0e66cc89a2d8 -->
- [ ] 1.2 dispatcher 接线：入站落盘+附注、出站 MEDIA 回发（发送器注入）；语音 silk 如实标注 <!-- comet-task:7bfd27e1-21c0-4292-8c12-5129516048dd -->

## 2. 验证

- [ ] 2.1 node:test：提取/落盘（含失败隔离）/指令解析（独占行/路径保真/MEDIA 行剥离）/dispatcher 双向接线 <!-- comet-task:2bd7054f-b8a3-471f-9b96-27205895849f -->
- [ ] 2.2 探针扩展：入站图片（假下载器）+ 出站 MEDIA（假发送器）；make check 全绿 <!-- comet-task:a8d935a3-b768-4232-b7c3-a75a4bb09129 -->

```

## docs/openspec/changes/wechat-bridge-media/.openspec.yaml

- Source: docs/openspec/changes/wechat-bridge-media/.openspec.yaml
- Lines: 1-2
- SHA256: dc08c29816def5c12ac71497ed005c1c0d6d779aa76f03fa6cd1d3ed38d91ec9

```md
schema: spec-driven
created: 2026-10-18

```

## docs/openspec/changes/wechat-bridge-media/specs/wechat-bridge-media/spec.md

- Source: docs/openspec/changes/wechat-bridge-media/specs/wechat-bridge-media/spec.md
- Lines: 1-46
- SHA256: b3136a1e7ec04a2412f98262bbf3c4bf9b941be8e4f3a4ad55a082593429a662

```md
# wechat-bridge-media 规格草案

## Purpose

微信与 agent 之间收发图片/文件/视频：入站媒体落盘并告知 agent 路径；agent 回复
经 `MEDIA:` 指令回发媒体。语音只落盘并如实标注不支持转码。

## ADDED Requirements

### Requirement: 入站媒体落盘并告知 agent

系统 SHALL 从入站消息 `item_list` 识别媒体项（IMAGE/VOICE/FILE/VIDEO），
下载解密后落盘到 `state/media/<date>/`，并在送给 agent 的文本中 MUST 附注
媒体类型与落盘路径；MUST NOT 假装理解媒体内容。

#### Scenario: 用户发图片
- **WHEN** 用户发送一张图片（item_list 含 IMAGE 项）
- **THEN** 图片解密落盘；agent 收到「用户发送了图片，已保存到 <path>」；
  用户收到「已收到图片」确认

#### Scenario: 用户发语音
- **WHEN** 用户发送语音（silk 格式）
- **THEN** 语音落盘；agent 收到的附注如实写明「语音消息（silk 格式，暂不支持
  转码）」；不谎称已转文本

#### Scenario: 下载失败
- **WHEN** 媒体下载或解密失败
- **THEN** 该媒体跳过（其余消息照常处理），用户收到如实失败提示

### Requirement: 出站媒体经 MEDIA 指令回发

agent 回复中独占一行的 `MEDIA:<本地路径或 https URL>` MUST 被解析为该条回复
的媒体附件：本地文件或远程 URL 下载后经协议上传发送（按 MIME 路由
image/video/file）；MEDIA 行本身 MUST NOT 出现在发给用户的文本里。

#### Scenario: 回复带本地图片
- **WHEN** agent 回复「这是海报\nMEDIA:/path/poster.png」
- **THEN** 用户先收到文本「这是海报」，再收到该图片消息

#### Scenario: 远程 URL 媒体
- **WHEN** MEDIA: 指向 https 图片 URL
- **THEN** 桥下载后上传发送（不要求 agent 先下载）

#### Scenario: 媒体发送失败
- **WHEN** 上传或发送失败（如文件不存在）
- **THEN** 用户收到如实失败提示，文本部分不受影响

```
