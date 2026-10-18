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
