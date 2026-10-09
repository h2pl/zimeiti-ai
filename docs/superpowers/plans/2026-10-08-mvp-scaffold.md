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

## Task Mapping（comet-task-ref）

- Phase A 工程骨架
  - 1.1 目录与 README <!-- comet-task-ref:ab562423-79d8-4232-8d28-3b9492d27897 -->
  - 1.2 uv 初始化与依赖锁定 <!-- comet-task-ref:ec920216-1889-45bc-aebf-d7553be8097e -->
  - 1.3 docker-compose <!-- comet-task-ref:35f2d9c7-8629-4e30-a710-97a27922c0ea -->
  - 1.4 FastAPI /health <!-- comet-task-ref:d28c0535-77ce-4fa6-9b03-90c5d59ee829 -->
- Phase B 主干与托管循环
  - 2.1 checkpointer <!-- comet-task-ref:5e336a78-8dc2-4a93-a8c7-54449d81c745 -->
  - 2.2 最小执行图 <!-- comet-task-ref:ed3ef53c-c3fd-4dca-bdc1-d0f8255eeb47 -->
  - 2.3 托管触发/断点恢复 <!-- comet-task-ref:ce77da8a-73e5-4e1d-a067-0a37c459b7f1 -->
  - 2.4 执行审计 <!-- comet-task-ref:a698fc0d-b997-402d-981f-34fc34ffea91 -->
- Phase C 画像与选题
  - 3.1 画像 schema/加载 <!-- comet-task-ref:f2ce709c-f4ed-46c6-a8b4-7d8eaa9ba2a9 -->
  - 3.2 注入与隔离 <!-- comet-task-ref:de1a3007-1413-4b8b-ba3d-1e3c2a7ec0aa -->
  - 4.1 选题卡产出 <!-- comet-task-ref:0cccb9ae-d49e-4d88-ad2f-bf3b16ae590a -->
  - 4.2 人工挑选闸门 <!-- comet-task-ref:0522e9c2-c078-4b0e-8d5d-f0f0358a147a -->
- Phase D 图文创作
  - 5.1 小红书草稿 <!-- comet-task-ref:c0e09a3e-1e99-48b8-a121-4930c73c4fc1 -->
  - 5.2 公众号草稿 <!-- comet-task-ref:3cd7010a-e18a-487a-8ab5-4088342bd586 -->
  - 5.3 合规闸门接入 <!-- comet-task-ref:b8420d7e-183c-4741-9c77-0a05a95ee578 -->
- Phase E 平台发布
  - 6.1 执行器框架 <!-- comet-task-ref:146a56df-1d9b-497c-8b02-a31399ff3a2c -->
  - 6.2 小红书脚本+读回 <!-- comet-task-ref:5df30b6a-cc1e-4ef5-99bc-8dc77426086a -->
  - 6.3 公众号脚本+读回 <!-- comet-task-ref:8f0e9db9-e476-4adb-88c6-6fbc67c08ee0 -->
  - 6.4 凭证加密 <!-- comet-task-ref:d2c1d792-2927-4520-acd8-9e4f337761a8 -->
- Phase F Web
  - 7.1 Next.js→Vite 审批页 <!-- comet-task-ref:2b61ca8b-bc91-407c-a8fa-f9105f2f0fa8 -->
  - 7.2 审批 API 对接 <!-- comet-task-ref:6261e12c-f3ef-44b1-af8f-6e0d533a34c2 -->
- Phase G 验证收尾
  - 8.1 全量测试 <!-- comet-task-ref:8357c148-bd8f-47e9-be35-f095eb6edfe1 -->
  - 8.2 验收核验（mock 层；真账号实测拆至后续变更） <!-- comet-task-ref:e6d0928a-5c84-4611-ad85-3ae610e63697 -->
  - 8.3 测试报告/缺陷记录 <!-- comet-task-ref:a73a7ee0-29f0-42df-8f87-852faedcc81c -->
