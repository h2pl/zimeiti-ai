---
name: ops-publish
description: >-
  运营发布层路由：把内容库成稿排版并上传公众号草稿箱。当用户说「发这篇、上传草稿、
  排版上传」时使用。只建草稿，绝不自动群发。本层是路由层——执行时先读下方详细技能。
layer: publish
---

# ops-publish 发布层（路由 + 发布门）

## 触发

发这篇 / 上传草稿 / 排版上传 / 同步到公众号

## 必读详细技能（先读再执行）

- `skills/builtin/skill-wechat-publisher/SKILL.md`：公众号草稿上传全流程
  （排版/封面/摘要/正文图/thumb 上传/draft 创建）
- `skills/builtin/skill-publish-checklist/SKILL.md`：发布前检查单

## 发布门（按序执行，缺一不可）

1. **内容安全门**：`exec_script content_guard scan --file <文章>`——BLOCK 级命中
   （退出码 7）必须删改敏感内容后重发，禁止 `--allow-unsafe` 绕过（用户明确要求除外）。
2. **人设一致性门**（只提醒、不阻断）：`exec_script persona_gate check --score <评分>`，
   评分须优先比较账号定位/赛道/形式/受众，不只因语气相似给高分；<80 分向用户展示
   分数、偏离点与修改建议；用户已明确要发布时继续执行，不额外索要确认。
3. **留痕**：草稿创建成功后写归因记录（ops-review 的数据源）。

## 硬边界

只建草稿，绝不自动群发；群发只能由用户在公众号后台手动完成。

## 交接

发布成功 → 归因层（ops-review）可复盘。
