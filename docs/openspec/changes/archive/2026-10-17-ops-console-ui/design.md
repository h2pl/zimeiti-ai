---
comet_change: ops-console-ui
role: technical-design
canonical_spec: openspec
archived-with: 2026-10-17-ops-console-ui
status: final
---

# 设计：运营控制台（定时任务 + 用量统计）

## 高层方案

```
Sidebar NAV += { page: 'automations', Icon: IconAutomations, label: '自动化' }
App.tsx      renderPage: case 'automations' → <AutomationsPage />
components/AutomationsPage.tsx  ← 新建（列表/新建表单/开关/立即执行/删除/执行记录）
components/UsageCard.tsx        ← 汇总卡片（工作台 + 设置面板复用）
lib/api.ts   += listAutomations/createAutomation/updateAutomation/deleteAutomation/
                runAutomationNow/listAutomationRuns/getUsage
```

## 关键决策

### D1：复用既有页面范式，不引入新依赖
现有页面（IdeasPage/OutputsPage）用 `fetch` + `useState/useEffect` 直连 `/api/*`，
无 react-query 等。新页面沿用同款写法（含 loading/error/empty 三态），与代码库一致。

### D2：「立即执行」不等待完成
后端 `run-now` 已是后台任务（立即返回 `{ok, started}`）。UI 点击后**提示已提交**，
并在 2 秒后刷新执行记录——不轮询阻塞、不假装同步完成（case 任务要跑几分钟）。

### D3：用量只展示 token，不折算金额
无单价数据源；界面标注「仅统计 token，未折算费用」，避免和契约里
「没有单价数据就说明将调用的次数与规格，不要编造金额」相冲突。

### D4：环境变量类配置**只读展示**
fallback 链 / 子代理模型是进程环境变量，改 UI 不会生效（除非重启且来源一致）。
设置面板只展示当前取值与修改方式说明——展示「假的可编辑控件」比不做更糟。

### D5：时刻输入用 HTML time input + 后端校验兜底
前端 `<input type="time">` 天然限制 HH:MM；后端仍校验（25:99 拒绝）——
两端校验不互相替代（后端是权威）。

## 风险与对策

- **风险**：自动化页在后端不可达时白屏 → 三态处理 + try/catch
- **风险**：用量表为空时展示怪异 → 明确空态文案「暂无用量数据」
- **风险**：新增导航项挤占侧栏 → 侧栏现有 6 项，加 1 项仍在可读范围

## Open Questions

无。
