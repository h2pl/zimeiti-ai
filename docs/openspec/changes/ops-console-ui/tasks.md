---
comet_change: ops-console-ui
---

# Tasks：运营控制台（定时任务 + 用量统计）

## 1. API 封装

- [ ] 1.1 `lib/api.ts` 补 automations 与 usage 六个函数（列表/新建/更新/删除/立即执行/执行记录/用量） <!-- comet-task:a2d50993-6cd0-48b5-b4d7-c4cd44b10966 -->

## 2. 自动化页

- [ ] 2.1 `components/AutomationsPage.tsx`：任务列表（名称/类型/时刻/下次运行/开关）+ 三态（loading/error/empty） <!-- comet-task:9c1ff0a5-8ba7-4d7b-8fb6-986695bc71fd -->
- [ ] 2.2 新建表单（名称+类型+时刻+指令）+ 后端错误提示（非法时刻/prompt 缺指令） <!-- comet-task:0ba93751-7b95-4122-aea1-61d5c0985090 -->
- [ ] 2.3 立立执行（后台提交提示 + 延迟刷新）+ 执行记录区（状态/摘要/耗时）+ 删除 <!-- comet-task:feaf9de8-9dd3-4e31-bd4c-8ef21ead0ff9 -->

## 3. 用量概览

- [ ] 3.1 `components/UsageCard.tsx`：汇总卡片（近 30 天 prompt/completion）+ 明细行 + 空态 <!-- comet-task:75b77b78-77fd-42d4-9867-d03a043623fc -->
- [ ] 3.2 接入工作台与设置面板；fallback 链/子代理模型只读展示 <!-- comet-task:d283e83e-c88c-41ee-af48-8e30d5d6012e -->

## 4. 导航与验证

- [ ] 4.1 侧栏加导航项 + App.tsx 路由分支 + 图标 <!-- comet-task:ef42909e-a35f-4121-9f30-593cf7c2c990 -->
- [ ] 4.2 tsc 通过 + make check 全绿 + 浏览器实测（新建→立即执行→记录出现→删除） <!-- comet-task:42d1827c-262e-41a2-a0b3-4383fb2c36f4 -->
