# zimeiti 微信通道桥

在微信里跟 zimeiti 的 agent 对话。**vendor 腾讯官方 ilink 协议码**
（`@tencent-weixin/openclaw-weixin` v2.4.10，MIT，原样收录 + 哈希校验），
**不依赖 openclaw 引擎**——openclaw 在 xiaobei 里承担的「传输」角色由本桥承担，
agent 永远是 zimeiti（凭据/技能/护栏/记忆全在 Python 服务端，Node 侧零密钥）。

## 前提

- Node ≥ 18（协议码是 JS；Python 主服务不受影响）
- zimeiti 后端已启动（`make api` 或 `make dev`，默认 `http://127.0.0.1:8000`）

## 使用

```bash
cd apps/wechat
npm install

node src/index.js login     # 扫码登录（终端二维码，8 分钟有效；扫码后按手机提示确认）
node src/index.js status    # 登录态 / 会话映射 / zimeiti 连通性
node src/index.js start     # 常驻桥接：微信 → zimeiti → 微信
```

在微信里对机器人说话即可。发「新会话」清空上下文重新开始。

**媒体**：你可以直接发图片/文件/视频——桥会下载解密后落盘
（`state/media/<日期>/`），并告知 agent 路径。agent 回复中若包含独占一行的
`MEDIA:<本地路径或 https URL>`，该媒体会作为消息发回给你。语音暂不支持转码
（silk 格式），会落盘并如实说明。

## 环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `ZIMEITI_API` | `http://127.0.0.1:8000` | zimeiti 后端地址 |
| `WECHAT_STATE_DIR` | `apps/wechat/state` | 运行态目录（登录态/会话映射） |
| `WECHAT_ZIMEITI_TIMEOUT_MS` | `180000` | 单轮对话超时 |

## 架构

```
微信 → ilink getupdates（长轮询，vendor 协议码）
     → dispatcher（每用户串行锁 / 指令 / typing / 分段）
     → zimeiti-client → POST /api/chat/stream（SSE 读全文）
     → ilink sendmessage 回发（≤4000 字符/段）
```

- `vendor/openclaw-weixin/`：腾讯协议码（**勿改**，`make check` 哈希校验）
- `shim/openclaw/`：本地 shim，仅提供协议码可达的 3 个 plugin-sdk helper
- `src/`：login / transport / bridge / dispatcher / sessions / zimeiti-client / CLI

## 测试与验证

```bash
npm test        # node:test（零网络：本地 SSE 服务器 + 假 transport）
```

端到端探针（真实 zimeiti + 假 ilink，零 token）：

```bash
# 终端 1：起 zimeiti（8123）
cd apps/api && PYTHONUTF8=1 ./.venv/Scripts/python.exe -m zimeiti_api --port 8123
# 终端 2：跑探针
PYTHONUTF8=1 python apps/scripts/probe_wechat_bridge.py
```

## 群聊

群消息默认**仅在@机器人时响应**（防骚扰）；会话按群隔离（`wxg-<群id>`）。

> ⚠️ **联调校准**：ilink 群消息的字段名无法从协议码证实（vendor 不含群处理）。
> 若群里@了没反应，先看日志里的原始消息字段，再用环境变量校准：
> `WECHAT_GROUP_ID_FIELDS`（群 id 字段，逗号分隔）、`WECHAT_GROUP_AT_FIELDS`
> （@标记字段）、`WECHAT_GROUP_REQUIRE_MENTION=false`（关闭@要求）。

## 开机自驻

```bash
bash services/install-service.sh            # 安装并启动（Linux/macOS 自动判别）
bash services/install-service.sh --uninstall
```

- Linux：systemd 用户服务（`systemctl --user status zimeiti-wechat`），
  启动前会等待 zimeiti `/api/status` 就绪，崩溃自动重启
- macOS：launchd LaunchAgent（`launchctl list | grep com.zimeiti.wechat`）
- Windows：无服务形态——用「任务计划程序」（触发器：登录时；操作：
  `node <路径>\\src\\index.js start`，起始于 `apps/wechat`）或把 start
  快捷方式放进 `shell:startup` 文件夹

## 多账号

`login` 多次（每次不同微信扫码）即存入多账号；`start` 会为每个账号各起一个桥
实例并行运行，单账号异常不影响其余。

## 注意

- **协议登录有账号风险**（非官方客户端）——建议用专用微信小号，不要用主号
- 多账号/群聊/媒体（图片、语音）收发尚未实现，见后续变更
