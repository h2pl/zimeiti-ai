---
comet_change: wechat-bridge-media
role: technical-design
canonical_spec: openspec
archived-with: 2026-10-18-wechat-bridge-media
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
