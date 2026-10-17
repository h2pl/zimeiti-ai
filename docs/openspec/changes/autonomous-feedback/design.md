---
comet_change: autonomous-feedback
role: technical-design
canonical_spec: openspec
status: final
---

# 设计：autonomous-feedback

## 高层方案

```
zimeiti_autonomous/feedback.py
  collect_published(days=14)  读 outputs/_analytics/<platform>/<date>.json → 事实列表
                              （源缺失/坏 JSON → 空列表；不虚构）
  build_calibration(items)    事实 → 校准信号文本：发过什么、密度、待补缺口
                              （无事实 → 如实「暂无发布记录」）
  context_for_discover()      汇总 + 归档 outputs/_feedback/<date>.md → 返回文本

flows.build_step_prompt(step, config, prev_summary, feedback="")
  仅当 step == discover 且 feedback 非空时追加校准段
runner.run_flow：discover 步执行前调 feedback.context_for_discover()（可关闭）
router：GET /api/feedback
```

## 关键决策

### D1：只读既有文件源，不新增表
`ops_analytics.py` 已经把发布事实落到文件（按 media_id 幂等）。再建一张 PG 表是
重复数据源、且要处理双写一致。校准是**读侧汇总**，读文件即可——与 xiaobei 的
`published-track`（SQLite）相比，这里的既有事实源已经存在，没必要另起炉灶。

### D2：校准信号只陈述事实与缺口，不做评分
不做「表现打分/推荐权重」——那需要真实表现数据（阅读数等），而项目既定决策是
先不拉。信号形态：`发过 N 条（平台分布）→ 最近一次 X 天前 → 建议补缺口 Y`。
诚实优先：没有表现数据就只说事实，不编造 CTR/阅读数。

### D3：注入只作用于 discover 步
闭环的意义是「上一轮影响下一轮的选题」。produce/publish 步注入校准段只会污染
上下文且有跑题风险；review 步自己就在产出结论。故仅 discover 注入（D3 与规格一致）。

### D4：feedback 可关闭（配置 `feedback: false`）
探针与单测需要确定性；部分流程（如纯复盘流程）不需要校准段。配置面留一个开关，
默认开。

### D5：归档到人可读的 Markdown
`outputs/_feedback/<date>.md`——既能被 agent 后续读取，也能被人直接打开看，
比 JSON 更契合「运营」场景。

## 风险与对策

- **风险**：analytics 文件结构演进（字段变化）→ 解析用 `.get` 容错，坏文件跳过并计数
- **风险**：时间窗内文件很多（大量发布）→ 汇总只取条数与最近若干条标题，截断上限
- **风险**：注入使 discover 步 prompt 变长 → 校准段限长（与摘要同量级），可关闭

## Open Questions

无。
