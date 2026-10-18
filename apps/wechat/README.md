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

## 注意

- **协议登录有账号风险**（非官方客户端）——建议用专用微信小号，不要用主号
- 多账号/群聊/媒体（图片、语音）收发尚未实现，见后续变更
