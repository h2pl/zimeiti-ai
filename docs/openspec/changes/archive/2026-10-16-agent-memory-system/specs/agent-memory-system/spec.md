# agent-memory-system 规格草案

## Purpose

让 agent 拥有跨会话的可复用记忆：经验可记录、可检索、带溯源标注、防重复注入；与画像 memory.md（用户画像长期记忆）边界分明，互不污染。

## ADDED Requirements

### Requirement: 记忆记录与溯源

agent 可将可复用经验（用户偏好/红线/制作技巧/效果归因）记入记忆库；每条记忆带 origin_class（owner=用户明确陈述 / agent=agent 凝练 / system=系统事件）；一次性规格、临时参数、流水账不记录。

#### Scenario: 任务结束凝练经验
- **WHEN** 一轮任务结束且出现真正可复用的偏好/红线/技巧/归因
- **THEN** agent 给出拟记内容（1-3 条）并说明目标，用户确认后落库（origin=owner 或 agent）
- **THEN** 用户拒绝或未指定时不写入

#### Scenario: 不记一次性内容
- **WHEN** 内容为一次性规格、临时参数或流水账
- **THEN** 不写入记忆库

### Requirement: 记忆检索与注入标注

记忆检索工具返回结果带溯源标注（origin_class + 记录时间）；注入对话上下文的内容结构化标记，已注入过的内容不因相同检索而重复注入（recall-loop 预防）。

#### Scenario: 检索结果可溯源
- **WHEN** agent 检索记忆
- **THEN** 每条结果标注 origin_class 与创建时间

#### Scenario: 不重复注入
- **WHEN** 同一会话中相同记忆已被注入
- **THEN** 后续检索不重复返回该内容

### Requirement: compaction 前 flush

会话历史压缩（summarization）前，把当前会话的关键上下文写入 episodic 记录，防止压缩丢失可复用信息。

#### Scenario: 压缩前保存
- **WHEN** 会话触发历史压缩
- **THEN** 压缩执行前有关键上下文的 episodic 记忆落库

### Requirement: 与画像 memory.md 的边界

画像 memory.md 是用户画像的长期记忆（画像域）；agent 记忆库是运营经验记忆（agent 域）。两者互不写入对方；并行会话各自读所绑定画像的记忆，不跨画像借用。

#### Scenario: 边界不互写
- **WHEN** agent 记录经验
- **THEN** 写入 agent 记忆库，不修改任何画像的 memory.md（画像更新只经用户确认的画像管理流程）
- **WHEN** agent 读取画像
- **THEN** 只读当前会话绑定画像的 memory.md
