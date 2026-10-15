# Tasks: browser-e2e

## 1. 套件骨架

- [x] 1.1 `apps/e2e/` 目录：`runner.py`（TargetManager：spawn/就绪/teardown，zimeiti 注入 mock LLM 环境变量与 Windows 策略） <!-- comet-task:c3675300-7f79-4cc2-b032-50b8b66f5c38 -->
- [x] 1.2 `mock_llm.py`：OpenAI 兼容 `/v1/chat/completions` 流式 mock（确定性回复、uvicorn 线程） <!-- comet-task:f521e41f-3749-4e15-bc7c-8cde611b1f84 -->
- [x] 1.3 `helpers.py`：click_nav 双重兜底、欢迎弹层轮询处理、`sync_mutation` 网络同步原语、`poll_text`、数据清扫 <!-- comet-task:bbb2fb4a-09c5-44af-badd-1627262c8574 -->
- [x] 1.4 `parity.py`：结构级观测值 diff（环境性差异 NOTE）+ `coverage_map.py` 映射表 <!-- comet-task:3374bf2e-0ff8-4c5b-82fb-3fb711b8d0ec -->
- [x] 1.5 `scenarios/base.py` 协议与 `run.py` 入口（`--scenarios`、`--target` 参数，退出码契约） <!-- comet-task:450cddd5-6223-496c-85ac-47efd11ea07d -->

## 2. 十个用户路径场景

- [x] 2.1 s01 首屏+引导弹层（异步挂载轮询、跳过、工作台渲染） <!-- comet-task:716ae5c7-9916-4ac7-96af-845360ee000a -->
- [x] 2.2 s02 侧栏 6 页 + 工具子导航 5 页全导航（无未捕获 JS 错误） <!-- comet-task:18da620d-c33e-470f-a521-dcd3f8b56e1e -->
- [x] 2.3 s03 选题 CRUD：新建（POST+GET 同步）→ 列表出现 → 删除 → 归零 + 残留清扫 <!-- comet-task:b95e4ea1-ac9a-45c4-9415-d65b710ca63a -->
- [x] 2.4 s04 选题→排期→内容日历出现条目→清理（POST /api/schedule 同步） <!-- comet-task:61ee8866-5c06-463a-93c6-abe502373cca -->
- [x] 2.5 s05 对话全链路：发送→流式开始→mock 回复渲染→完成→新建会话→切换→删除（confirm 对话框） <!-- comet-task:a0e63a15-0daf-4bff-bde6-d5fa63887668 -->
- [x] 2.6 s06 内容库：树渲染→打开 fixture 文件→预览内容断言（fixture 由 runner 预置/清理） <!-- comet-task:0c10a57e-9f5a-47ea-ac28-a7b36be72666 -->
- [x] 2.7 s07 画像：列表→创建向导（mock LLM 增强）→出现在列表→删除 <!-- comet-task:f057c549-1378-4142-abb4-bd98bba06a6a -->
- [x] 2.8 s08 账号页渲染 + whoami 状态结构 <!-- comet-task:ce137059-b32f-4669-b3c6-8cef32f85cdf -->
- [x] 2.9 s09 设置面板：模型通道行渲染可见 <!-- comet-task:79c5dd3c-f9d8-4888-99ec-87ad59cb95f7 -->
- [x] 2.10 s10 热点雷达：页渲染（条件断言）→有条目时「做内容」跳转对话页预填 <!-- comet-task:98d9b4d3-d058-4f05-81ea-18fc2a829ba9 -->

## 3. 集成与切换

- [x] 3.1 删除 `apps/scripts/browser_e2e.py` <!-- comet-task:26d87778-45f5-4589-a46e-076a4a1b797b -->
- [x] 3.2 Makefile `e2e-browser` 指向新入口；`apps/e2e/README.md`（使用说明+覆盖映射表） <!-- comet-task:aa8b69e0-cb40-421a-952a-827075d5a4a8 -->
- [x] 3.3 lint/format 通过（ruff 对 apps/e2e 或豁免配置） <!-- comet-task:e17be00b-cf40-497a-87e8-83771ccc4a4f -->

## 4. 验证

- [x] 4.1 全量套件双端跑通：全部场景 PASS、双端结构差异 0 <!-- comet-task:50eebab1-88b9-4c07-88a5-c4a66d822392 -->
- [x] 4.2 稳定性：连续 3 轮全绿、测试数据零残留 <!-- comet-task:d2a007b6-10dd-4e88-a693-3766295d5d6e -->
- [x] 4.3 `make check`（既有门禁）全绿不回归 <!-- comet-task:0bb0214f-eaaf-4b9e-b607-3cb37012bc8e -->
