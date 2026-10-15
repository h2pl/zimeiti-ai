# Brainstorm Summary

- Change: browser-e2e
- Date: 2026-10-14

## Confirmed Technical Approach

用户逐条确认（对话记录为准）：

1. **独立目录管理**：浏览器 E2E 从单文件迁入 `apps/e2e/`，按用户路径拆场景模块（10 个），旧 `apps/scripts/browser_e2e.py` 删除——用户明确「是的」。
2. **全链路真实 + LLM mock**：用户明确「每个场景都要真实测试，llm调用可以mock返回值」。mock 边界选在 OpenAI 兼容 HTTP 端点（本地 18900），zimeiti 后端以显式 `OPENAI_API_KEY/OPENAI_BASE_URL/ZIMEITI_MODEL` 注入；除模型推理外链路全真（前端→HTTP→SSE→deepagents→langchain-openai→mock→渲染）。
3. **双端对齐**：同一旅程在 zimeiti(:8110) 与 Easel(:7860) 跑，结构级观测值 diff 为验收判据（Easel 端 LLM 不受控，语义差异仅 NOTE）。
4. **网络同步**：单文件版三轮调试确认的竞态（弹层异步挂载/hover 渲染按钮/POST-GET 竞态）全部以 `expect_response` 同步根治，不靠固定 sleep。

## Key Tradeoffs and Risks

- Easel 端真实 LLM 慢（180s 上限）且不确定 → 只比结构级事实
- 热点数据来自外部站点 → 条件断言 + skip 记录
- 两端构建版本 UI 细微差异 → role/text 双重兜底点击

## Test Strategy

- 每场景 `run(page, ctx) -> obs`（结构级观测值）；套件 3 轮连续全绿 + 数据零残留为稳定性标准
- 覆盖映射表随输出打印：有 UI 入口的路径 → 场景；无 UI 入口 → 显式登记 API parity 覆盖

## Spec Patch

None（spec 已含全部验收场景）
