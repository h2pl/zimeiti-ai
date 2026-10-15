# browser-e2e — 浏览器级双端对齐测试套件

真实 Chromium 模拟用户操作，同一套用户旅程分别在 **zimeiti(:8110)** 与 **Easel(:7860)** 上执行，断言结构级行为一致。LLM 在 OpenAI 兼容端点 mock（`mock_llm.py`，:18900），其余链路（前端→HTTP→SSE→deepagents→PG→渲染）全部真实。

## 运行

```bash
make e2e-browser                                        # 双端全量
cd apps/api && uv run python ../e2e/run.py --scenarios S3,S5   # 按场景
cd apps/api && uv run python ../e2e/run.py --target zimeiti    # 单端调试
```

前置：`apps/web/dist` 已构建（`cd apps/web && npm run build`）、本机 PG 可用、Easel 在 `e:/Projects/Easel`。

## 场景 ↔ 用户路径 ↔ API 覆盖

| 场景 | 用户路径 | API 路径簇 |
|---|---|---|
| s01 | 首次访问引导 | GET /api/status |
| s02 | 全页面导航（11 页） | 各页 GET |
| s03 | 选题新建/编辑/删除 | POST/PUT/DELETE /api/ideas |
| s04 | 选题→排期→日历 | POST/GET/DELETE /api/schedule |
| s05 | 对话流式+会话管理（mock LLM） | POST /api/chat/stream + 会话 CRUD |
| s06 | 内容库浏览+文件预览 | GET /api/outputs, /api/output/{path} |
| s07 | 画像创建向导（mock LLM）/删除 | GET/POST/DELETE /api/personas |
| s08 | 账号页 whoami | GET /api/accounts/*/whoami |
| s09 | 设置面板模型通道 | GET /api/env |
| s10 | 热点→做内容跳转（条件断言） | GET /api/trends |

无 UI 入口的路径（上传、HITL 问答、平台登录/发布、技能执行）由 API 级 parity（`apps/scripts/e2e_parity_check.py`，57 项）覆盖——运行结束时打印完整映射表。

## 结构

```
run.py          入口（--scenarios / --target）
runner.py       双端 spawn/就绪/teardown + fixture 预置清理
mock_llm.py     OpenAI 兼容流式 mock（确定性回复，MOCK: 前缀）
helpers.py      导航/弹层/网络同步/清扫原语
parity.py       结构级 diff（环境性差异 NOTE）
coverage_map.py 路径→场景映射
scenarios/      s01…s10（run(page, ctx, check) -> obs）
```

## 约定

- 场景只做**真实用户操作**；数据清理可走 API；场景开始清扫历次残留（幂等）
- 断言同步用 `expect_response`（等变更回包+列表回包），禁止固定 sleep 碰运气
- obs 只含结构级观测值；回复文本/数据条数等语义差异仅 NOTE
