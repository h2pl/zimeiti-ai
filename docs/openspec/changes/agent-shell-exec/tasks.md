---
comet_change: agent-shell-exec
---

# Tasks：白名单命令执行器

## 1. ExecTool 实现（apps/api）

- [ ] 1.1 `zimeiti_api/runtime/exec_tool.py`：注册表（脚本名→路径/参数 schema/说明）+ 参数校验（`..`/绝对路径/`$ \` \` | ; &` 拒绝）+ subprocess 执行（cwd=数据根、timeout 120s、PYTHONUTF8=1、输出截断尾部 8KB/2KB）
- [ ] 1.2 首批注册表盘点：扫 `skills/shared/scripts/` 可独立运行无交互的脚本，登记 ai_score.py / render_card.py 等（附各自参数 schema）；需 TTY/凭据或写敏感区的不注册
- [ ] 1.3 接入 `_build_agent`（tools 注册）+ SYSTEM_PROMPT 提及「可用脚本经 exec_script 调用，先读对应 SKILL.md」

## 2. SKILL 标注

- [ ] 2.1 相关 SKILL.md（质检/卡片渲染所在技能）标注可用脚本名、参数与调用示例

## 3. 验证

- [ ] 3.1 单元测试：合法调用成功、未注册拒绝、路径注入拒绝、超时终止
- [ ] 3.2 对话探针：agent 实际调用 exec_script 跑通一次质检脚本并消费输出
- [ ] 3.3 `make check` 全绿
