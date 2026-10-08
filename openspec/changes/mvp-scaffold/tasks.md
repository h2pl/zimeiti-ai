# Tasks

## 1. 工程骨架

- [x] 1.1 初始化单仓库四目录（apps/api、apps/web、packages/skills、mcp/）与根 README；验证：目录结构与本文档一致，README 存在 <!-- comet-task:ab562423-79d8-4232-8d28-3b9492d27897 -->
- [x] 1.2 apps/api 用 uv 初始化并锁定 Python 3.12 与 LangGraph/deepagents/LiteLLM/FastAPI 版本；验证：`uv sync` 成功且 `uv run python -c "import langgraph, fastapi"` 无报错 <!-- comet-task:ec920216-1889-45bc-aebf-d7553be8097e -->
- [ ] 1.3 编写 docker-compose.yml（Postgres + pgvector + 健康检查）；验证：`docker compose up -d` 后健康检查通过，`psql` 可连 <!-- comet-task:35f2d9c7-8629-4e30-a710-97a27922c0ea -->
- [x] 1.4 FastAPI 应用工厂与 `/health` 端点；验证：`uv run uvicorn` 启动后 `GET /health` 返回 200 <!-- comet-task:d28c0535-77ce-4fa6-9b03-90c5d59ee829 -->

## 2. LangGraph 主干与托管循环（hosted-loop）

- [x] 2.1 Postgres checkpointer 接入与连接管理；验证：写入一条检查点后能在数据库中查到对应记录 <!-- comet-task:5e336a78-8dc2-4a93-a8c7-54449d81c745 -->
- [ ] 2.2 最小执行图（选题→创作→审批 interrupt→发布）编排；验证：本地触发图执行能走到审批中断点 <!-- comet-task:ed3ef53c-c3fd-4dca-bdc1-d0f8255eeb47 -->
- [ ] 2.3 托管触发器（定时/事件入口）与断点恢复；验证：kill 进程后重启，循环从持久化状态继续且已完成节点不重复执行 <!-- comet-task:ce77da8a-73e5-4e1d-a067-0a37c459b7f1 -->
- [ ] 2.4 执行审计记录（动作/时间/结果）写入与查询接口；验证：执行一轮后审计查询接口返回完整动作列表 <!-- comet-task:a698fc0d-b997-402d-981f-34fc34ffea91 -->

## 3. 账号画像（account-profile）

- [ ] 3.1 画像文件 schema 与加载/校验；验证：示例画像通过校验，缺字段画像被拒绝并提示缺失项 <!-- comet-task:f2ce709c-f4ed-46c6-a8b4-7d8eaa9ba2a9 -->
- [ ] 3.2 创作上下文注入与多账号隔离；验证：账号 A 创作任务的上下文不含账号 B 的画像内容（测试断言） <!-- comet-task:de1a3007-1413-4b8b-ba3d-1e3c2a7ec0aa -->

## 4. 选题（topic-discovery）

- [ ] 4.1 选题卡产出（信息源输入→结构化选题卡）；验证：给定测试输入产出 ≥3 张含标题/理由/方向的选题卡 <!-- comet-task:0cccb9ae-d49e-4d88-ad2f-bf3b16ae590a -->
- [ ] 4.2 人工挑选接口；验证：未挑选状态下创作流程不被触发（测试断言） <!-- comet-task:0522e9c2-c078-4b0e-8d5d-f0f0358a147a -->

## 5. 图文创作（content-creation）

- [ ] 5.1 小红书笔记草稿生成（deepagents 创作段）；验证：给定选题+画像产出含标题/正文/标签/封面文案的草稿制品 <!-- comet-task:c0e09a3e-1e99-48b8-a121-4930c73c4fc1 -->
- [ ] 5.2 公众号文章草稿生成；验证：产出含标题/正文/摘要的草稿制品 <!-- comet-task:3cd7010a-e18a-487a-8ab5-4088342bd586 -->
- [ ] 5.3 合规审查闸门（fail-closed）接入创作→审批链路；验证：构造命中规则的草稿被标记阻断且不可进入可发布状态（测试断言） <!-- comet-task:b8420d7e-183c-4741-9c77-0a05a95ee578 -->

## 6. 平台发布（platform-publishing）

- [ ] 6.1 发布执行器框架（确定性脚本 + 频控/白名单入口强制）；验证：超频控任务被拒绝且无平台侧调用（测试断言） <!-- comet-task:146a56df-1d9b-497c-8b02-a31399ff3a2c -->
- [ ] 6.2 小红书发布脚本 + 读回对账；验证：测试账号小流量发布后读回状态，返回 verified/unverified/failed 之一 <!-- comet-task:5df30b6a-cc1e-4ef5-99bc-8dc77426086a -->
- [ ] 6.3 公众号发布脚本（草稿箱/发布）+ 读回对账；验证：同上 <!-- comet-task:8f0e9db9-e476-4adb-88c6-6fbc67c08ee0 -->
- [ ] 6.4 凭证加密存储模块；验证：加密落库后明文不出现在存储与日志中（测试断言） <!-- comet-task:d2c1d792-2927-4520-acd8-9e4f337761a8 -->

## 7. Web 最小界面（apps/web）

- [ ] 7.1 Next.js 初始化与审批列表/状态查看页；验证：`pnpm dev` 打开页面可见待审批项与发布状态 <!-- comet-task:2b61ca8b-bc91-407c-a8fa-f9105f2f0fa8 -->
- [ ] 7.2 审批确认动作对接执行图 resume；验证：界面确认后执行图从 interrupt 处继续 <!-- comet-task:6261e12c-f3ef-44b1-af8f-6e0d533a34c2 -->

## 8. 验证与收尾

- [ ] 8.1 单元与集成测试全量通过（执行器/频控/合规闸门/图执行/interrupt-resume/对账）；验证：测试套件全绿 <!-- comet-task:8357c148-bd8f-47e9-be35-f095eb6edfe1 -->
- [ ] 8.2 PRD 验收 A1-A6 逐条核验（测试账号小流量）；验证：每条场景有执行证据记录 <!-- comet-task:e6d0928a-5c84-4611-ad85-3ae610e63697 -->
- [ ] 8.3 测试报告与缺陷记录（test-summary / defect-log）；验证：两份文档存在且与 8.1/8.2 证据一致 <!-- comet-task:a73a7ee0-29f0-42df-8f87-852faedcc81c -->
