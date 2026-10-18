---
comet_change: wechat-bridge-transport
---

# 验证报告：wechat-bridge-transport（微信 ↔ zimeiti 桥接）

## Spec 场景核对

| Scenario | 结果 | 证据 |
|---|---|---|
| 一句话闭环（含稳定 session id） | ✅ | 探针：两条消息均回发、`sessionIds=['wx-u-probe-1','wx-u-probe-1']`（同用户稳定）、回复为**真实 agent 输出**（"你好呀，我是你的自媒体运营搭子…"） |
| 长回复分段（≤4000 不丢内容） | ✅ | 单测 `dispatcher 长回复按 4000 分段不丢内容`（9500 字符 → ≥3 段、拼接等于原文、每段 ≤4000） |
| 「新会话」指令 | ✅ | 单测 + 探针：指令回发确认、**不进 agent**（sessionIds 只有 2 条）、映射重置 |
| 后端不可达 → 可行动提示 | ✅ | 单测 + 探针（指向 127.0.0.1:9）：「⚠️ zimeiti 后端暂时不可达，请检查服务（make api）后重试」 |
| 后端错误帧透传 | ✅ | 单测 `chat 遇 error 帧抛出带摘要的异常`（「请重启后端」原样透传） |
| 同用户串行 / 不同用户并行 | ✅ | 单测 `dispatcher 同用户串行、不同用户并行`（顺序断言 start:B > end:A 且 start:C < end:A） |
| status 展示连通性 | ✅ | CLI 冒烟 + README 联调文档 |

## 自动化验证

- **node:test 15/15**：客户端 SSE 累积/error 帧/连接失败/ping；dispatcher 指令/
  会话稳定/锁/错误翻译/分段
- **端到端探针 PASS**（真实 zimeiti + 假 ilink transport，零 token）：闭环、
  会话稳定、typing 先行、指令、不同用户独立、不可达提示共 10 项断言
- **make check**：exit 0，**278 passed**
- **E2E 全量**：69/69、双端差异 0（Node 侧不影响浏览器层）

## 过程中抓出并修复的三个问题（诚实记录）

1. **config 常量式 STATE_DIR 不读 `WECHAT_STATE_DIR`**：scaffold 的 sessions
   测试因此读了真实 state 文件——**假绿灯**。改惰性解析函数
   （`stateDir()/sessionsFile()/accountsFile()`），并给测试加「隔离有效性
   前置断言」（断言 SESSIONS_FILE 就在临时目录里）。教训：测试隔离不能只靠
   设 env，要断言隔离真的生效
2. **`core.autocrlf=true` 切分支时改写 vendor 文件**：git checkout 把
   LICENSE/README 从 LF 改成 CRLF，哈希守卫报「vendor 被改动」。持久修复：
   `.gitattributes` 加 `apps/wechat/vendor/** -text`（与仓库既有的 comet
   快照豁免同范式），恢复原始字节后切分支复验不再被改写
3. **`node --test` 把 `test/` 目录下所有文件当测试跑**：探针驱动
   `driver_probe.mjs` 挂 60s 等 stdin。移至 `tools/`

## 已知边界（留给后续变更）

- 媒体（图片/语音文件）收发、群聊/@触发、多账号同时在线：后续变更
- **真微信联调需人工**：`node src/index.js login` 扫码（8 分钟窗口）后
  `start`——步骤已写入 `apps/wechat/README.md`；探针覆盖了除「真 ilink 网络」
  外的全部逻辑
- 协议登录账号风险已在 README 与主 README 明示（建议专用小号）
