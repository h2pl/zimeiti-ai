# 验证报告（Verify Report）——变更 gzh-typesetting-pipeline

- 日期：2026-10-09
- 分支：comet/gzh-typesetting-pipeline（build 阶段完成即验证）
- 范围：公众号封面自动生成（vendor my-tools generate_cover_combined）

## 结论

**通过（Go）**——封面自动生成链路真账号验证通过：

- 拼接封面自动生成（900×1283：2.35:1 宽封面 + 1:1 方封面，标题自适应排版，裁剪坐标随草稿上送）
- 真账号发布至草稿箱 + 读回 **verified**（A3-gzh 复跑）
- 门禁：make check 58 passed（覆盖率 ≥80%）

## 校验记录

| 项 | 结果 | 证据 |
|---|---|---|
| 单测 | 12 passed（封面生成/裁剪坐标/显式封面/缓存复用/排版回归/来源标注） | tests/test_gzh_cover.py |
| 真账号走查 A3-gzh | verified | scripts/walkthrough_a3_gzh.py 输出 + 审计 JSONL + 草稿箱人工确认 |
| vendor 来源标注 | 上游一字未改 + 头部标注 | vendor/wechatfmt/generate_cover_combined.py |
| 门禁 | make check 全绿 | comet check run build 记录 fbaa…/a3e9… 日志 |

## 范围修正记录

proposal 初稿按「排版三模块全量接入」编写；经代码核对，正文排版转换（md2html + formatting）已在 real-account-verification build 阶段落地（vendor/wechatfmt/ 与依赖均已存在），本变更实际缺口仅封面自动生成——工件已修正为真实范围（铁律：零假阳性，禁止虚构范围）。

## 缺陷记录

| # | 缺陷 | 修复 |
|---|---|---|
| D1 | 话题/系列名等个人配置硬编码风险 | generate_cover_combined 调用时 sub/series 显式传空（zimeiti-ai 无系列体系） |
| D2 | 封面缓存使新封面路径无法触发 | 走查前迁移缓存文件（.bak），真实验证生成路径；生产行为：缓存优先不变 |

## 遗留

1. 封面主题（ocean 等 5 主题）当前默认 ocean，多主题可配置化留待后续
2. 公众号后台人工确认排版效果（草稿箱已可见，最终视觉验收归用户）
