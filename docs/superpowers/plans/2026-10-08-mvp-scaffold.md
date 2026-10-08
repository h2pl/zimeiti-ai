---
change: mvp-scaffold
design-doc: openspec/changes/mvp-scaffold/design.md
base-ref: b681d3128aab1db5cae9ab08108efbbe72c0cdca
---

<!-- comet-task-authority: openspec/changes/mvp-scaffold/tasks.md -->

# 实施计划：mvp-scaffold（最小闭环骨架）

需求基准：`docs/prd/zimeiti-ai-prd.md`（A1-A6）｜行为契约：5 个 delta spec｜技术决策：design.md D0-D7
配置：autonomous / tdd / standard，Python 3.12 + uv，Postgres 真库（docker）

## Phase A：工程骨架（tasks 1.1-1.4）

串行强依赖。产出可启动的空壳：四目录 + uv 环境 + Postgres 容器 + /health。
验收：`uv run uvicorn` 后 `/health` 200；`docker compose ps` 健康。

## Phase B：主干与托管循环（tasks 2.1-2.4）

checkpointer 接入 → 最小图（选题→创作→审批 interrupt→发布）→ 触发器 → 审计。
验收：图执行到审批中断点；kill 重启后从持久化状态恢复。

## Phase C：画像与选题（tasks 3.1-3.2, 4.1-4.2）

画像 schema/加载/注入隔离；选题卡产出 + 人工挑选闸门。
验收：单测断言隔离与未挑选不创作。

## Phase D：图文创作（tasks 5.1-5.3）

deepagents 创作 subagent：小红书笔记/公众号文章草稿；合规闸门 fail-closed 接入。
验收：给定选题+画像产出双草稿；命中规则被阻断。

## Phase E：平台发布（tasks 6.1-6.4）

执行器框架（频控/白名单 fail-closed）→ 小红书脚本+读回 → 公众号脚本+读回 → 凭证加密。
验收：超频控拒绝；测试号小流量发布读回三档 outcome；明文不落盘。

## Phase F：Web 最小界面（tasks 7.1-7.2）

Next.js 审批列表/状态页 + 确认动作对接 resume。
验收：页面可见待审批项，确认后图继续执行。

## Phase G：验证收尾（tasks 8.1-8.3）

全量测试 → A1-A6 真账号小流量走查 → test-summary/defect-log。

## 风险与回滚

- 小红书/公众号选择器失效：脚本隔离 + 选择器集中维护（Easel 模式）
- 风控：全程测试号、低频、读回对账；频控 fail-closed
- deepagents API churn：锁 `deepagents>=0.7.6,<0.8`，适配层隔离创作段
- 回滚：Phase 内 `git reset`；Phase 间独立 commit

## 依赖顺序

A → B → (C,D 可并行) → E（依赖 B/D4）→ F → G
