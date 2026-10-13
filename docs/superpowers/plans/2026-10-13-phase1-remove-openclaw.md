---
change: phase1-remove-openclaw
design-doc: docs/openspec/changes/phase1-remove-openclaw/design.md
base-ref: 5e38f9d0792be55275389c281cd15f9e0a7d0819
archived-with: 2026-10-13-phase1-remove-openclaw
---

# 实施计划：phase1-remove-openclaw

<!-- comet-task-authority: docs/openspec/changes/phase1-remove-openclaw/tasks.md -->

> 说明：本变更「实现先行、后补验收」——T1-T8 的实现在 Comet 变更建立前已于工作区完成（未提交），本计划记录任务-提交映射与验收口径；T9 为验证收口。

## T1 流式端点去兜底 <!-- comet-task-ref:ed09aee6-e4a2-4a7a-9eff-293481e54855 -->

- 范围：`apps/api/app.py` `/api/chat/stream` 删除 `runtime_enabled()` 分支与 openclaw 双路径体（约 475 行），无条件 `run_turn`。
- 验收：端点无 openclaw 分支；SSE 帧序 activity→token…→done 契约不变。

## T2 非流式入口切换 <!-- comet-task-ref:f135f17e-1b44-44b6-b12a-2f9d778a10f6 -->

- 范围：`/api/chat`、`/api/skill` → `_agent_runtime.ask`；画像 AI 增强 → `ask_sync`。
- 验收：三入口无 `run_agent_sync`/CLI 调用；与流式共享会话历史。

## T3 死代码清除 <!-- comet-task-ref:98ff9dca-b299-4c6d-b396-fda02a2697f4 -->

- 范围：传输层选择/钉扎、`_GatewayHttpProc`、`_CrossProcLock`、会话自愈、uuid5 transcript、问答题 gateway 桥接、`run_agent_sync`/`check_gateway`/`clean_agent_output`/`_scrub_secrets`、失效 import/常量。
- 验收：ruff 无 F821/F401/F811；符号引用搜索归零。

## T4 设置面板去 openclaw.json 化（后端） <!-- comet-task-ref:b9a0452b-c3a3-49c7-9dd6-2cf7c2918587 -->

- 范围：保存端点仅 `.env` 槽位；`_model_channels` 主通道由 `OPENAI_MODEL` 推导；local-agents 端点删除；`/api/session/{key}` 改删 deepagents 会话文件；status `gateway` → `model_configured()`。
- 验收：全仓无 `openclaw.json` 读写代码。

## T5 agent_runtime 对齐 <!-- comet-task-ref:dcbf9d55-9a77-4002-8eb1-cce590fef757 -->

- 范围：`_build_model` 读 `OPENAI_MODEL`（兜底 `ZIMEITI_MODEL`）；`AIMessageChunk` 顶层导入（修复 F821 NameError）。
- 验收：`import app` 成功，路由数 64。

## T6 模块与依赖 <!-- comet-task-ref:b848636a-c512-4a68-845a-059fcfa3dead -->

- 范围：删 `easel/` 7 模块 + `commands/` + `gateway.{sh,ps1}`；移除 `easel` CLI 入口、`websocket-client`/`cryptography`；声明 `deepagents`/`langchain-core`；`requires-python>=3.11`；`biliup==1.2.9`。
- 验收：`uv sync` 可重建环境；`import app` 成功。

## T7 技能目录归位 <!-- comet-task-ref:35501601-a4d2-4631-ab5e-f5ed573ab576 -->

- 范围：`skills/openclaw/*` → `skills/builtin/skill-wechat-publisher/*`；app.py 路径引用指向真实布局；`validate_skills.py` 修正。
- 验收：`validate_skills.py` OK；skill 测试通过。

## T8 前端对齐 <!-- comet-task-ref:daac4b57-d662-4e2f-902c-9e4c09347d22 -->

- 范围：`SettingsPanel.tsx` 移除 local-agents 区块/custom 供应商/chat 主备切换；`api.ts` 移除 `LocalAgent*`。
- 验收：`tsc -b` 零错误；`vite build` 成功。

## T9 验证收口 <!-- comet-task-ref:47b87a04-8e15-4915-afbd-1fb677a60104 -->

- 范围：compileall、`import app`、ruff F/E、openclaw 符号归零、`validate_skills.py`、skill 测试 38 项、tsc/vite build。
- 验收：全部证据通过并登记 Runtime；verify 独立集成评审 PASS。

## 回滚

单提交实现 + 单提交归档；回滚 = revert 两个提交（无 DB/配置迁移，无不可逆操作）。

## T10 独立评审返修 <!-- comet-task-ref:8b10ad78-e1bb-4275-93f8-02fb29033379 -->

- 范围：会话删除改经 `agent_runtime.delete_session`（历史文件 + InMemorySaver checkpoint + 活跃中断登记，CRITICAL-1）；`/api/chat/stop` 改取消后台任务并正常收尾（I-3）；声明 `langchain-openai`（I-4，实测未安装）；删除 `runtime_enabled` 残留（W-5）；`validate_skill_commands.py` 指向 `skills/builtin`（W-6）；误导性注释清理（W-9）。
- 验收：TestClient 冒烟 DELETE/STOP/穿越 key 全部正确；compileall + import OK；ruff 无 F/E；两个 validator OK；skill 测试 38 passed。
