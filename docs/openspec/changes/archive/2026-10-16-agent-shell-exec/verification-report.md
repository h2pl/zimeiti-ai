---
comet_change: agent-shell-exec
---

# 验证报告：agent-shell-exec（白名单命令执行器）

## Spec 场景逐条核对

| Requirement / Scenario | 结果 | 证据 |
|---|---|---|
| 白名单脚本执行 —— 执行注册脚本 | ✅ | 单测 `test_runs_registered_script`（exit/stdout/stderr 断言）；真脚本烟测 content_guard scan 净文本 exit 0 |
| 白名单脚本执行 —— 拒绝未注册脚本 | ✅ | 单测 `test_rejects_unregistered`；错误信息含白名单说明与可用清单 |
| 参数与路径安全 —— 路径注入被拒 | ✅ | 参数化单测 7 种载荷（`../`、绝对路径、`$()`、反引号、`|`、`&&`）全部拒绝；不产生进程 |
| 执行资源约束 —— 超时被终止 | ✅ | 单测 `test_timeout_terminates`（sleep 30 脚本 1s 超时终止，总耗时 <15s） |
| 输出上限 | ✅ | 单测 `test_output_truncated`（50KB stdout 截断至 <9KB 且 truncated 标记） |

## 自动化验证

- **单测**：`tests/test_exec_tool.py` 13 项 RED→GREEN
- **真脚本烟测**：content_guard scan（净文本/敏感文本）、ai_score（运营 case 3287 字成稿 → 🟢 PASS 真人味）
- **对话探针（真实 LLM）**：agent 实际调用 exec_script 执行 ai_score 质检并消费输出，给出字数/burstiness 结论与下一步选项（引用 content_guard 与 ops-create 规范）
- **`make check`**：全绿（exit 0，经 `comet check run` 登记）
- **浏览器 E2E S05**：4/4 通过、双端差异 0（工具接入无回归）

## 注册表首批（design D4 盘点结果）

| 脚本 | 位置 | 参数形态 |
|---|---|---|
| content_guard | skills/shared/scripts/ | 子命令 `scan/redact` + `--text/--file/--out` |
| ai_score | skills/builtin/skill-wechat-publisher/scripts/ | 位置参数 article + `--json/--threshold` |
| render_card | skills/shared/scripts/ | `--html/--out/--selector/--all/--full-page/--width/--height` |

需 TTY/凭据的脚本未注册（按设计）。

## 结论

白名单执行器达成安全边界下的能力补齐：agent 可跑质检/渲染脚本，白名单外一律拒绝。**建议通过。**
