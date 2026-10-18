---
comet_change: cli-entry-point
role: technical-design
canonical_spec: openspec
status: final
---

# 设计：cli-entry-point

## 高层方案

```
apps/api/zimeiti_cli/
  client.py     HTTP 客户端（urllib，零三方依赖）
                - get/post/delete：统一 Origin 头 + JSON 解析 + 可行动错误
                - sse_chat()：读 /api/chat/stream，逐帧 yield (event, data)
                - ApiError 带 status/body——把 4xx/5xx 翻成中文可读
  cli.py        argparse 子命令树
                chat / flows(list|new|run) / runs / usage
                chat 流式打印：token→stdout 无换行累积；activity→stderr 灰字；
                error→stderr 红字 + 非 0 退出
```

## 关键决策

### D1：纯客户端，零新端点
CLI 只调既有 API（`/api/chat/stream`、`/api/flows*`、`/api/flows/runs`、
`/api/autonomous/status`、`/api/usage`）。**不加任何服务端路由**——路由数不变，
`make verify` 的守卫不会因本变更误报（这是「入口 vs 能力」的边界自觉）。

### D2：urllib 而非 requests/httpx
仓库 API 侧已用 requests，但 CLI 是给开发者的轻工具：stdlib 实现让
`pip install zimeiti-cli` 零依赖，也让 CI 门禁（bandit/ruff）面最小。
SSE 用 `resp.readline()` 逐行读——与 Web 端同契约，无库可用恰好避免过度封装。

### D3：凭据留在服务端
CLI 的 chat 走服务端 API，**不读 OPENAI_API_KEY**。本地裸调模型是 Web/API
早已封死的路径（key 轮换、fallback、门禁都在服务端），CLI 复制一份只会漂移。

### D4：`flows run` 明示成本
立即执行真实消耗 token。子命令 help 里写明，且执行后回显 summary。
不设确认提示（开发者工具，多一次回车反而烦）——但 help/文档必须诚实。

### D5：退出码契约
0=成功；1=API 错误（含连接失败，附行动指引）；2=用法错误（argparse 默认）。
脚本里好判断，且与 CLI 惯例一致。

## 风险与对策

- **风险**：SSE 长连接中途断网 → 读超时（默认无超时）+ 服务端 30min TTL；
  CLI 给 `--timeout` 覆盖，断流时打印已收到的部分并提示重试
- **风险**：Windows GBK 终端炸在中文/emoji → 输出前 `sys.stdout.reconfigure`
  （UTF-8, errors=replace）——E2E 目检过的最小处理
- **风险**：与 `zimeiti-api` console script 命名混 → CLI 定名 `zimeiti`，
  帮助文本首行写明「zimeiti 命令行入口（连接已有后端）」

## Open Questions

无。
