# gate-compliance 任务清单

## 1. 工具链与门禁入口

- [x] 1.1 pyproject dev 依赖补 ruff/mypy/bandit/pytest-cov，`uv sync --all-extras` 安装 <!-- comet-task:319792ec-d200-4b90-97db-6dcefcca39bc -->
- [x] 1.2 Makefile 新增 `check` 目标：ruff format → ruff lint → mypy → bandit → pytest+cov≥80（PYTHONUTF8=1） <!-- comet-task:32f90596-b018-415f-a712-36ebb19a9b6d -->
- [x] 1.3 ruff format 全量重整（apps/api 源码与测试） <!-- comet-task:1ed92e66-64a6-4033-be1d-44796b9b0deb -->

## 2. 静态门禁清零

- [x] 2.1 ruff lint 错误清零（含 app.py 与 zimeiti_api 全包） <!-- comet-task:e218d1fd-512d-4c94-8d51-c6a2a9ad12bd -->
- [x] 2.2 bandit 扫描通过（-s B101 + subprocess 类告警定点 nosec 注明理由） <!-- comet-task:acacbb63-d984-4b89-a166-1bcbd82a0fc1 -->
- [x] 2.3 mypy 通过（check_untyped_defs + ignore_missing_imports 起步，逐文件收敛至零错误） <!-- comet-task:d64c1b41-b3f2-43ba-a3ea-82fd9de33701 -->

## 3. 测试扩充（cov ≥80%）

- [x] 3.1 conftest 完善：PG 测试库 + TestClient（TrustedHost 兼容）+ 事件循环策略 fixture <!-- comet-task:073f80d5-fba1-441b-8a11-f69812fa08b7 -->
- [x] 3.2 core 域测试：pg（扩展现有 12 项）、paths（路径安全函数）、settings、dotenv、timeouts <!-- comet-task:7b396cc1-2b82-46bc-a94e-0ff095699533 -->
- [x] 3.3 governance 域测试：guard 中间件（写保护/TrustedHost/origin） <!-- comet-task:b7a9146a-8803-49cd-bb0a-4a69c93d1c4f -->
- [x] 3.4 content 域测试：ideas/schedule/outputs/uploads/skills/trends 路由 CRUD（PG fixture）+ personas/persona_core <!-- comet-task:139c65e1-8cf9-46f1-b1b1-3df3c0aa14ec -->
- [x] 3.5 platforms 域测试：accounts/analytics/login/publish/wechat 路由契约（mock subprocess/httpx/Playwright） <!-- comet-task:be5cc642-c7c7-4618-88da-14c71c724329 -->
- [x] 3.6 operations 域测试：env/models 设置面板路由（ENV_FILE fixture） <!-- comet-task:53cc1145-6812-41d5-91c6-b073d293e56c -->
- [x] 3.7 runtime 域测试：status 全覆盖 + chat 契约（monkeypatch agent_runtime）+ agent_runtime 配置分支 <!-- comet-task:5894b42f-90c4-4095-8687-ce52e369a78a -->
- [x] 3.8 覆盖率迭代至 ≥80%，对真正无法离线到达的行定点 pragma（注明理由） <!-- comet-task:2ec720c9-7d3e-44ae-a517-6abb7578f9c4 -->

## 4. 验证与收尾

- [x] 4.1 `make check` 全绿 <!-- comet-task:d4d1864e-e0e1-40e2-baa3-1f4b4ec522ff -->
- [x] 4.2 行为零回归：verify_openclaw_removal PASS（52 api routes）+ verify_pg_data_layer restart 4/4 <!-- comet-task:55a4c116-3a07-419c-8c35-cf9ec7a653d5 -->
- [x] 4.3 双服务 E2E 抽查：e2e_parity_check 与 Easel 全部一致 <!-- comet-task:e5320eb3-1fe0-4265-b7d6-c9d82c99f739 -->
- [x] 4.4 提交（b6f1e26）；独立验收与归档即 verify/archive 阶段本体 <!-- comet-task:52e7595e-e912-4aea-b4fa-56d0a5690a1e -->
