---
comet_change: browser-e2e
role: technical-design
canonical_spec: openspec
---

# Design: browser-e2e

## Context

现状：`apps/scripts/browser_e2e.py` 单文件（~300 行），5 个粗场景，双端对齐比较已验证可行（18/18 通过）。已知的浏览器层脆性来源均已定位：欢迎弹层异步挂载、kanban 按钮 hover 渲染、保存 POST 与列表刷新 GET 竞态。LLM 调用走 `.env` 真实 key（`load_dotenv(override=False)` 意味着显式环境变量可覆盖）。Playwright + Chromium 已就绪，PG 本机可用。

## 高层结构

```
apps/e2e/
├── run.py            # 入口：解析参数（--scenarios s03,s05 / --target zimeiti）→ 双端循环 → 对齐报告
├── runner.py         # TargetManager：spawn/就绪等待/teardown；zimeiti 注入 mock LLM 环境
├── mock_llm.py       # OpenAI 兼容流式 mock（uvicorn 线程，端口 18900）
├── helpers.py        # click_nav / dismiss_onboarding / syncMutation / sweep / 轮询原语
├── parity.py         # compare()：结构级观测值 diff（S5 语义内容差异仅 NOTE）
├── coverage_map.py   # API 路径 → 场景映射表（运行末打印）
├── scenarios/
│   ├── base.py       # Scenario 协议：run(page, ctx) -> dict（结构级观测值）
│   ├── s01_onboarding.py … s10_trends_topics.py
└── README.md         # 使用说明 + 覆盖映射表
```

运行方式：`cd apps/api && uv run python ../e2e/run.py`（复用 api venv 的 playwright/fastapi）；`make e2e-browser` 封装。

## 关键决策

### 1. LLM mock 边界（用户拍板：全链路真实 + LLM mock）

zimeiti 后端以显式环境变量启动：`OPENAI_API_KEY=sk-e2e-mock`、`OPENAI_BASE_URL=http://127.0.0.1:18900/v1`、`ZIMEITI_MODEL=mock-model`。`load_dotenv(override=False)` 保证显式变量优先于 `.env`。mock 端点实现 `/v1/chat/completions` 流式 SSE（`data: {"choices":[{"delta":{"content":...}}]}` + `[DONE]`），按消息内容返回确定性回复（含 `MOCK:` 前缀）。链路真实性：前端→HTTP→SSE→deepagents agent→langchain-openai 客户端→mock 端点→回程渲染，除「真模型推理」外全部真实。画像向导的 LLM 增强同样经此边界确定性化。

Easel 端保持自身配置（其网关读 Easel/.env，不受控）——S5 类场景对 Easel 侧只比较「气泡出现」等结构级事实，回复内容差异记 NOTE 不判失败。

### 2. 场景契约与双端对齐

每个场景 `run(page, ctx) -> obs`，obs 只含**结构级可比较观测值**（布尔、可达页面列表、错误计数）；语义内容（回复文本、数据条数）不入 obs。同一场景在两端执行，`parity.compare()` 逐键 diff：结构级必须一致，环境性差异显式 NOTE。

### 3. 网络同步取代固定 sleep

单文件版三轮调试确认的竞态全部以 `expect_response` 同步根治：写操作等其变更请求回包 + 后续列表 GET 回包再断言。导航后等列表 GET。弹层异步挂载用轮询等待。kanban 操作按钮 `display:none`→`:hover` 渲染，用 hover 后普通点击（force 对无布局盒元素无效）。

### 4. 数据自清理与幂等

场景内创建的数据（选题/排期/画像/会话/输出 fixture）场景结束前删除；场景开始时按标题清扫历次残留。输出 fixture 由 runner 在 spawn 前直接写入两端数据目录（`outputs/e2e-fixture/note.md`），teardown 删除。

### 5. 环境与确定性

- 外部依赖数据（热点雷达抓微博/抖音）：页面渲染必断言，条目存在性为条件断言（无条目时记录 skip 理由，「做内容」跳转仅在有条目时执行）
- Windows：zimeiti spawn 前设 `WindowsSelectorEventLoopPolicy`（psycopg 异步要求，`python -m zimeiti_api` 已内置）；teardown 强杀 + 端口核对
- 端口：zimeiti 8110（避开用户 8000）、mock LLM 18900、Easel 7860（其默认）

## 风险与对策

| 风险 | 对策 |
|---|---|
| Easel 端真实 LLM 慢/失败 | S5 对 Easel 上限 180s，失败仅影响该端该场景，diff 报告明确归属 |
| 热点无数据 | 条件断言 + skip 记录 |
| 两端构建版本 UI 差异 | click_nav role→text 双重兜底（已在单文件版验证） |
| 场景间数据串扰 | 每场景独立清扫；会话类操作用独立会话名 |
