---
comet_change: agent-ops-workflow
---

# Tasks：五层运营流程技能化

## 1. 五层 skills 内容（apps/skills/builtin/）

- [ ] 1.1 `ops-discover/SKILL.md` 发现层：热点雷达（/api/trends 数据源）→ 热点筛选 → 收藏为选题（/api/ideas）；触发条件「发现选题/找热点/今天写什么」；产物=选题库条目
- [ ] 1.2 `ops-plan/SKILL.md` 策划层：读画像 profiles/（赛道/受众）评估选题契合度、产出差异化角度与推荐；触发条件「判断赛道/选角度/定选题」；交接条件=确定选题+角度后进制作层
- [ ] 1.3 `ops-create/SKILL.md` 制作层：按写作规范成稿（钩子/字数/格式/数据边界四项质检清单）；产物=outputs/ 下命名文章；触发条件「写文章/出初稿/做内容」
- [ ] 1.4 `ops-publish/SKILL.md` 发布层：草稿链路说明（wechat_mp draft 能力、只建草稿不发布）；产物=outputs/wechat-drafts/ 排版材料；交接条件=草稿创建成功后进归因层
- [ ] 1.5 `ops-review/SKILL.md` 归因层：读 outputs/_analytics/ 数据做结构化复盘；无记录时如实报告并说明需要什么数据；触发条件「复盘/数据怎么样」

## 2. Agent 接线

- [ ] 2.1 SYSTEM_PROMPT 索引化：五层名称+触发规则一句话+「执行前必须先读对应 SKILL.md」硬指令；删除流程细节（保留语言/文件布局/不编造数据等既有硬约束）
- [ ] 2.2 最小归因数据源：发布/草稿创建成功时写 `outputs/_analytics/` 记录（日期/平台/内容路径/media_id/状态），归因层读它

## 3. 验证

- [ ] 3.1 `make check` 全绿 + 浏览器 E2E S5（对话）无回归
- [ ] 3.2 对话探针：发「围绕某热点做一期内容」→ 验证 agent 按层执行（回复中明示流程层、引用 skill）；发「复盘」→ 无数据时如实报告
- [ ] 3.3 spec 场景核对：四条 Requirement 的 Scenario 逐条对照实现行为
