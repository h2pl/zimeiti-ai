---
comet_change: wechat-bridge-ops
---

# 验证报告：wechat-bridge-ops（群聊@触发/多账号/开机自驻）

## Spec 场景核对

| Scenario | 结果 | 证据 |
|---|---|---|
| 群内@bot → 进 agent、会话 `wxg-<roomId>` | ✅ | 单测 `dispatcher 群内@bot`（sessionId 精确等于 `wxg-room-1`、@前缀被清洗） |
| 群内未@ → 静默跳过 | ✅ | 单测 `dispatcher 群内未@`（不进 agent/不回复/不计错三断言） |
| 私聊不受影响 | ✅ | 单测 `dispatcher 私聊仍无需@` + transport 既有用例全绿 |
| @要求可关闭 | ✅ | 单测 `dispatcher 群@检测可关闭`（env 置 false 后群内无需@） |
| 群/at 字段名可配 | ✅ | 单测 `isGroupMessage：字段名可配`、`isBotMentioned：at 字段名可配` |
| 多账号并行 + 单账号隔离 | ✅ | 实现（`Promise.allSettled` + 每实例 catch）；`start` 文案列出全部账号 |
| systemd/launchd 安装 | ✅ | Python 守卫 13 项（Restart=always/ExecStartPre 等待 /api/status/KeepAlive/RunAtLoad/占位符/卸载分支） |
| Windows 替代方案 | ✅ | README「开机自驻」节（任务计划程序 + 启动文件夹两步） |

## 自动化验证

- **node:test 36/36**（群判定/@检测/前缀/清洗/非@静默/私聊不回退/@可关 +
  transport/media/scaffold 既有 24 项不回归）
- **Python 服务单元守卫** 13 项全 PASS，接入 `make check` 第八连
- **make check**：exit 0，**278 passed**
- **媒体探针**：PASS（④ 的改动不触碰媒体链路，回归确认）
- **E2E 全量**：69/69、双端差异 0

## 过程中修正的一处（诚实记录）

`sessionFor` 的「已带前缀不重复加」守卫初版写成 `startsWith("wx")`——会把
**私聊 id 恰好以 wx 开头**的情形也误判为已前缀（scaffold 测试当即红：
`wx-user-abc` 少了 `wx-`）。收窄为 `startsWith("wxg-")`（群前缀专用）。

## 已知边界（联调时校准）

- **ilink 群消息真实字段名未经真机验证**（vendor 无群处理，无法从代码证实）：
  按 `room_id/group_id/chat_type` 常见约定实现 + 环境变量可配 + README 写明
  校准方法。若群里@了没反应，看日志原始字段后改一处配置即可——**识别失败的
  方向是安全的**（群里不响应，而非乱响应）
- 真机扫码联调仍需人工（`login` + `start`）
