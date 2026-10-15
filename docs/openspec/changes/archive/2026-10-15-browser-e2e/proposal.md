# Proposal: browser-e2e

## Why

浏览器级 E2E 目前是单个 300 行脚本（`apps/scripts/browser_e2e.py`），仅覆盖 5 个粗粒度场景（首屏/导航/选题/对话/渲染）。用户路径远不止这些：排期、内容库预览、画像向导、账号、设置、热点跳转等全部没有浏览器层覆盖；单文件结构也无法承载"覆盖每个用户路径"的目标。另外 LLM 调用走真实 `.env` key，慢且不确定——需要 mock 边界让全链路测试确定性化。

## What Changes

- 新建 `apps/e2e/` 独立目录管理浏览器自动化测试：
  - `runner.py`——双端目标管理（spawn zimeiti:8110 / Easel:7860、就绪等待、teardown）
  - `mock_llm.py`——OpenAI 兼容流式 mock 服务器（本地端口，zimeiti 后端以 `OPENAI_BASE_URL` 指向它），对话/画像向导走真实后端链路但 LLM 响应确定性
  - `helpers.py`——导航点击、欢迎弹层处理、网络回包同步原语、数据清扫
  - `parity.py`——双端观测值对齐比较器
  - `scenarios/`——按用户路径拆分的场景模块（每路径一文件）
- 场景覆盖（每个用户路径）：首屏引导、全页面导航、选题 CRUD、选题→排期→日历、对话流式（含新建会话/删除会话）、内容库浏览+文件预览、画像列表+创建向导+删除、账号页 whoami、设置面板模型通道、热点→做内容跳转
- 删除 `apps/scripts/browser_e2e.py`（内容全部迁移重组，无行为丢失）
- `make e2e-browser` 指向新入口；套件可单跑某场景、可单端跑（调试用）

## Capabilities

### New Capabilities

- `browser-e2e-suite`: 浏览器级双端对齐测试套件的结构、场景覆盖与运行契约

### Modified Capabilities

（无——本变更只新增测试设施，不改产品行为）
