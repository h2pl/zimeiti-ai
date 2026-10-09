# 验证报告（Verify Report）——变更 ops-metrics-collection

- 日期：2026-10-09
- 分支：comet/ops-metrics-collection
- 范围：运营数据层（发布事件/指标快照/失败留痕）+ 双平台取数 + 只读归因

## 结论

**通过（Go）**——双平台真实取数与后台数值一致：

- gzh：datacube 真实返回（近 7 日新增 1 / 取消 0）
- xhs：创作者中心看板真实解析（关注 6 / 粉丝 212 / 获赞与收藏 5281，与页面一致）
- 门禁：make check 77 passed，覆盖率 ≥80%

## 校验记录

| 项 | 结果 | 证据 |
|---|---|---|
| 事件 upsert | 同 platform+source_folder+publish_date 更新而非插入 | tests/test_ops_metrics.py |
| 失败保留历史 | 采集失败落 collection_errors，历史值不被零覆盖 | 单测 + spec 场景 |
| gzh 取数 | ok=true（user_source/new_user/cancel_user） | `python -m zimeiti_api.ops_metrics pull --platform gzh` |
| xhs 取数 | ok=true（12 项指标，与页面文本一致） | `python -m zimeiti_api.ops_metrics pull --platform xhs` |
| 只读归因 | report 前后快照不变 + 生命周期判定确定性 | 单测 |
| 发布事件接线 | tools.publish 成功/失败均记录 | tools.py |

## 缺陷记录

| # | 缺陷 | 根因 | 修复 |
|---|---|---|---|
| D1 | gzh datacube 返回非 JSON | 上游 `wechat_mp._post` 固定拼 `/cgi-bin` 前缀，而 datacube 在 `/datacube` 下 | 适配层 `GzhClient.datacube()` 单独实现（不改 vendor，注明差异） |
| D2 | datacube 取今天返回空 | 仅提供 T-1 及以前数据 | CLI 默认取过去 7 天（截至昨天） |
| D3 | **xhs 指标错位一位**（关注数读成 212、粉丝数读成 5281） | 首页两种排版并存：账号概览「值→标签」、数据总览「标签→值」 | 按「笔记数据总览」边界分区解析 + 回归测试 |
| D4 | xhs 单篇明细列语义不可确定 | 笔记管理页 5 个数字列无列头文本、无 title 属性（仅 svg 图标） | 范围收敛：本变更只采账号级指标；列序留待人工比对后做（后续变更） |

## 设计来源（开发铁律「禁止重复造轮子」）

- **xiaobei `published-track`**：SQLite 单库、upsert 去重键、采集失败留痕、关联内容策略校准
- **Easel 数据三层**：事件与快照分离（单一事实来源）、消费层只读不回写、确定性脚本聚合、内容生命周期分类
- **未采用 MediaCrawler**（46k stars）：其许可证为 NON-COMMERCIAL LEARNING LICENSE 1.1，与 PRD 订阅 SaaS 商业化路径冲突；xhs 数据改走自有创作者中心通道，零许可证风险

## 遗留

1. xhs 单篇笔记明细指标（列语义需人工比对笔记管理页 5 列数字后固化）
2. 定时调度（当前手工/托管循环触发）
3. 消费方（内容策略校准）尚未接入——本变更只提供只读归因数据
