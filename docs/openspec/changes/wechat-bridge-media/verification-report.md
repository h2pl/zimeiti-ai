---
comet_change: wechat-bridge-media
---

# 验证报告：wechat-bridge-media（微信媒体收发）

## Spec 场景核对

| Scenario | 结果 | 证据 |
|---|---|---|
| 用户发图片 → 落盘 + 告知 agent + 确认 | ✅ | 单测 `dispatcher 入站图片`；探针「入站图片附注路径」（agent 收到「用户发送了图片，已保存到 <path>」）、「入站确认回发」（已收到图片）、「入站媒体落盘」（png 落盘） |
| 用户发语音 → 落盘 + 如实标注不转码 | ✅ | 单测 `saveInboundMedia 落盘并按类型命名；silk 标注`（`mediaLabel(3)` 含 silk 字样）；vendor `silkToWav` 可用时自动升级措辞 |
| 下载失败隔离 | ✅ | 单测 `saveInboundMedia 单个失败不影响其余`（第一个抛错、第二个成功落盘） |
| 回复带本地图片 → 先文本后媒体 | ✅ | 单测 + 探针「出站先发文本」「出站媒体发送」（filePath/to 正确） |
| MEDIA 行不出现在文本里 | ✅ | 单测 `parseMediaDirectives`（独占行才认、行内形态不算、路径含空格保真、file:// 剥离）；探针「出站 MEDIA 行不出现」 |
| 媒体发送失败 → 文本照发 + 如实提示 | ✅ | 单测 `dispatcher 媒体发送失败` |

## 自动化验证

- **node:test 24/24**（含 transport/scaffold 既有用例）
- **媒体探针 PASS**（真实 dispatcher + 假下载器/假发送器，零网络零 token）：
  入站附注/确认/落盘 + 出站先文本后媒体 + MEDIA 行剥离 + 发送参数
- **make check**：exit 0，**278 passed**
- **vendor 守卫**：PASS（合规三件套/哈希完整性/零 openclaw 引擎依赖）

## 过程中修正的一处（诚实记录）

**初版手写媒体字段名被 vendor 源码纠正**：我按常见命名猜了
`full_url/encrypted_query_param/aes_key_base64`，单测首跑即红。读
`media/media-download.js`（vendor 权威实现）后发现真实形态是
`image_item.media.encrypt_query_param` + `image_item.aeskey`（hex 需转
base64）+ `file_item.file_name`。**改为直接调用 vendor 的
`downloadMediaFromItem`**（字段名/AES 解密/silk 转码尝试全包），自己的
`extractMediaItems` 只做类型过滤、保留原始 item 交 vendor 解析——消掉了一整类
「猜字段」的漂移风险。

另：探针驱动的 `existsSync` 初版查默认 state 目录而非 `WECHAT_STATE_DIR`，
导致「落盘」断言假红——已修。

## 已知边界

- **真微信联调需人工**（扫码 + 发图/收图）——探针覆盖了除真 ilink 网络外全部逻辑
- 语音 ASR（silk→文本）未做：vendor 有 silkToWav（需 ffmpeg），ASR 需凭据——后续
- 媒体内容的多模态理解（让 agent「看懂」图）是 zimeiti 对话契约的演进，桥只负责
  路径透传
