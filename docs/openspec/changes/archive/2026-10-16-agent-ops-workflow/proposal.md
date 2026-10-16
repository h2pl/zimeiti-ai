---
comet_change: agent-ops-workflow
---

# agent-ops-workflow：五层运营流程技能化

## Why

OpenClaw→deepagents 迁移后，harness 层已对齐（文件工具/权限/PG 持久化），但 OpenClaw 时代的**五层运营流程知识**（发现/策划/制作/发布/归因）没有随之建模——agent 只有江小湖画像和通用提示词，做事靠即兴。实证：验证跑中 agent 自己报告「归因层没有数据支撑」「ai_score.py 没能跑」；同一选题两次生成走完全不同的路径。运营方法论散落在 multi-agent-manager 知识库与历史对话里，没有成为 agent 可按需读取的**结构化流程**。

## What Changes

- 新增五个内置 skills（`apps/skills/builtin/`）：`ops-discover`（发现=热点雷达选题）、`ops-plan`（策划=赛道评估/角度选择）、`ops-create`（制作=写作规范+质检清单）、`ops-publish`（发布=公众号草稿链路）、`ops-review`（归因=数据复盘）
- 每个 SKILL.md 定义：触发条件、执行步骤、数据源（系统 API/文件）、产物约定（落 outputs/）
- `agent_runtime.SYSTEM_PROMPT` 收敛为**索引 + 触发规则**：只声明五层存在与何时读哪个 skill，流程细节全部下沉到 SKILL.md（改流程不改代码）
- 归因层数据源接线：agent 可经文件系统读取 `_analytics/`（账号表现数据缓存），无数据时如实报告
- 用户问「做一期内容/发一篇/复盘」类请求时，agent 按 skill 流程执行并引用所在层

## Capabilities

### New Capabilities

- `agent-ops-workflow`：五层运营流程技能——agent 按发现/策划/制作/发布/归因五层执行运营任务，流程知识在 skills 中结构化沉淀

## Non-Goals

- 命令执行能力（agent-shell-exec，batch ②——质检/渲染脚本自动执行在那边做）
- 前端 OpenClaw 兼容债清理（frontend-openclaw-debt，batch ③）
- 多画像差异化流程（所有画像共用同一套五层流程）
- 发布动作自动化（发布层仍只产出草稿材料，不自动群发）
