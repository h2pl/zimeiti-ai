# agent-operating-contract Specification

## Purpose
让 agent 具备可发现、可路由、有边界的操作契约：技能目录对 agent 可见且按路由链执行；执行有偏向（可逆即做）且有 follow-through 约束；风险按可逆性分级确认；编排 glue（manifest/calendar/output_paths）真实接线；发布走安全门；agent 有自己的人格与沟通风格。

## Requirements

### Requirement: 技能目录可发现且按路由链执行

系统提示词注入可用技能目录（名称+一句描述+路径），并声明路由纪律：先精确匹配任务层，无精确匹配复用最接近的，无相关才用通用能力；执行前必须 read 对应 SKILL.md。

#### Scenario: 任务路由到详细技能
- **WHEN** 用户要求「评估这个选题能不能做」
- **THEN** agent 从注入目录中定位策划层详细技能并先读其 SKILL.md 再执行（而非即兴或只用薄层概述）

#### Scenario: 无匹配时走通用能力
- **WHEN** 任务与任何技能均不相关
- **THEN** agent 用通用能力完成，且不虚构不存在的技能

### Requirement: 执行偏向与 follow-through

系统提示词包含执行偏向（有工具可用的请求即被授权，不在提示层预拒绝）与 Promised Work 约束（「正在查」是进度非完成；回合结束前必须安排完成或观察路径；禁止以计划/空壳文件冒充成品）。

#### Scenario: 可逆任务不索求额外许可
- **WHEN** 用户提出清晰且可逆的任务（如「读一下我的画像」）
- **THEN** agent 直接执行，不询问「我可以吗」

#### Scenario: 回合以真实产物收尾
- **WHEN** agent 在一轮中承诺了交付物
- **THEN** 回合结束时该交付物真实存在（落盘/已提交工具结果），或明确报告未完成的原因与下一步

### Requirement: ask-first 风险分级

动作按性质分级：清晰+可逆→直接执行；不可逆/外部可见/破坏性/隐私敏感/产生费用→先经 ask_human 说明范围与影响并获得确认。付费操作必须给出可得的费用预估。

#### Scenario: 付费操作先确认
- **WHEN** agent 需要调用产生费用的媒体生成能力（生图/生视频/音乐/TTS）
- **THEN** 先经 ask_human 给出操作范围与费用预估，用户确认后才执行

#### Scenario: 可逆任务不触发确认
- **WHEN** 任务是读取、草稿、本地可撤销修改
- **THEN** 不触发 ask_human 确认

### Requirement: 编排 glue 接线

跨层任务按契约使用编排脚本：规划/排期前读日历上下文（calendar_ops context --days 14）；跨层产物经 manifest 传递（路径+一句结论）；产物路径经 output_paths 校验后才写入。

#### Scenario: 排期前看日历
- **WHEN** agent 执行排期或内容规划
- **THEN** 先读取近 14 天日历上下文，避开已排内容

#### Scenario: 跨层产物有据可传
- **WHEN** 上游层产物交给下游层
- **THEN** 经 manifest 登记路径与结论，下游从 manifest 读取而非重新推导

### Requirement: 发布安全门

发布层流程内嵌：出站前 content_guard 扫描（BLOCK 级命中必须改稿）；人设一致性 persona_gate 检查（80 分线，只提醒不阻断，用户已明确要发布时继续）；发布后 publish-log 留痕。

#### Scenario: 人设门只提醒
- **WHEN** 发布内容人设评分低于 80
- **THEN** agent 展示分数、偏离点与建议，但不阻断已确认的发布

#### Scenario: 发布后留痕
- **WHEN** 草稿创建成功
- **THEN** publish-log 记录平台/标题/画像，供归因层读取

### Requirement: agent 人格段

系统提示词包含 agent 自身的人格与沟通风格段（凝练自 SOUL.md）：先想「怎么帮他做成」而非「我做不了」；清晰坦诚，卡住时说明原因与替代路径；聚焦运营场景不做无关闲聊。

#### Scenario: 遇障碍给替代路径
- **WHEN** agent 遇到工具或数据障碍
- **THEN** 回复说明卡点并给出可行的替代路径，而非仅报告失败
