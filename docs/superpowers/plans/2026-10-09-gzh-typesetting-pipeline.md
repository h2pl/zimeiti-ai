---
change: gzh-typesetting-pipeline
design-doc: openspec/changes/gzh-typesetting-pipeline/design.md
base-ref: 484f7206b52dc57351a439c55fadd8361e9b94cd
archived-with: 2026-10-09-gzh-typesetting-pipeline
---

<!-- comet-task-authority: openspec/changes/gzh-typesetting-pipeline/tasks.md -->

# 实施计划：gzh-typesetting-pipeline

公众号发布质量补齐：封面自动生成（vendor my-tools generate_cover_combined，Pillow 拼接封面 900×1283）。
正文排版转换已由 real-account-verification 落地，本变更不含。需求来源：real-account-verification
验证报告遗留项 + AGENTS.md 开发铁律「禁止重复造轮子」。

## Phase A 管线接入（任务 1.1-1.2）

vendor generate_cover_combined（标注来源）+ Pillow 依赖 → publish_gzh_draft 无显式封面且无缓存时
自动生成拼接封面（title=草稿标题，sub/series 留空）→ 上传 thumb + 裁剪坐标随草稿上送。
验收：单测覆盖（PNG 900×1283 / 裁剪坐标 / 显式封面路径行为不变 / 缓存复用）。

## Phase B 真账号走查（任务 2.1）

A3-gzh 复跑：真实发布带排版与封面的草稿至草稿箱 + 读回 verified + 公众号后台人工确认排版效果。
验收：审计留痕 + 平台侧可见结果。

## Phase C 收尾（任务 3.1）

验证报告增补（本轮缺陷与证据）。

## 任务引用（canonical refs）

<!-- comet-task-ref:eb3ad730-2be0-4368-b8fe-b6df362bc244 -->
<!-- comet-task-ref:9f02a521-412d-4c5a-b4f9-96afd26103cc -->
<!-- comet-task-ref:a71ab0d6-ff75-4669-af82-c300569392c0 -->
<!-- comet-task-ref:43318177-d347-4c16-8695-c9907fae35a5 -->
