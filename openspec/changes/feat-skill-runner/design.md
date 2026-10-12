---
comet_change: feat-skill-runner
role: technical-design
canonical_spec: openspec
---

# 设计：feat-skill-runner

## 决策记录

- **D1 标记格式升级**：`ops-trigger.json` 值从 `true` 改为
  `{"job": "hosted_content", "params": {"account": "xhs-main", "direction": "..."}}`
  对象形态（向后兼容读取：网关侧兼容旧 bool 值）。
- **D2 参数白名单**：仅 account/direction 两键；account 过
  `operations.workbench.valid_account`；direction 长度上限 200 字符。
- **D3 hosted_daily 注入**：`run_daily_async(accounts, direction="")`——
  direction 非空时替换 INSTRUCTION 中的选题指引段（模板化拼接）。
- **D4 前端技能卡片**：SkillPage 从「按钮+清单」改为技能卡片数组
  （SKILLS 常量：id/name/desc/params schema），运行后 toast 回显；
  结果不回显正文（触发即语义完成，执行结果看执行日志页）。
