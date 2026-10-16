---
comet_change: agent-ops-workflow
---

# 设计：五层运营流程技能化

## 高层方案

```
SYSTEM_PROMPT（索引层，改一次定型）
  "运营任务分五层：发现 ops-discover / 策划 ops-plan / 制作 ops-create /
   发布 ops-publish / 归因 ops-review。执行前必须先读对应 SKILL.md。"
        │ agent 按任务自选层
        v
apps/skills/builtin/ops-*/SKILL.md（流程层，可独立演进）
  每个文件声明：触发条件 → 执行步骤 → 数据源（API/文件）→ 产物约定 → 交接条件
        │ agent 用既有文件工具按需读取
        v
真实世界（已接线）
  发现层 ← /api/trends（热点雷达）
  策划层 ← 画像 profiles/（赛道/受众）+ 选题库 /api/ideas
  制作层 ← multi-agent-manager 写作规范（已沉淀为 WRITING 范式）
  发布层 ← wechat_mp draft.py（已沉淀，batch 外）
  归因层 ← outputs/_analytics/（本 change 新建最小数据源）
```

## 关键决策

### D1：skills 放 builtin 还是 shared
放 `apps/skills/builtin/`（与 card-design 等 119 个内置技能同层，/api/status 的技能清单自动收录，设置面板可见）。`shared/scripts/` 只放可执行脚本，不放流程文档。

### D2：归因层数据源——发布时写最小记录
系统当前没有持久化的往期表现数据（agent 实证报告过 `_analytics/` 不存在）。本 change 落**最小真实数据源**：发布流程（草稿创建成功）时在 `outputs/_analytics/` 追加一条 JSON 记录（日期、平台、内容路径、media_id、状态=pending-feedback），后续真实阅读/互动数据接入时在同一文件体系上扩展。归因层 SKILL.md 声明：读 `_analytics/`，无记录→如实报告。**不做**：接微信阅读数据 API（需要凭据+拉取任务，超出本 change）。

### D3：SYSTEM_PROMPT 收敛边界
索引化只删流程细节，保留既有硬约束（中文回复、文件布局说明、不编造数据）。触发规则用一句话×5 层，防止提示词膨胀。

### D4：制作层与 multi-agent-manager 知识库的关系
写作规范已在 case 中沉淀使用（WRITING 范式），制作层 SKILL.md 把它固化为**质检清单**（钩子/字数/格式/数据边界四项自检），不引入对 multi-agent-manager 仓库的运行时依赖（那是外部项目，知识要落在自己仓库）。

## 风险与对策

- **风险**：agent 不读 skill 直接即兴（prompt 遵从性）→ 对策：SYSTEM_PROMPT 用硬性指令（"必须先读"）+ 验证任务做对话探针确认
- **风险**：五层之间交接断裂（上层不知道下层产物在哪）→ 对策：每个 SKILL.md 显式写"交接条件"节，spec 已约束产物命名
- **风险**：归因层无数据被 agent 编造 → 对策：skill 明示"无记录即报告"，且 spec 场景覆盖

## Open Questions

无——三个关键决策（白名单执行器归 batch ②、五层 skills 载体、拆分方式）均已由用户确认。
