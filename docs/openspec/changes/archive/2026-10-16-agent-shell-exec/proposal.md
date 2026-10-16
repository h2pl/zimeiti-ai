---
comet_change: agent-shell-exec
---

# agent-shell-exec：白名单命令执行器

## Why

deepagents 迁移后 agent 无法执行任何命令（实证：agent 在交付里报告「ai_score.py/content_guard.py/render_card.py 没能跑，卡片 PNG 未生成」）。质检脚本、卡片渲染等已沉淀在 `skills/shared/scripts/` 的能力，agent 只能望脚本兴叹，把命令列在发布备注里让人手动跑——自动化断在最后一公里。

安全约束（用户已拍板）：**不做任意 shell**。只允许执行注册脚本，agent 跑不了白名单外的任何东西。

## What Changes

- 新增 `ExecTool`（apps/api，注册进 `_build_agent` 的 tools）：内置**脚本注册表**（脚本名 → `skills/shared/scripts/` 相对路径 + 参数 schema + 说明），agent 按名调用
- 参数白名单校验：`--flag value` 形式，未知参数/路径注入（`..`、绝对路径、`$`/反引号）直接拒绝
- 执行约束：subprocess 超时（默认 120s）、输出截断（尾部 8KB）、cwd 固定数据根、UTF-8 强制解码
- 注册表首批：`ai_score.py`（文章质检）、`render_card.py`（分享卡片渲染）等既有脚本
- 相关 SKILL.md 标注可用脚本与调用方式

## Capabilities

### New Capabilities

- `agent-shell-exec`：白名单脚本执行——agent 经 ExecTool 运行注册脚本完成质检/渲染等收尾工作，白名单外一律拒绝

## Non-Goals

- 任意 shell 命令、Docker/远程沙箱、交互式命令、后台任务
- 脚本注册表的动态发现（首批静态注册，后续按需扩）
