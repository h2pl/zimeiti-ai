---
change: ops-console-ui
design-doc: docs/openspec/changes/ops-console-ui/design.md
base-ref: ad6e97c
---

# Plan：运营控制台（定时任务 + 用量统计）

<!-- comet-task-authority: docs/openspec/changes/ops-console-ui/tasks.md -->

## G1 API 封装 <!-- comet-task-ref:a2d50993-6cd0-48b5-b4d7-c4cd44b10966 -->

lib/api.ts 补 automations 六函数 + usage 一函数（沿用 request 封装与 no-store 策略）。

## G2 自动化页 <!-- comet-task-ref:9c1ff0a5-8ba7-4d7b-8fb6-986695bc71fd --><!-- comet-task-ref:0ba93751-7b95-4122-aea1-61d5c0985090 --><!-- comet-task-ref:feaf9de8-9dd3-4e31-bd4c-8ef21ead0ff9 -->

AutomationsPage：列表三态 + 新建表单（后端错误回显）+ 启停 + 立即执行（后台提交提示
+ 延迟刷新）+ 执行记录（状态/摘要/耗时）+ 删除。

## G3 用量概览 <!-- comet-task-ref:75b77b78-77fd-42d4-9867-d03a043623fc --><!-- comet-task-ref:d283e83e-c88c-41ee-af48-8e30d5d6012e -->

UsageCard compact/full 两形态；接入工作台与设置面板；fallback 链与子代理模型只读展示。

## G4 导航与验证 <!-- comet-task-ref:ef42909e-a35f-4121-9f30-593cf7c2c990 --><!-- comet-task-ref:42d1827c-262e-41a2-a0b3-4383fb2c36f4 -->

侧栏导航项 + 图标 + App 路由分支；tsc/build/make check + 浏览器六项实测。
