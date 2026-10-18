# wechat-bridge-media Specification

## Purpose
微信与 agent 之间收发图片/文件/视频：入站媒体落盘并告知 agent 路径；agent 回复
经 `MEDIA:` 指令回发媒体。语音只落盘并如实标注不支持转码。

## Requirements

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
