---
name: ops-discover
description: >-
  运营发现层路由：找热点、筛选题、追热点。当用户说「找选题、今天写什么、追热点、
  看看有什么可写的」时使用。本层是路由层——执行时先读下方详细技能，按其中的流程走，不要跳过。
layer: discover
---

# ops-discover 发现层（路由）

## 触发

找选题 / 今天写什么 / 追热点 / 热点雷达 / 有什么可写的

## 必读详细技能（按任务精度选，先读再执行）

- `skills/builtin/skill-trending-topics/SKILL.md`：热点抓取与榜单浏览（系统热点雷达数据源）
- `skills/builtin/skill-trend-rider/SKILL.md`：热点二创机会评估（哪些热点值得追、怎么追）
- `skills/builtin/skill-news-intelligence/SKILL.md`：行业资讯与信源监控

## 本层职责与产物

从热点/资讯中筛出与账号赛道相关的候选选题；产物：候选选题清单（写入 outputs/ 或
经 manifest.py record 登记路径+结论）。筛选标准见对应详细技能；无精确匹配时用最接近的
技能，都不要时用通用能力（grep/read 系统数据）。

## 交接

候选选题交给策划层（ops-plan）做赛道评估。
