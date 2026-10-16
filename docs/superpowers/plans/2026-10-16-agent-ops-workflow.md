---
change: agent-ops-workflow
design-doc: docs/openspec/changes/agent-ops-workflow/design.md
base-ref: fa56b4e
archived-with: 2026-10-16-agent-ops-workflow
---

# Plan：agent-ops-workflow 五层运营流程技能化

<!-- comet-task-authority: docs/openspec/changes/agent-ops-workflow/tasks.md -->

## G0 归因数据源（先建地基：发布层的产物落点） <!-- comet-task-ref:04b0be57-7840-48ac-8d13-a4939c67d25f -->

`wechat_mp/analytics.py`：`record_publish(platform, content_path, media_id, status="pending-feedback")` 追加写 `outputs/_analytics/<platform>/<date>.json`（UTF-8、幂等 append-by-key）。draft.py 建草稿成功后调用。单测：写入/读取/空目录行为（RED→GREEN）。

## G1 五层 SKILL.md（核心内容，顺序=运营顺序）

1.1 ops-discover <!-- comet-task-ref:a18fc0aa-0932-49f2-ab34-c82b7c16049b -->：触发「发现选题/找热点/今天写什么」；数据源 GET /api/trends（weibo/douyin/zhihu）；步骤=抓榜→筛选（与画像赛道匹配度）→ POST /api/ideas 收藏；产物=选题库条目。
1.2 ops-plan <!-- comet-task-ref:b6d685e0-c426-4162-a46f-9b39345d6370 -->：触发「判断赛道/选角度/定选题」；读 profiles/<画像>/（identity/audience/style）；步骤=契合度评估→ 2-3 差异化角度→推荐；交接=选题+角度确定。
1.3 ops-create <!-- comet-task-ref:c440d4ba-d6d5-4522-8d20-6aa3c47688a2 -->：触发「写文章/出初稿/做内容」；步骤=钩子→短段→技术主体（可运行例子）→结尾引导；四项质检自检（钩子/字数 1200-1800/格式两层/数据不编造）；产物=outputs/<命名>.md。
1.4 ops-publish <!-- comet-task-ref:4b45a6ea-a652-4513-8c0e-ed931e35e769 -->：触发「发草稿/上传」；引用 wechat_mp draft 能力（只建草稿不发布）；产物=outputs/wechat-drafts/<slug>/；成功后进归因层（G0 落记录）。
1.5 ops-review <!-- comet-task-ref:b5feaeb4-bc04-4529-bc28-43727449fe26 -->：触发「复盘/数据怎么样」；读 outputs/_analytics/；无记录→如实报告并说明缺什么数据；有记录→按层给出结构化复盘。

## G2 SYSTEM_PROMPT 索引化 <!-- comet-task-ref:11f39498-1732-4a25-809b-36421d75b2a9 -->

改 agent_runtime.SYSTEM_PROMPT：保留既有硬约束（中文/文件布局/不编造），流程段替换为五层索引（每层一句话+触发词）+「执行前必须先读对应 SKILL.md」。

## G3 验证 <!-- comet-task-ref:ba721ff9-783f-4753-bdfb-51cad0aef9bd -->

`make check` 全绿 + 浏览器 E2E S5 无回归。<!-- comet-task-ref:ca884115-677f-41c0-a123-e95db6528bec -->
对话探针（真实 LLM）：发「围绕某热点做一期内容」→ 回复中明示流程层与 skill 引用；发「复盘」→ 无数据时如实报告（spec 场景核对）。<!-- comet-task-ref:1a37b684-502a-4239-bec7-4aa46a7d5587 -->
四条 Requirement 的 Scenario 逐条对照实现行为，记入验证报告。
