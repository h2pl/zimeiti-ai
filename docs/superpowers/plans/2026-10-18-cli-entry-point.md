---
change: cli-entry-point
design-doc: docs/openspec/changes/cli-entry-point/design.md
base-ref: 937ece7
---

# Plan：命令行入口

<!-- comet-task-authority: docs/openspec/changes/cli-entry-point/tasks.md -->

## G1 客户端与命令树 <!-- comet-task-ref:7f70378c-b1f6-4e84-a1a5-077e27a146ee --><!-- comet-task-ref:7066ade5-242d-4e69-a0c9-7dc780fee50c --><!-- comet-task-ref:e3249684-6203-416f-8c97-efcc6483980f -->

client.py（urllib+SSE+错误翻译）；cli.py 子命令树+退出码契约；console script
注册 + 检查范围纳入。

## G2 验证与文档 <!-- comet-task-ref:5c979a79-5413-465f-9980-584f2ebb45dd --><!-- comet-task-ref:eeaf1eee-80dd-4f56-bca7-866bced42cd4 --><!-- comet-task-ref:af3af4c3-6ba3-495f-b36b-d0c4b7d722d7 -->

10 单测；真实服务探针（不烧 token）；README 章节；make check 全绿 + E2E 不回归。

## 探针抓出的两个真 bug（见提交信息）

1. `--base` 只认子命令前位置（argparse 全局参数限制）→ common 父解析器，
   SUPPRESS 默认值保证两种写法都通；回归测试固化
2. `/api/flows/runs` 与 `/api/flows/steps/catalog` 被更早注册的
   `/api/flows/{flow_id}` 动态路由吞掉——执行记录接口一直 404，Web 页面
   `.catch(()=>[])` 静默吞掉所以从未暴露。修路由顺序 + 新增
   `tests/test_route_ordering.py` 静态/动态路由遮蔽守卫（牙齿已验证：改回旧
   顺序即报红）
