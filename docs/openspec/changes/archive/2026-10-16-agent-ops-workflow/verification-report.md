---
comet_change: agent-ops-workflow
---

# 验证报告：agent-ops-workflow（五层运营流程技能化）

## 验证环境

- 真实后端（`zimeiti_api`，测试实例 127.0.0.1:8119）+ 真实 LLM（.env 通道）+ 真实文件系统挂载
- 数据：江小湖画像（profiles/）、119+5 个内置技能、运营 case 历史选题

## Spec 场景逐条核对

| Requirement / Scenario | 结果 | 证据 |
|---|---|---|
| 五层技能可被发现并按层执行 —— 「围绕某热点做一期内容」 | ✅ | 对话探针 1（122s）：回复引用 ops skill（discover/plan/create），无流错误；E2E S05 4/4 无回归 |
| 五层技能可被发现并按层执行 —— 复盘请求走归因层 | ✅ | 对话探针 2（43s）：agent 按 ops-review 数据源清单读 outputs/_analytics/，输出结构化复盘 |
| 每层 skill 声明数据源与产物约定 | ✅ | 五个 SKILL.md 均含「数据源/产物约定/交接条件」节（代码审查） |
| 归因层有数据给复盘 / 无数据如实报告 | ✅ | 探针 2：明确「无发布记录」并说明缺什么数据（未编造读数），另给三条策略建议 |
| 系统提示词只承载索引 | ✅ | SYSTEM_PROMPT 五层各一句话+触发词；流程细节全部在 SKILL.md（diff 审查） |
| 流程修改不需要改代码 | ✅ | 设计结构验证：SKILL.md 为纯文档，agent 每次对话读盘 |

## 自动化验证

- **单测**：`tests/test_ops_analytics.py` 5 项 RED→GREEN（写/幂等/空目录/路径穿越/默认目录锚点）
- **`make check`**：全绿（exit 0，经 `comet check run` 登记，15min 超时，log 见 `.comet/checks/`）
- **浏览器 E2E S05**（对话全链路+会话管理）：4/4 通过、双端差异 0
- **技能收录**：`get_skills` 返回 ops-discover/plan/create/publish/review 五个技能（layer 分别 discover/plan/produce/publish/attribute）

## 遗留事项（不阻塞验收）

- 归因层当前只落「发布事实」（media_id/路径/状态）；平台阅读/互动数据接入属后续变更范围（design D2 已声明）
- 探针 1 回复首段为英文操作叙述（token 流中 agent 的工具使用旁白）——内容交付正常，纯观感问题，记录备查

## 结论

五层流程技能化达成设计目标：流程知识结构化、agent 按层执行、归因数据源真实可读、无数据诚实报告。**建议通过。**
