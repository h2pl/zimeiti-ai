# 任务清单：phase1-remove-openclaw

> 实现说明：本变更的实现在 Comet 变更建立前已完成于工作区（后补验收）；任务勾选以「实现完成 + 对应证据通过」为准。

- [x] T1 流式端点去兜底：删除 `/api/chat/stream` 的 `runtime_enabled()` 分支与 openclaw 双路径体，无条件走 `run_turn` <!-- comet-task:ed09aee6-e4a2-4a7a-9eff-293481e54855 -->
- [x] T2 非流式入口切换 deepagents：`/api/chat`、`/api/skill` → `ask`；画像 AI 增强 → `ask_sync` <!-- comet-task:f135f17e-1b44-44b6-b12a-2f9d778a10f6 -->
- [x] T3 死代码清除：传输层选择/钉扎、`_GatewayHttpProc`、`_CrossProcLock`、会话自愈、uuid5 transcript、问答题 gateway 桥接、`run_agent_sync`/`check_gateway`/`clean_agent_output`/`_scrub_secrets`、失效 import 与常量 <!-- comet-task:98ff9dca-b299-4c6d-b396-fda02a2697f4 -->
- [x] T4 设置面板去 openclaw.json 化（后端）：保存端点重写为仅 `.env` 槽位；`_model_channels` 主通道由 `OPENAI_MODEL` 推导；删除 local-agents 端点与全部 openclaw.json 读写函数；`/api/session/{key}` 改删 deepagents 会话文件；status `gateway` 字段改报 `model_configured()` <!-- comet-task:b9a0452b-c3a3-49c7-9dd6-2cf7c2918587 -->
- [x] T5 agent_runtime 对齐：`_build_model` 读 `OPENAI_MODEL`（兜底 `ZIMEITI_MODEL`）；补 `AIMessageChunk` 顶层导入 <!-- comet-task:dcbf9d55-9a77-4002-8eb1-cce590fef757 -->
- [x] T6 模块与依赖：删除 `easel/` 下 7 个 openclaw 模块 + `commands/`、`gateway.{sh,ps1}`；移除 `easel` CLI 入口与 `websocket-client`/`cryptography`；声明 `deepagents`/`langchain-core`；`requires-python>=3.11`；`biliup==1.2.9` <!-- comet-task:b848636a-c512-4a68-845a-059fcfa3dead -->
- [x] T7 技能目录归位：`skills/openclaw/*` → `skills/builtin/skill-wechat-publisher/*`；app.py 路径引用指向真实布局；`validate_skills.py` 修正指向并移除未随迁技能契约条目 <!-- comet-task:35501601-a4d2-4631-ab5e-f5ed573ab576 -->
- [x] T8 前端对齐：`SettingsPanel.tsx` 移除 local-agents 区块/custom 供应商/chat 主备切换；`api.ts` 移除 `LocalAgent*` <!-- comet-task:daac4b57-d662-4e2f-902c-9e4c09347d22 -->
- [x] T9 验证：compileall、`import app`（64 路由）、ruff 无 F/E 类错误、`validate_skills.py` OK、skill 测试 38 passed、openclaw 符号引用归零、tsc + vite build 通过 <!-- comet-task:47b87a04-8e15-4915-afbd-1fb677a60104 -->
- [x] T10 独立评审返修：会话删除改删 deepagents 历史+checkpoint（CRITICAL-1）、stop 端点改取消后台任务（I-3）、声明 langchain-openai（I-4，实为未安装）、删除 `runtime_enabled` 残留（W-5）、`validate_skill_commands.py` 路径修正（W-6）、误导性注释清理（W-9） <!-- comet-task:8b10ad78-e1bb-4275-93f8-02fb29033379 -->
