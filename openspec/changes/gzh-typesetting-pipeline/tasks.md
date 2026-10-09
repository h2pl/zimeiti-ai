# Tasks

## 1. 管线接入

- [ ] 1.1 vendor 封面模块：拷贝 my-tools/wechat-mp-manage 的 generate_cover_combined.py 至 vendor/wechatfmt/（标注来源），新增依赖 Pillow；验证：uv sync 通过 + 模块可导入 <!-- comet-task:eb3ad730-2be0-4368-b8fe-b6df362bc244 -->
- [ ] 1.2 封面自动生成接入：publish_gzh_draft 无显式封面且无缓存时调用 generate_cover_combined（title=草稿标题，sub/series 留空），上传 thumb 并携带裁剪坐标；验证：单测断言封面 PNG 生成（900×1283）、裁剪坐标随草稿上送、显式封面路径行为不变 <!-- comet-task:9f02a521-412d-4c5a-b4f9-96afd26103cc -->

## 2. 真账号走查

- [ ] 2.1 A3-gzh 复跑：发布带排版草稿至草稿箱 + 读回 verified + 公众号后台人工确认排版效果；验证：审计留痕 + 平台截图 <!-- comet-task:a71ab0d6-ff75-4669-af82-c300569392c0 -->

## 3. 收尾

- [ ] 3.1 验证报告增补（本轮缺陷与证据）；验证：文档与证据一致 <!-- comet-task:43318177-d347-4c16-8695-c9907fae35a5 -->
