---
comet_change: cli-entry-point
---

# Tasks：cli-entry-point

## 1. 客户端与命令树

- [x] 1.1 client.py：urllib HTTP（统一错误）+ SSE 流式读取；单测（含错误翻译/连接失败行动指引） <!-- comet-task:7f70378c-b1f6-4e84-a1a5-077e27a146ee -->
- [x] 1.2 cli.py：chat/flows/runs/usage 子命令 + 退出码契约 + UTF-8 输出保护 <!-- comet-task:7066ade5-242d-4e69-a0c9-7dc780fee50c -->
- [x] 1.3 console script 注册（apps/api/pyproject）+ Makefile/pyproject 检查范围纳入 <!-- comet-task:e3249684-6203-416f-8c97-efcc6483980f -->

## 2. 验证与文档

- [x] 2.1 单测（客户端/命令树/参数解析/SSE 帧解析，mock 传输） <!-- comet-task:5c979a79-5413-465f-9980-584f2ebb45dd -->
- [x] 2.2 探针：真实服务上跑 flows 列表/新建/删除 + usage + runs（不烧 token） <!-- comet-task:eeaf1eee-80dd-4f56-bca7-866bced42cd4 -->
- [x] 2.3 README 补「命令行入口」章节；make check 全绿 + E2E 不回归 <!-- comet-task:af3af4c3-6ba3-495f-b36b-d0c4b7d722d7 -->
