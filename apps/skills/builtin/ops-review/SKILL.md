---
name: ops-review
description: >-
  运营归因层路由：发布记录复盘、数据回顾、下期建议。当用户说「复盘、数据怎么样、
  下期写什么、看看发布记录」时使用。本层是路由层——执行时先读下方详细技能。
layer: attribute
---

# ops-review 归因层（路由）

## 触发

复盘 / 数据怎么样 / 下期写什么 / 发布记录 / 效果如何

## 必读详细技能（按任务精度选，先读再执行）

- `skills/builtin/skill-publish-analytics/SKILL.md`：发布数据抓取与分析
- `skills/builtin/skill-content-postmortem/SKILL.md`：内容复盘方法论（事后分析）
- `skills/builtin/skill-data-tracker/SKILL.md`：数据追踪与看板

## 本层职责与产物

数据源清单（按序尝试，读不到就如实报告，不编造读数）：
1. `outputs/_analytics/`：本系统发布事实记录（日期/平台/标题/路径/media_id/状态）
2. 各平台登录态下的真实表现数据（skill-my-account / 账号分析接口）
3. 以上都无 → 明确报告「无数据支撑」，并说明需要什么数据才能复盘

产物：结构化复盘结论（manifest.py record 登记）；值得长期沉淀的经验经用户确认后
写入画像 memory.md。
