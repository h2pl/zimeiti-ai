---
comet_change: frontend-openclaw-debt
---

# 验证报告：frontend-openclaw-debt（前端 OpenClaw 语义残留清理）

## Spec 场景逐条核对

| Requirement / Scenario | 结果 | 证据 |
|---|---|---|
| 流式渲染契约 —— 长回复流畅渲染 | ✅ | 打字机队列机制保留（渲染节流），注释改为现行语义；S05 流式断言 4/4 |
| 流式渲染契约 —— 不依赖上游攒批假设 | ✅ | 注释重写为「渲染节流手段，不假设上游攒批节奏」；机制行为不变（缓冲+pump） |
| 重试语义 —— 范围与理由一致 | ✅ | G1 探针实测（chat/stream 请求体仅 message/persona/sessionId/turnId/attachments，无历史无截断参数；后端从 PG checkpoint 重放）→ 重试限最后一轮，代码注释以现行后端事实说明；spec 场景同步对齐 |
| HITL 卡片直连 | ✅ | QuestionCards 注释改现行语义（SSE question 事件 → POST /api/chat/question/answer）；代码本就直连无桥接层，残留仅在注释 |
| 无过时运行时假设 | ✅ | `apps/web/src` 全域 grep OpenClaw 残留清零（App.tsx/ChatPage.tsx/QuestionCards.tsx/index.css 五处） |

## 自动化验证

- **tsc --noEmit**：通过
- **`make check`**：全绿（exit 0，经 `comet check run` 登记）
- **浏览器 E2E S05**（对话全链路+会话管理）：4/4 通过、双端差异 0

## 说明（行为未变，属文档/语义债清理）

本变更不改变前端行为：打字机队列、重试限制、HITL 应答链路的行为均保持原样
（经探针核实它们本身就是对的或有现实约束），清理的是**误导性注释与过时语义框架**。
G1 探针发现的重试后端约束（无服务端截断）已如实写入代码注释与 spec；待后端支持
服务端截断后可另立变更放开限制。

## 结论

前端对话链路不再背负已退役运行时的语义假设，读代码的人看到的就是现行事实。**建议通过。**
