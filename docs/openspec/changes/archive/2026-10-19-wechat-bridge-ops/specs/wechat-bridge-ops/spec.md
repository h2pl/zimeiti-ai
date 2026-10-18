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
