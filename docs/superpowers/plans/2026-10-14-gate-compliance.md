---
change: gate-compliance
design-doc: docs/openspec/changes/gate-compliance/design.md
base-ref: 485670448f4f2bf5b2b34368e06362fb30fd98bd
---

# gate-compliance 实施计划

策略：autonomous + tdd + standard。行为零回归为硬约束——每个阶段收尾跑 `verify_openclaw_removal.py`（52 api routes）作为回归锚。测试是主要工作量，按域迭代、每域一文件、外部边界全 mock。

<!-- comet-task-authority: docs/openspec/changes/gate-compliance/tasks.md -->

## 1. 工具链与门禁入口

<!-- comet-task-ref:319792ec-d200-4b90-97db-6dcefcca39bc -->
- **1.1 dev 依赖**：pyproject `[project.optional-dependencies].dev` 补 `ruff>=0.6`、`mypy>=1.10`、`bandit>=1.7`、`pytest-cov>=5`；`uv sync --all-extras`。
  - RED：`uv run python -m mypy --version` 报 No module → GREEN：版本号输出。
  - 验收：四工具 `--version` 全部可执行。

<!-- comet-task-ref:32f90596-b018-415f-a712-36ebb19a9b6d -->
- **1.2 Makefile `check`**：五步串行（ruff format src+tests → ruff check → mypy → bandit → pytest --cov --cov-fail-under=80），全部 `PYTHONUTF8=1`，`set -e` 语义（make 天然逐命令失败即停）。
  - RED：目标缺失。GREEN：`make check` 可执行（允许此时报告格式/lint 问题）。

<!-- comet-task-ref:1ed92e66-64a6-4033-be1d-44796b9b0deb -->
- **1.3 ruff format**：`uv run ruff format app.py zimeiti_api tests`，diff 后跑 import app + pytest 确认零行为变化。

## 2. 静态门禁清零

<!-- comet-task-ref:e218d1fd-512d-4c94-8d51-c6a2a9ad12bd -->
- **2.1 ruff lint 清零**：`ruff check --fix` 自动修 + 手工逐条处理残余；含 app.py。验收：`ruff check app.py zimeiti_api tests` 零输出。

<!-- comet-task-ref:acacbb63-d984-4b89-a166-1bcbd82a0fc1 -->
- **2.2 bandit**：`bandit -q -r zimeiti_api`（-ll 仅中高危起步）+ tests 用 assert 属测试常态，pytest 文件不进 bandit 范围；subprocess/临时文件类告警逐条评估：产品行为（登录子进程）→ 定点 `# nosec B603` 注明理由，真风险 → 修。

<!-- comet-task-ref:d64c1b41-b3f2-43ba-a3ea-82fd9de33701 -->
- **2.3 mypy**：pyproject `[tool.mypy]`：`check_untyped_defs=true`、`ignore_missing_imports=true`、`exclude` 无。逐文件收敛至 `mypy zimeiti_api app.py` 零错误（类型标注按需补、不可达复杂处定点 `# type: ignore[<code>]` 注明理由）。

## 3. 测试扩充（cov ≥80%）

<!-- comet-task-ref:073f80d5-fba1-441b-8a11-f69812fa08b533 -->
- **3.1 conftest**：保留 PG 库/uid 租户 fixture；新增 `client` fixture（TestClient base_url=`http://127.0.0.1` 过 TrustedHost）；`pytest.ini` 或 pyproject 配 coverage。
  - RED：`pytest --cov` 报告覆盖率基线（预计 <30%）。

<!-- comet-task-ref:7b396cc1-2b82-46bc-a94e-0ff095699533 -->
- **3.2 core 域**：test_core_pg.py（扩展：connect/pending/ideas/schedule 边界）、test_core_paths.py（路径安全函数穿越/403/404/下沉常量）、test_core_settings.py（guard/mask/ssrf/model spec）、test_core_dotenv.py、test_core_timeouts.py。

<!-- comet-task-ref:b7a9146a-8803-49cd-bb0a-4a69c93d1c4f -->
- **3.3 governance 域**：test_governance_guard.py（写保护规则、origin/Host 校验、_EXTRA_HOSTS）。

<!-- comet-task-ref:139c65e1-8cf9-46f1-b1b1-3df3c0aa14ec -->
- **3.4 content 域**：test_content_*.py——ideas/schedule CRUD（PG）、outputs 列表/文件/删除（OUTPUTS_DIR fixture 树）、uploads（上传/保护目录）、skills（目录枚举 mock）、trends（httpx mock）、personas/persona_core（PROFILES_DIR fixture 树）。

<!-- comet-task-ref:be5cc642-c7c7-4618-88da-14c71c724329 -->
- **3.5 platforms 域**：test_platforms_*.py——accounts/login/publish/wechat/analytics 路由契约；subprocess/httpx 全 monkeypatch；状态端点（未登录 404/200 结构）优先。

<!-- comet-task-ref:53cc1145-6812-41d5-91c6-b073d293e56c -->
- **3.6 operations 域**：test_operations_env/models.py——ENV_FILE fixture（临时 env 文件）、models 的渠道 spec/mask 逻辑。

<!-- comet-task-ref:5894b42f-90c4-4095-8687-ce52e369a78a -->
- **3.7 runtime 域**：test_runtime_status.py（全覆盖）；test_runtime_chat.py（monkeypatch agent_runtime.ask/run_turn 假实现，验证路由契约与持久化）；test_runtime_agent_runtime.py（_build_model/model_configured 等配置分支）。

<!-- comet-task-ref:2ec720c9-7d3e-44ae-a517-6abb7578f9c4 -->
- **3.8 覆盖率收敛**：`pytest --cov-report=term-missing` 逐文件补缺口至 ≥80%；仅对真实无法离线到达的行加 `# pragma: no cover` 并注明。

## 4. 验证与收尾

<!-- comet-task-ref:d4d1864e-e0e1-40e2-baa3-1f4b4ec522ff -->
- **4.1** `make check` 全绿（RED→GREEN 的最终 GREEN 即本任务验收）。

<!-- comet-task-ref:55a4c116-3a07-419c-8c35-cf9ec7a653d5 -->
- **4.2** 行为零回归：verify_openclaw_removal PASS；verify_pg_data_layer restart 4/4。

<!-- comet-task-ref:e5320eb3-1fe0-4265-b7d6-c9d82c99f739 -->
- **4.3** 双服务 E2E：e2e_parity_check 与 Easel 全部一致（57 项）。

<!-- comet-task-ref:52e7595e-e912-4aea-b4fa-56d0a5690a1e -->
- **4.4** 提交 → guard build → verify 阶段（独立验收）→ 归档。

## 回归与回滚

- 每阶段后跑 `verify_openclaw_removal.py`；行为变化即回滚该阶段（git 按 task 分组提交）。
- coverage 中途任何时点低于改造前基线且无法短期修复 → 停下诊断，不带病推进。
