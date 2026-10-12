# 参考项目对齐：需求缺口分析（2026-10-10）

> **实施状态（2026-10-12 更新）**：P0 七项、P1 七项全部落地；页面层对齐
> Easel 后新增缺口矩阵 ⚠ 5 项已全部补齐：
> ① Chat 内联续跑+工具事件（feat-chat-resume-tools，08dcb11）
> ② 发布编排 UI 预检/定时/取消（feat-publish-orchestration，586107e）
> ③ 账号增删管理（feat-accounts-crud，c69f55c）
> ④ 技能运行器参数化触发（feat-skill-runner，2f16811）
> ⑤ 内容库正文查看（feat-outputs-viewer，786b284，并行会话完成）
> 全部经 Comet branch 隔离流程归档合并。P2 维持「按触发条件再做」。

> 调研对象：xiaobei（托管运营/获客/风控对标）、Easel（工作流/发布编排对标）。
> 方法：两轮代码级盘点（能力清单 + 实现位置证据），对照 zimeiti-ai 现状与 PRD
> （时间>创作>获客、先自用后订阅、图文起步、xhs+gzh 首发、发布 HITL）合成优先级。
> 本文是后续 OpenSpec 变更的需求池；实现时按宪法注明参考来源。

## zimeiti-ai 现状（已闭环）

选题→创作→合规（fail-closed）→HITL 双闸门（Web 审批页+interrupt）→发布
（xhs 私密 via xiaohongshu-mcp / gzh 草稿箱）→读回三档→审计 JSONL；频控/白名单/
Fernet 凭证；运营数据三表（PG）+HTML 报告+策略校准；常驻网关（APScheduler 07:30
内容 / 08:30 取数，catch-up 幂等）；gzh 排版管线（md2html+封面）。

## P0（发布闭环的生命线与短板，下一批变更）

| # | 需求 | 来源 | 参考实现 | 说明 |
|---|---|---|---|---|
| 1 | 风控信号分级：登录墙（SESSION_EXPIRED→停平台+上报）vs 软风控（SECURITY_BLOCK→降速冷却重试，不触发重登）；当前 blocked 三档无此语义 | xiaobei | `crews/main/skills/login-manager/SKILL.md`、`skills/_shared/relay-sign.ts`（LoginWallError/XhsSecurityBlockError 判定顺序） | xiaobei 有真实封号事故教训；xhs 读回/MCP 错误接入此分级 |
| 2 | 禁止 cookie 注入造会话红线 + 取数节流（单账号 24h 全量≤1 次、不翻页） | xiaobei | `docs/profile-loss-handling.md`、`expert-xhs/tools/xhs-engagement/SKILL.md` | 固化为代码断言与网关纪律，不靠提示词 |
| 3 | 错误分类纪律：单条失败留痕继续 / 设计性跳过码 / 登录失效停平台 | xiaobei | `xhs-engagement/SKILL.md` 退出码表、`HEARTBEAT.md` Step1 | ops_daily/hosted 的容错语义升级 |
| 4 | 发布结果通知 webhook（飞书/钉钉/TG 等）：发布成败、审批待办提醒 | Easel | `skills/openclaw/skill-publish-notify/` | 低成本高感知；同时解决「审批了没人知道」的遗留缺口 |
| 5 | 定时发布排期队列 + mark 幂等回填 | Easel | `skill-publish-scheduler/scripts/publish_queue.py`（「每条发布后务必 mark，避免重复发布」） | 挂到现有 APScheduler 网关扫描队列；与频控天然衔接 |
| 6 | 发布前约束校验前置（字数/比例/标签，确定性脚本） | Easel | `skill-cross-platform-publish/scripts/publish_dispatch.py` | 现在散在 xhs publisher 里，提为派发前统一预检 |
| 7 | 账号健康巡检 + 失效平台晨报 + 平台启停开关（platform-state.json fail-closed） | xiaobei | `HEARTBEAT.md` Step1/2/5、`published-track/SKILL.md` 平台状态段 | 挂网关巡检环节；登录失效自动发现并通知 |

## P1（生产管线与沉淀，自用期下一阶段）

| # | 需求 | 来源 | 参考实现 |
|---|---|---|---|
| 8 | HITL 升级：结构化问题卡片（执行中途随时向人提问，不只审批暂停） | Easel | `easel/gateway_questions.py` + `web/.../QuestionCards.tsx` |
| 9 | 单篇复盘（Hook/结构/选题/时间拆解成败 + 同期对照基线） | Easel | `skill-content-postmortem/SKILL.md` |
| 10 | 画像/DNA 结构化载体（{dna-id}.dna.md）+ 对标账号风格提炼 + 评估建议回写走 HITL（agent 不得自动改画像） | xiaobei | `expert-xhs/workflows/style-dna.md`、`tools/xhs-style-profiler/scripts/build_style_profile.py`；评估引擎我们已对标过（content-calibrator） |
| 11 | 选题看板（三态 Kanban）+ 内容日历（排期+状态回写） | Easel | `web/.../IdeasPage.tsx`、`CalendarPage.tsx` |
| 12 | 模板库/素材库沉淀（成功结构模板化复用） | Easel | `template-library/SKILL.md`、`asset-manager/SKILL.md` |
| 13 | gzh 排版主题化（主题组件库+自定义主题） | Easel | `gzh-design/SKILL.md` |
| 14 | 多账号 alias（accounts.json+记录带 account+评估按账号归一化） | xiaobei | `wx-mp-publisher/accounts.example.json`、`published-track record --account` |

## P2（远期/按 PRD 扩展触发——触发条件未到，暂不实现）

- 多平台抽象层（expert-pack 架构 + pub 分表 + 取数双链路）——**触发：接入第三平台**（xiaobei `published-track/SKILL.md`）
- 评论区获客/截流、潜客挖掘、私信客服——**触发：PRD 获客阶段启动**；浏览器互动自动化风控成本高，自用期先人工（xiaobei `expert-bd/SKILL.md`、`bd_record.db` 去重）
- 视觉资产设计系统 + AI 生图（xhs 知识卡组有价值，独立里程碑）——**触发：图文数据证明配图是瓶颈**（Easel `card-xiaohongshu/`、`ai_image.py`）
- 多格式一稿多发适配（字数硬裁剪三模式可复用为确定性脚本）——**触发：扩媒介（视频/知乎）**（Easel `text-condenser/`）
- UTM 短链归因——**触发：公开链接出现（xhs 转公开发布后）**（Easel `skill-short-link/`）
- 画像记忆回写——已被 P1⑩ dna suggest 覆盖（建议清单+人工回写）；全自动回写违反对齐纪律（Easel `skill-profile-manager/`）
- SKILL 原子能力三层加载规范（架构借鉴，降常驻 token）——**触发：工具数膨胀致 prompt 预算紧张**（Easel `docs/SKILL-SPEC.md`）

## 明确不对标

- AB 测试（Easel 也未实现，仅 Hook 变体评分）
- 全局 pipeline 状态机（deepagents/LangGraph 图编排已更可控；仅按需吸收 Easel
  video-pipeline-sdk 的「质量门+人工确认门」设计）
- cookie/CDP 造会话（xiaobei 事故红线，永久禁止）
