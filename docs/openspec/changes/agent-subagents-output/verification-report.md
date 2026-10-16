---
comet_change: agent-subagents-output
---

# 验证报告：agent-subagents-output（专属子代理与结构化输出）

## Spec 场景逐条核对

| Requirement / Scenario | 结果 | 证据 |
|---|---|---|
| 探索类子任务用只读子代理 | ✅ | 探针：agent 实调 `task` 派出 research 扫内容库，回报稿件目录清单与命名不一致问题（工具轨迹 `🔧 task…`） |
| 子代理不得越权 | ✅ | 确定性断言：子代理工具面不含 ask_human / exec_script / memory_*；research 权限为 deny `/**`、无任何 allow；draft 的 allow 全部限定 `outputs/` |
| 可关闭 | ✅ | `ZIMEITI_SUBAGENT_ENABLED=false` → `_build_subagents()` 返回空表 |
| 结构化产出按 schema | ✅ | 探针：3s 返回完整 `TopicEvaluation`（六维评分 + 综合 76 + 结论「改角度后做」+ 4 条建议），字段类型全部合规 |
| 不影响普通对话 | ✅ | 确定性断言：主 agent 源码不出现 `response_format=`（图级配置不污染普通对话） |

## 自动化验证

- **`make check`**：全绿（exit 0）——219 passed
- **`make evals`**：5/5 通过（行为层，真实 LLM）
- **子代理单测**：9 项通过（角色边界 / 权限 / 模型降档 / 开关 / schema / 结构化注册校验）
- **结构化图缓存**：进程内按 schema 名复用（实测第二次调用命中缓存）

## 实现过程中修正的设计（与 design.md 差异，已实测）

1. **「不传 model」不可行**：deepagents 校验要求 spec 必须含 `model`，
   否则 `ValueError: SubAgent must specify model`。改为必传（缺省=主模型）。
2. **「传 tools 白名单字符串」不可行**：`tools` 必须是工具对象，传字符串导致
   ToolNode 构建报 `Tool object must not be None`。改为不传 tools（继承文件工具）
   + 用 `FilesystemPermission` 收死写权限——职责分离更干净。
3. **工具集需共用**：`_build_tools` 原为 `_build_agent` 内嵌（ask_human 绑定会话），
   结构化图无法复用 → 抽出 `_build_base_tools()`（exec + memory）供两图共用。

## 结论

子代理有角色边界与成本分层入口，结构化产出有 schema 约束且不影响普通对话。**建议通过。**
