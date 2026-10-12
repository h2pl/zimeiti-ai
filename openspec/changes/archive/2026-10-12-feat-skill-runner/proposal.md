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
