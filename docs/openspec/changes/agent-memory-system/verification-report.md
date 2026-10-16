---
comet_change: agent-memory-system
---

# 验证报告：agent-memory-system（agent 记忆系统）

## Spec 场景逐条核对

| Requirement / Scenario | 结果 | 证据 |
|---|---|---|
| 记忆记录与溯源 —— 任务结束凝练 | ✅ | 探针会话1：用户陈述偏好 → agent 凝练记录并主动追问细化（色值/底色） |
| 记忆记录与溯源 —— 不记一次性内容 | ✅ | 工具 docstring 纪律 + record 白名单（origin 非法值单测拒绝） |
| 记忆检索与注入标注 —— 可溯源 | ✅ | 探针会话2：检索结果标注「记忆来源：你本人明确陈述，重要度 8」（工具层 [记忆:origin] 标注，agent 转述保留溯源语义） |
| 记忆检索与注入标注 —— 不重复注入 | ✅ | 单测 test_injection_dedup（同会话过滤/新会话可注入） |
| compaction 前 flush | ✅ | 单测 test_episodic_flush_writes（40 条消息触发，origin=system）；ask() 挂点实测无异常 |
| 与画像 memory.md 边界 —— 不互写 | ✅ | 契约段两条边界 + record 无画像路径写入能力（只写 PG 记忆表） |

## 自动化验证

- **单测**：`tests/test_memory.py` 6 项 RED→GREEN（记录/检索/溯源白名单/注入去重/flush/级联清理）
- **全量测试**：180 passed（含既有回归）
- **跨会话探针（真实 LLM）**：会话1 记录「封面克莱因蓝极简风」→ 全新会话2 检索命中并带溯源与适用范围说明
- **`make check`**：全绿（exit 0，经 comet check run 登记）
- **浏览器 E2E S05**：8/8 通过、双端差异 0

## 与 OpenClaw 的刻意差异（design 决策）

- 所有记录经用户确认，无后台静默写入（比 OpenClaw dreaming 自动固化保守，单用户场景确认成本低）
- flush 用确定性截断零 LLM 成本（OpenClaw compaction 前 flush 为同等思路）
- 溯源用 PG origin_class 列（等价 OpenClaw SQLite provenance 列的防注入设计）

## 结论

跨会话记忆达成：可复用经验可记录、可检索、带溯源、防重复注入，与画像边界分明。**建议通过。**
