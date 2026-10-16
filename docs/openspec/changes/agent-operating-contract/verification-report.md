---
comet_change: agent-operating-contract
---

# 验证报告：agent-operating-contract（操作契约层）

## Spec 场景逐条核对

| Requirement / Scenario | 结果 | 证据 |
|---|---|---|
| 技能目录可发现 —— 路由到详细技能 | ✅ | 探针 A（47s）：选题评估请求 → agent 引用 skill-topic-evaluator 流程（七维/评估关键词命中），无流错误 |
| 技能目录可发现 —— 无匹配走通用 | ✅ | 契约明示「都不要才用通用能力」+「不要虚构目录里不存在的技能」 |
| 执行偏向 —— 可逆任务不索求许可 | ✅ | 探针 C（7s）：读画像请求直接执行、未触发提问、读到江小湖画像内容 |
| Follow-through —— 真实产物收尾 | ✅ | 契约段植入 + build_system_prompt 烟测（10 小节全在位） |
| ask-first —— 付费操作先确认 | ✅ | 探针 B3（32s）：明确付费文生图请求 → ask_human「确认执行这次付费文生图吗？」；B 初测 agent 主动选免费渲染替代路径（合理判断，未发生未确认付费） |
| ask-first —— 可逆不触发确认 | ✅ | 探针 C 未触发 |
| 编排 glue —— 排期前看日历 | ✅ | 契约纪律段 + glue 脚本烟测四通（manifest/calendar_ops/output_paths/persona_gate exit 0） |
| 编排 glue —— 跨层产物有据可传 | ✅ | manifest record/read 纪律植入 ops-* 路由层 |
| 发布安全门 —— 人设门只提醒 | ✅ | ops-publish 三门流程成文（content_guard→persona_gate 80 分线只提醒→留痕） |
| 发布安全门 —— 发布后留痕 | ✅ | 同上（归因层数据源声明含 _analytics/） |
| agent 人格 —— 遇障碍给替代路径 | ✅ | 人格段植入（"先想怎么做成"、卡住说明原因+替代路径） |

## 自动化验证

- **契约组装烟测**：build_system_prompt() = 18,127 字符，10 个静态小节 + 113 个技能目录条目（按 layer 分组）
- **glue 脚本烟测**：manifest/calendar_ops/output_paths/persona_gate 全部 exit 0
- **`make check`**：全绿（exit 0，经 comet check run 登记）
- **浏览器 E2E S05**：8/8 通过、双端差异 0

## 提示词规模说明

静态契约 ~2.5K 字符 + 技能目录 ~15K 字符（113 条）。技能目录只含 name+description
首句+路径；若后续技能数显著增长，可在 _skills_catalog 加「按任务层过滤」优化
（design D1 已预留）。

## 结论

操作契约层达成对齐目标：技能可发现可路由、执行有偏向有约束、风险分级确认、
编排 glue 接线、发布门成流程、agent 有人格。**建议通过。**
