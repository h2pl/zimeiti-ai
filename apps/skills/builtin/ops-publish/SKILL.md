---
name: ops-publish
description: >
  运营发布层：把内容库成稿排版并上传公众号草稿箱（只建草稿，绝不自动群发）。
  当用户说「发这篇 / 上传草稿 / 排版上传」时使用；成功后自动落归因记录。
layer: publish
---

# 运营发布层（ops-publish）

> 五层流程第四层：**发布**。目标——把成稿变成公众号后台里一篇可审的草稿。
> 上一层：`ops-create`；下一层：`ops-review`。
>
> **红线：只建草稿，绝不发布、绝不群发。** 任何「定时/群发/群发通知」动作都不做。

## 触发条件

用户要求上传草稿/排版发布时先读本 SKILL。

## 执行步骤

1. **确认输入**：`outputs/<slug>.md` 成稿路径 + 标题/作者（作者=画像名，如「江小湖」）。
2. **排版 + 建草稿**：调用 vendored 草稿流水线
   （`apps/skills/shared/scripts/wechat_mp/draft.py`，能力说明见同目录 README）：
   Markdown → 公众号样式 HTML → 封面（1:1 + 2.35:1）→ 摘要 → 草稿箱
   （media_id 幂等：重复跑是更新草稿，不是重复建）。
3. **凭据缺失处理**：公众号登录态过期时如实报告，不重试、不询问用户扫码以外的方案。

## 产物约定

- `outputs/wechat-drafts/<slug>/`：`draft_meta.json`（media_id/标题/摘要/封面）、
  排版 HTML、封面图
- 公众号后台「草稿箱」可见对应草稿（标题/封面/摘要/全文）

## 交接条件

草稿创建/更新成功 → 归因记录已自动写入 `outputs/_analytics/wechat-oa/` →
进入 `ops-review`（归因层复盘）。
