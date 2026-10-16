---
comet_change: agent-behavior-evals
---

# 验证报告：agent-behavior-evals（agent 行为回归套件）

## Spec 场景逐条核对

| Requirement / Scenario | 结果 | 证据 |
|---|---|---|
| 确定性断言随门禁 —— 契约段缺失即失败 | ✅ | 参数化断言覆盖 10 个契约小节；改提示词即报红 |
| 确定性断言随门禁 —— 技能目录不含详细技能即失败 | ✅ | skill-topic-evaluator / skill-quality-gate / skill-wechat-publisher 在册 + 路由链纪律 + layer 分组 + 40K 规模护栏 |
| 行为层可一键复跑 —— 五条用例 | ✅ | `make evals` → **5 passed**（112s） |
| 行为层可一键复跑 —— 无密钥 SKIP | ✅ | fixture 在缺 OPENAI_API_KEY 时 `pytest.skip`（退出码 0） |
| 断言基于证据 —— 付费门判据 | ✅ | 双证据（工具轨迹/语义命中）+ 不变量（确认前不发起付费调用） |

## 自动化验证

- **`make check`**：全绿（exit 0）——209 passed、5 deselected（行为层被正确排除）
- **`make evals`**：5/5 通过（约 2 分钟）

## 套件实测发现的问题（都已在本次处理）

1. **语言硬约束曾被违反**：探针中 agent 输出整段英文（"I'll start by reading…"）。
   → 已加「中文主导」断言固守（中文字符占比阈值），行为层用例③覆盖。
2. **付费门判据写错了对象**：首版写死「必须触发 ask_human」，实测 agent 有时用正文
   给出更完整的费用说明（并明确「没有单价数据就不编金额」）且并未发起调用。
   → 契约改为不变量「确认前不发起付费调用」，载体不限；已同步进 spec。
3. **技能 TTL 缓存跨用例污染**：`build_system_prompt()` 预热 `get_skills` 的 300s 缓存，
   导致后续用 tmp 假目录测 `/api/skills` 的用例读到真实技能而失败
   （`test_get_skills_route` 实测踩到，可复现）。→ 确定性层加缓存清理 fixture。
4. **pytest.ini 覆盖 pyproject 配置**：新增 ini 会因优先级更高而丢掉
   `addopts = --import-mode=importlib`。→ 标记改为注册在 pyproject 的 ini_options。

## 已知边界

真实 LLM 行为探针具有概率性：同一用例不同轮次可能给出不同表述（付费门首轮曾未命中
待确认关键词）。套件采取「双证据 + 失败时打印原文尾部 400 字」的策略，失败时先人工复核
是判据过严还是行为退化，而不是直接放宽断言。

## 结论

agent 行为首次具备可重复回归能力：确定性层守行为前提（门禁级），行为层守真实行为
（一键复跑）。**建议通过。**
