# 验证报告（Verify Report）——变更 content-strategy-calibration

- 日期：2026-10-10
- 分支：comet/content-strategy-calibration
- 范围：内容策略校准证据引擎与评估报告（对标 xiaobei content-calibrator 四铁律 + Easel publish-analytics）

## 结论

**通过（Go）**——用已回收真实数据生成校准报告，证据与洞察分离、混杂降级、画像零改动：

- xhs-main / gzh-main 双平台校准报告生成（12 项账号级指标证据齐全）
- 基线不足（单点快照）诚实标注，未伪造归一化值
- 门禁：make check 全绿（85 passed）

## 校验记录

| 项 | 结果 | 证据 |
|---|---|---|
| 证据引擎 | 基线归一化/趋势/生命周期分布/发布节奏，只读不回写 | tests/test_ops_calibration.py（8 passed） |
| 报告结构 | 证据/结论/Agent 洞察留位/建议 章节齐全 | 单测 + 真实报告检视 |
| 混杂降级 | 快照 <5 → 「观察（混杂：样本不足）」 | 单测 + 真实报告（首轮快照仅 1 组，正确降级） |
| 画像零改动 | 校准前后画像文件一致 | 单测（monkeypatch profile_paths） |
| CLI | calibrate --platform/--profile/--force | 真实执行输出 |

## 设计遵循（xiaobei 四铁律对照）

| 铁律 | 落地 |
|---|---|
| 趋势优先 | 基线归一化（值/账号均值），绝对值仅上下文 |
| 脚本只给证据 | eval.md 证据章为确定性计算；洞察章留位给 Agent |
| 先排混杂再归因 | 成熟度检查（快照≥5+跨度≥3天）不足 → 降级「观察」 |
| 不自动改策略 | calibrate 不触碰画像文件（单测覆盖） |

## 遗留

1. 洞察生成（--with-insights 模型回读）留待 hosted 创作前消费时一并做（设计 D4）
2. 按量自动触发（成熟记录积累后）
3. 多账号聚合对比
