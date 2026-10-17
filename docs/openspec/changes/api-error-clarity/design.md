---
comet_change: api-error-clarity
role: technical-design
canonical_spec: openspec
status: final
---

# 设计：API 错误可读性

## 高层方案

```
lib/api.ts request()
  const res = await fetch(...)
  if (!res.ok) { ...现有 detail 提取逻辑不变... }
  const ct = res.headers.get('content-type') || ''
  if (!ct.includes('application/json')) {
    throw new Error('服务返回了 HTML 而非 JSON——API 代理/后端未就绪，'
      + '或前后端版本不一致。请重启 make dev（或刷新页面后重试）。')
  }
  return res.json()
```

## 关键决策

### D1：校验 Content-Type 而非 try/catch res.json()
内容协商是「意图」层面的事实（后端永远回 JSON；回 HTML 一定是链路故障），
比 catch 解析异常更早、更准地定位问题类别。catch JSON.parse 只能给出
「解析失败」，无法区分「后端真坏了」还是「代理回了页面」。

### D2：错误信息给处置指引而非仅描述现象
这次事故里用户面对 `Unexpected token '<'` 完全无从下手。新文案直接告诉用户
两步：这是链路问题（不是你的操作问题）→ 重启 make dev。后端 JSON 404
（版本错位）则由现有 `!res.ok` 分支展示 `{detail}`，无需重复处理。

### D3：回归探针用 Playwright route 拦截，不引入前端测试框架
「后端返回 HTML」在真实链路里难以稳定复现（要人为弄坏 dev 代理），但
Playwright 可以精确注入这个场景：`route.fulfill(body: '<!doctype html>')`。
探针断言用量卡片渲染的是新文案且不含 `Unexpected token`。脚本放
`apps/scripts/probe_api_error.py`，与既有探针同范式，不进 make check
（前端无测试基建，这是本次明确的 Non-Goal）。

## 风险与对策

- **风险**：个别端点返回非标准 Content-Type 被误杀 → 已核查后端全部
  FastAPI JSONResponse 均带 application/json；SSE（chat/stream）不走 request()
- **风险**：FileResponse 类端点（如预览文件）也走 request()？→ 已核查：
  文件下载/预览由独立函数处理，不经 request()

## Open Questions

无。
