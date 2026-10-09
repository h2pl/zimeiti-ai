# Why

content-strategy-calibration（已归档）产出的校准报告只有证据与留位，「Agent 洞察」无人填写；且校准仅手动触发。对标 Easel `skill-publish-analytics` 后发现其「关键发现」由**确定性脚本**按数据排名生成（Top 3 可执行洞察 + 方法论 + 局限性声明），模型完全不在链路里——比引入 LLM 更简单、可单测、零成本。本变更补齐：关键发现生成、方法论/局限性章节、按量触发（--auto）与定时入口。

# What Changes

- `ops_calibration.py` 新增：关键发现生成（确定性排名：最佳生命周期类型/发布日/基线异常指标）、方法论与局限性章节、`--auto` 按量触发（自上次校准以来新快照 ≥5 才执行，否则输出跳过原因）
- 评估报告新增「关键发现」「方法论」「局限性」三章节
- 不引入模型依赖；Agent 洞察章保留留位（托管循环的 Agent 填写）

# Capabilities

## Modified Capabilities

- `content-calibration`：校准报告 MUST 含确定性「关键发现」（Top 3 可执行洞察）、方法论与局限性章节；MUST 支持按量触发（自上次校准以来新快照 ≥5）

## Added Capabilities

（无）

# Impact

- `apps/api/src/zimeiti_api/ops_calibration.py`（扩展）
- `apps/api/tests/test_ops_calibration.py`（新增用例）
