---
name: ops-plan
description: >-
  运营策划层路由：判断选题与账号赛道契合度、选二创角度、定选题。当用户说「这个题
  能不能做、选哪个角度、判断赛道、帮我定选题」时使用。本层是路由层——执行时先读
  下方详细技能。
layer: plan
---

# ops-plan 策划层（路由）

## 触发

这个题能不能做 / 选哪个角度 / 判断赛道 / 定选题 / 评估选题

## 必读详细技能（按任务精度选，先读再执行）

- `skills/builtin/skill-topic-evaluator/SKILL.md`：选题七维深评（流量/匹配/差异化/
  时效/变现/成本/合规）与推荐结论——**选题评估的权威流程在此，不要即兴**
- `skills/builtin/skill-content-strategy/SKILL.md`：内容支柱与账号定位策略
- `skills/builtin/skill-audience-profiler/SKILL.md`：受众画像分析

## 本层职责与产物

读当前画像（profiles/<画像>/）判断选题与赛道契合度，产出 2-3 个差异化角度与推荐；
产物：评估结论+角度清单（manifest.py record 登记）。事实边界：热点新闻只作引子，
主体写技术原理；无数据支撑处如实说明。

## 交接

确定的选题+推荐角度交给制作层（ops-create）。
