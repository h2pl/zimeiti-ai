---
comet_change: agent-behavior-evals
role: technical-design
canonical_spec: openspec
status: final
---

# 设计：agent 行为回归套件

## 高层方案

```
apps/api/tests/evals/
  ├─ conftest.py        端口/实例管理（起独立 8121 实例，用例级清理）
  ├─ test_deterministic.py   ← 进 make check（无 LLM，秒级）
  │     契约段在位 / 技能目录含详细技能 / 白名单拒绝 / fallback 判定矩阵
  └─ test_behavior.py        ← 仅 make evals（真实 LLM，分钟级）
        5 条用例：路由 / 付费确认 / 可逆直做 / 跨会话记忆 / fallback 切换

Makefile: evals 目标（uv run pytest tests/evals -m behavior）
标记：@pytest.mark.behavior；make check 跑 tests/ 但用 -m "not behavior" 排除
```

## 关键决策

### D1：两层分离，行为层不进 make check
行为层要真实 LLM（每条 10-60s，五条数分钟，且花钱）。塞进 `make check` 会让本地门禁不可用。故：
- 确定性层（`tests/evals/test_deterministic.py`）：随 `make check` 跑
- 行为层（`tests/evals/test_behavior.py`，标 `behavior`）：`make evals` 触发；pytest 默认收集时用 `-m "not behavior"` 排除（写进 Makefile check 目标与 pytest 配置）

### D2：断言用双证据，不用字面量
手工探针时代我判「提到 topic-evaluator 就算命中」——太脆。改为：
- **工具轨迹证据**：从 SSE 的 `activity` 事件与最终消息里提取工具调用名（如 read_file / exec_script / memory_search / ask_human）
- **语义证据**：回复关键词命中（多条同义表述任一即可）
两条都有才算通过；只有一条 → 报「证据不足」并打印原文片段供人工复核。

### D3：行为层自带实例与清理，不依赖外部服务
每个 session 起独立端口（8121），用例结束删会话/清记忆条目/清 automation 与 usage 记录。用例失败也要清理（`finally`）。

### D4：fallback 用例的环境构造
主模型指向 `http://127.0.0.1:<空闲端口>/v1`（必连不上），备用写 `deepseek-chat@https://api.deepseek.com`——复用 `.env` 的真实 key。断言：① 服务日志出现切换记录；② 回复非空且不含「未配置模型」。

### D5：超时与费用护栏
行为层单条上限 300s；套件总耗时上限 ~10min。付费确认用例**只要求触发 ask_human**，不实际执行付费调用（避免真花钱）。

## 风险与对策

- **风险**：真实 LLM 输出不稳定导致偶发失败 → 对策：双证据降低脆弱性；失败时打印完整回复尾部 500 字；不重试掩盖问题
- **风险**：行为层污染真实数据（记忆/内容库）→ 对策：D3 清理 + 用例用独立 sessionKey 前缀 `eval-`
- **风险**：确定性层断言过严阻碍正常改动 → 契约段断言只查小节标题存在，不查措辞

## Open Questions

无。
