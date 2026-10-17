# autonomous-flow 规格草案

## Purpose

让一个定时任务能编排并跑完整条运营流程，每步状态与产出可追溯，为「无人值守运营」
提供执行骨架。

## ADDED Requirements

### Requirement: 运营流程定义与持久化

系统 SHALL 提供运营流程（flow）定义，MUST 支持从五层运营流程中裁剪步骤集
（discover / plan / produce / publish / review 的任意非空子集），并 MUST 持久化
到 PG（幂等建表）。

#### Scenario: 定义一条「发现+选题」的每日流程
- **WHEN** 用户创建流程：名称「每日选题」，步骤 `[discover, plan]`，schedule `08:00`
- **THEN** 流程持久化成功，可查询到步骤集与调度配置

### Requirement: 流程逐步执行与记录

调度到点时系统 SHALL 按步骤顺序串行执行，MUST 为每一步落记录（状态、耗时、
产出摘要、产出文件引用），并 MUST 把每一步的完整产出归档到 `outputs/_automations/`
下以流程执行实例为名的目录。

#### Scenario: 到点跑完整链路
- **WHEN** 流程「全链路」步骤 `[discover, plan, produce, review]` 到点执行
- **THEN** 依次执行四步，上一步产出摘要作为下一步输入；每步记录状态与耗时；
  执行结束后可查到每步的产出文件

#### Scenario: 单步失败
- **WHEN** 某一步执行抛错
- **THEN** 该步标记失败并记录错误原因，流程**不再继续后续步骤**（重试与熔断由
  护栏变更负责），整体执行结果如实反映「在第 N 步失败」

### Requirement: agent 入口经组装层注入

`zimeiti_autonomous` 包 MUST NOT import harness 的 agent 入口；入口 SHALL 由
组装层通过 setter 注入（对齐 personas / scheduler 既有范式）。

#### Scenario: 未注入时显式报错
- **WHEN** runner 执行流程但组装层未注入 agent 入口
- **THEN** 立即抛「agent 入口未注入」的明确错误，而非静默或 AttributeError

### Requirement: 既有任务类型行为零变化

`kind=case` 与 `kind=prompt` 两类既有定时任务 MUST 保持原有行为。

#### Scenario: 回归
- **WHEN** 运行既有 case/prompt 任务
- **THEN** 执行路径与产出位置与变更前一致
