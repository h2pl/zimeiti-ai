# Comet Design Handoff

- Change: feat-skill-runner
- Phase: design
- Mode: compact
- Context hash: e4cb745642462f9b325fa23ab10b275fe1004305dd7386d09c1b997553f4e35a

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## openspec/changes/feat-skill-runner/proposal.md

- Source: openspec/changes/feat-skill-runner/proposal.md
- Lines: 1-32
- SHA256: 4ebd764240e96ad13fc6c355c4c78233b1aae3f9b1883edec3f656e34640eb31

```md
# 提案：技能运行器（feat-skill-runner）

## Why

对齐缺口矩阵 ⚠ 第 4 项（最后一项）：SkillPage 只有运维触发+工具清单；
Easel 支持带参数手动运行技能。当前运维触发是固定参数（无账号/方向选择）。

## What Changes

- 后端：
  - `POST /api/ops/trigger` 扩展 params：{job, params:{account?, direction?}}；
    标记文件携带 params；网关消费时透传
  - `hosted_daily.run_daily_async(accounts, direction="")`：direction 注入
    INSTRUCTION（无方向时维持现状）
  - 网关 `_consume_manual_triggers` 读 params 并传给 hosted_daily
- 前端 SkillPage：技能卡片化（名称/描述/参数表单/运行按钮+最近结果），
  托管循环技能带「账号 + 选题方向」参数

## Capabilities

- **Modified Capabilities**: `web-workbench`（MODIFIED：运维操作页需求——
  触发带参数）

## Non-Goals

- 不做技能编排（多技能串联）；不做技能市场/分享

## 关键决策

- 参数收敛为「账号 + 选题方向」两个维度（覆盖托管循环最常见的手动诉求；
  数据取数/校准无参数）
- params 白名单键（account/direction），account 复用白名单校验

```

## openspec/changes/feat-skill-runner/design.md

- Source: openspec/changes/feat-skill-runner/design.md
- Lines: 1-20
- SHA256: 897eb99d5b13055190e70e1bc7fe7c268e1dc210ea5d2aa8128bf7296ff955d7

```md
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

```

## openspec/changes/feat-skill-runner/tasks.md

- Source: openspec/changes/feat-skill-runner/tasks.md
- Lines: 1-6
- SHA256: 9e68651a820af4817f1da4a14d4e786deb8b085f9f703612a38999fa8bdf8a69

```md
# 任务：feat-skill-runner

- [ ] T1 后端：ops/trigger params 白名单校验 + 标记对象格式（兼容旧值）+
      hosted_daily.run_daily_async(direction) + 网关透传 + 测试
- [ ] T2 前端：SkillPage 技能卡片（参数表单/运行）
- [ ] T3 make check + npm build + spec 场景核对

```

## openspec/changes/feat-skill-runner/.openspec.yaml

- Source: openspec/changes/feat-skill-runner/.openspec.yaml
- Lines: 1-2
- SHA256: 1dfdca412094f24473d8b842866201ec26f200b29b17064b03f1e4982c35a7b9

```md
schema: spec-driven
created: 2026-10-12

```

## openspec/changes/feat-skill-runner/specs/web-workbench/spec.md

- Source: openspec/changes/feat-skill-runner/specs/web-workbench/spec.md
- Lines: 1-16
- SHA256: 991a52f977e9faf69cb01a677816978de46ac87dc245b41616510b712bbe0657

```md
# web-workbench 能力增量（feat-skill-runner）

## MODIFIED Requirements

### Requirement: 运维操作页

运维操作页以技能卡片展示可手动运行的能力（名称/描述/参数表单/运行按钮）；
触发携带参数（账号 + 选题方向）写入标记文件，由常驻网关下一循环消费执行。

#### Scenario: 带参数触发托管循环
- **When** 用户在技能卡片填写账号与选题方向并运行
- **Then** 标记文件携带 params，网关消费时该轮托管循环使用指定账号与方向

#### Scenario: 参数白名单
- **When** trigger 提交未知 param 键或非法 account
- **Then** 返回 400，不写标记

```
