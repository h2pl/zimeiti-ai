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
