# 验证报告：phase1-remove-openclaw

- 日期：2026-10-13；模式：full；基线：5e38f9d → 4bd53fc（h2pl/zimeiti-ai）；verify_mode=full
- 说明：本变更「实现先行、后补验收」；实现提交 ea7733a + 评审返修提交 4bd53fc

## 七项核查

| # | 检查 | 结果 | 证据 |
|---|---|---|---|
| 1 | 任务完成 | PASS | 10/10（T1-T10） |
| 2 | 文件与任务匹配 | PASS | app.py（-700 行级重构）、easel/agent_runtime.py、pyproject.toml、validate_skills.py、7+2 模块删除、skills 目录归位、前端 2 文件——与 T1-T10 一一对应 |
| 3 | 构建/导入 | PASS | compileall exit=0（Runtime 证据）；`import app` 64 路由（较 phase1 的 66 少 2，对应 local-agents 端点移除） |
| 4 | 相关测试 | PASS | skill 测试 38 passed/5 skipped；validate_skills OK；validate_skill_commands OK（15 条命令契约，修正后首个可用版本） |
| 5 | 安全 | PASS | 无密钥入库；会话删除路径穿越已防护（`..%5C..%5Cpyproject` 冒烟 → 200 {'deleted': False}，目标文件无损） |
| 6 | 独立集成评审 | PASS（两轮） | 首轮 1 CRITICAL + 3 IMPORTANT + 5 WARNING + 3 SUGGESTION，CRITICAL/IMPORTANT 全部返修（4bd53fc）；返修项逐一复验（见下） |
| 7 | 核心场景 | PASS | 见 delta spec 场景核对 |

## delta spec 场景核对（deepagents-runtime）

| 场景 | 结果 | 证据 |
|---|---|---|
| 流式对话走运行时 | PASS | app.py:1753-1768 无条件 `run_turn`；SSE 契约未动（前序变更实测帧序） |
| 非流式入口走运行时 | PASS | `/api/chat`、`/api/skill` → `ask`（app.py:1889/1906），画像增强 → `ask_sync`（app.py:2820）；与流式共享会话历史 |
| 兜底开关移除 | PASS | `runtime_enabled()` 已删除；验收脚本 AST 断言 `ZIMEITI_RUNTIME` 代码引用为零 |
| 模型配置保存与生效 | PASS | 面板仅写 .env 槽位（app.py:1192+）；`_build_model` 读 `OPENAI_MODEL` 兜底 `ZIMEITI_MODEL`（agent_runtime.py:116）；全仓无 openclaw.json 读写（AST 断言） |
| 会话删除 | PASS | `delete_session` 清落盘历史 + InMemorySaver checkpoint + 活跃中断（agent_runtime.py:71-97）；TestClient 冒烟 DELETE/STOP/穿越 key 全部正确 |

## 独立评审返修记录（一轮）

- **C1 会话删除删不到 deepagents 历史**：原实现只删 `apps/outputs/_sessions` 轮次文件；新增 `agent_runtime.delete_session` 统一清理 `apps/sessions` 历史 + checkpoint storage + `_LIVE_INTERRUPTS` + `_LOCKS`
- **I2 路径穿越（Windows）**：删除路径改经 `_session_file`/`_turn_file` 的文件名清洗；冒烟验证 `..%5C..%5Cpyproject` 无副作用
- **I3 `/api/chat/stop` 空转**：`_RUNNING_CHAT` 改为 sk→asyncio.Task 登记，stop 取消任务并经 supervisor `CancelledError` 分支正常落盘（status=stopped）+ 解锁 forward；`_STOPPED_CHAT` 死变量删除
- **I4 `langchain_openai` 未安装**（比评审判断更严重：惰性导入掩盖，真实对话路径必崩；前序验收只测了无 key 降级路径所以漏检）：显式声明 `langchain-openai>=0.2,<3`，uv sync 装得 1.7.1，`import langchain_openai` 通过
- **W5/W6/W9**：`runtime_enabled` 残留删除；`validate_skill_commands.py` 指向 `skills/builtin`（修正后 15 条命令契约校验通过）；误导性 openclaw 注释清理（app.py/pyproject/前端 4 处）

## 已接受偏差（WARNING/SUGGESTION 级，已记录）

1. **W7 HITL 中断轮的 user 消息不落盘**（重启后磁盘历史缺该轮提问，checkpoint 内有、但 checkpoint 不持久）——修复涉及 run_turn resume 落盘语义扩展，超出本变更「移除 openclaw」范围；记录为跟进项
2. **W8 `_LOCKS` 跨事件循环共享**——当前主 loop 与 ask_sync worker 线程的 key 空间不重叠（会话 key vs `enhance:<name>`），实际风险低；按 loop 隔离记录为跟进项
3. **S10 `run_turn.event_path` 形参未使用**、**S11 calendar_ops.py 残留 `skills/openclaw` 候选路径（best-effort 跳过，无害）**、**S12 httpx 注释已修、消费方保留（趋势取数出站请求）**——净化级，不阻断

## 结论

无 CRITICAL / 无未处理 IMPORTANT（偏差 1-3 为已记录跟进项）。Ready for archive。
