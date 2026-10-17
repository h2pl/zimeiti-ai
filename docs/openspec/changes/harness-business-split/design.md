---
comet_change: harness-business-split
role: technical-design
canonical_spec: openspec
status: final
---

# 设计：harness/business 分层

## 目标结构

```
apps/api/
  zimeiti_harness/            # agent harness——禁止 import 业务域
    __init__.py
    contract.py               # 注入点（见 D1）
    runtime/
      agent_runtime.py        # 改：_skills_catalog 走 contract；其余不动
      model_fallback.py  exec_tool.py  pricing.py  schemas.py   # 原样搬
      __init__.py             # 薄出口：ask_sync/chat_structured/build_system_prompt/set_main_loop
    memory/                   # store/tools/flush 原样搬
    usage.py                  # 原样搬
  zimeiti_api/                # 业务 + 组装
    chat_router.py            # ← runtime/chat.py（/api/chat/stream 路由）
    status_router.py          # ← runtime/status.py（/api/status 路由）
    usage_router.py           # 原地（import 改指向 harness）
    content/ automations/ platforms/ operations/ governance/ core/
    app.py                    # 组装层：唯一接线点
```

## 关键决策

### D1：contract.py 注入点（依赖倒置），不是回调地图散落各处

harness 需要的业务输入只有一类：**提示词装配期的目录数据**（技能清单）。
集中到一个 contract 模块：

```python
# zimeiti_harness/contract.py
_skills_provider: Callable[[], list] = lambda: []
def register_skills_provider(fn: Callable[[], list]) -> None: ...
def skills_catalog() -> list:  # 供 agent_runtime._skills_catalog 渲染
    try: return _skills_provider()
    except Exception: return []
```

app.py 启动时 `harness.contract.register_skills_provider(content.skills.get_skills)`。
画像前缀不进 contract——`chat.py` 归位为 `chat_router.py` 后**留在业务侧**，
它直接 import content 是合法的（业务→harness 单向，路由属于业务组装）。

### D2：chat.py/status.py 归位为路由而非搬进 harness

它们 95% 是 FastAPI 路由（SSE 流、请求模型、附件解析），只有最后一步调
harness 的 ask/harness 流式入口。路由属于业务组装层——搬到 `zimeiti_api/`
顶层（对齐既有 `usage_router.py` 命名惯例），harness 保持「无 HTTP」。

### D3：scheduler 走 setter 注入（对齐 personas 范式）

`automations/scheduler.py` 加 `set_ask_sync(fn)`；app.py lifespan 里
`automations.scheduler.set_ask_sync(harness_runtime.ask_sync)`。守卫规则：
scheduler 源码不得出现 agent 入口的 import。

### D4：core/ 定性为共享 infra，划在「完全分开」边界之外

paths/pg/settings/timeouts 无业务逻辑，harness 依赖它们如同依赖 stdlib。
把 core 抽成第三个包是概念洁癖，churn 巨大且收益为零——明确写入 Non-Goal。
守卫规则相应表述为：harness 禁止 import `zimeiti_api.{content,automations,
platforms,operations,governance,routers}`，`zimeiti_api.core` 白名单放行。

### D5：import 更新策略——一次到位，不留 shim

13 个文件直接改 import（`zimeiti_api.runtime` → `zimeiti_harness.runtime`），
**不留 re-export shim**——shim 会让分层守卫形同虚设。测试文件一并更新。

## 风险与对策

- **风险**：myopic 遗漏某个延迟 import → 分层守卫扫描的是源码文本，能抓到
  字符串级 import；`make check` + E2E 兜底运行时
- **风险**：pyproject/mypy/ruff/bandit/Makefile 检查范围漏配 harness → 各处
  scope 显式更新并在验证清单核对（mypy 报 0 文件即漏配信号）
- **风险**：循环 import（harness ← → api）→ contract 是 harness 的叶子模块，
  组装方向永远是 app.py → 两侧，无环

## Open Questions

无。
