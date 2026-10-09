# Tasks

## 1. 数据层

- [ ] 1.1 SQLite 数据层：publish_events / metric_snapshots / collection_errors 三表 + upsert 去重键（platform+source_folder+publish_date）+ 失败留痕；验证：单测覆盖幂等 upsert 与失败不覆盖历史 <!-- comet-task:8d8c204c-c3b9-4bc2-8fe5-dc688914368f -->
- [ ] 1.2 gzh datacube 取数入口：调用已 vendor 的 wechat_mp.client datacube 方法，写入快照（source=datacube）；验证：单测 mock 解析 + 日期跨度越界显式报错 <!-- comet-task:395260eb-f627-4aad-8eee-6120a3a7ae12 -->
- [ ] 1.3 xhs 创作者中心取数：复用登录态解析笔记行指标（列头动态映射）；验证：单测覆盖列解析与列缺失落 collection_errors <!-- comet-task:75778886-c690-4d6f-92c2-1f9046edacde -->

## 2. 只读消费

- [ ] 2.1 归因查询（只读）：按平台/画像趋势 + 单篇内容生命周期判定（速爆/稳增/长尾，确定性规则）；验证：单测断言查询结果且数据不回写 <!-- comet-task:eee6978a-b4aa-4895-bd7c-1433e6896c4d -->

## 3. 真账号走查

- [ ] 3.1 双平台真实取数一次并与后台数值人工比对；验证：快照落盘 + 人工核对一致 <!-- comet-task:563f8837-3e25-4909-9ddf-7c12db00f8f4 -->

## 4. 收尾

- [ ] 4.1 验证报告增补；验证：文档与证据一致 <!-- comet-task:0c3e4dd1-7b03-425e-92a2-0b7342ba4919 -->
