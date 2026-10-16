---
change: agent-shell-exec
design-doc: docs/openspec/changes/agent-shell-exec/design.md
base-ref: e9ae031
archived-with: 2026-10-16-agent-shell-exec
---

# Plan：agent-shell-exec 白名单命令执行器

<!-- comet-task-authority: docs/openspec/changes/agent-shell-exec/tasks.md -->

## G1 ExecTool 核心（TDD） <!-- comet-task-ref:f8b702a8-5a91-49a3-b797-89d58d4dccb4 -->

`zimeiti_api/runtime/exec_tool.py`：`exec_script(name, args_json)` LangChain 工具。
- 注册表 SCRIPT_REGISTRY：name → (相对路径, 参数 schema, 说明)，静态登记
- 校验链：注册表查名 → args 逐个 key 在 schema → value 拒 `..`/绝对路径/`$ \` \` | ; &`
- 执行：subprocess.run([sys.executable, 脚本绝对路径, *args], cwd=PROJECT_ROOT,
  timeout=120, env 强制 PYTHONUTF8=1, capture_output) → 尾部 8KB/2KB 截断
单测 RED→GREEN：合法执行、未注册拒绝、路径注入拒绝、超时终止、输出截断。

## G2 注册表盘点与接入 <!-- comet-task-ref:5fd7a73e-f72b-4b4d-adbb-4f5141718022 --><!-- comet-task-ref:b945ce78-80e4-4795-876a-3abb4af78aba -->

扫 skills/shared/scripts/ 可独立运行无交互的脚本，登记 ai_score.py / render_card.py
等（逐个确认参数形态）；SYSTEM_PROMPT 补「可用脚本经 exec_script 调用，先读对应 SKILL.md」。

## G3 SKILL 标注 <!-- comet-task-ref:20e39965-d16c-4554-b835-50ad6b04feb1 -->

质检/卡片渲染相关 SKILL.md 标注可用脚本名、参数与调用示例。

## G4 验证 <!-- comet-task-ref:04fa3b9c-c07c-45ab-a12a-afa3b18d5124 --><!-- comet-task-ref:a72e68dc-0a09-47b9-9e90-01aa7e2be998 --><!-- comet-task-ref:fcd4e944-21a5-4f04-9740-c84ee169f7c0 -->

make check 全绿；对话探针：agent 实际调用 exec_script 跑通一次质检脚本并消费输出；
spec 三 Requirement 场景逐条核对。
