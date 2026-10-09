# AGENTS.md — zimeiti-ai 工程指引

> 任何 agent/开发者在本项目工作前必读。产品需求见 `docs/prd/zimeiti-ai-prd.md`。

## 一键命令（Makefile）

| 命令 | 作用 |
|---|---|
| `make dev` | 一键开发：Postgres + API(:8000) + Web(:5173)，Ctrl+C 全停 |
| `make test` | 后端测试（自动预检 Docker/PG，含真模型集成测试约 15-20s） |
| `make check` | 质量门禁五连：ruff format → ruff lint → mypy → bandit → pytest-cov(≥80%) |
| `make up` / `make install` / `make clean` | 基础设施 / 依赖安装 / 清理 |

**铁律**：每个任务收尾必须 `make check` 全绿才能提交；DB 测试前置检查已内置（conftest 等待 PG 30s）。

## 目录结构（单仓库四目录 + 基建）

```
apps/api/     后端：FastAPI + deepagents agent 运行时（src/zimeiti_api/）
  └── data/   运行时数据唯一归宿（gitignore）：audit/ credentials/ login/ state/ outputs/
apps/web/     前端：Vite + React + TS 审批页
packages/skills/   agent 技能包（预留，对齐 Easel skills 体系）
mcp/          MCP servers（预留：媒体/发布/搜索/采集）
profiles/     账号画像（YAML，人可读可版本化，进 git）
docs/         prd/ 需求文档 ｜ superpowers/plans|reports 实施计划与报告（Comet 约定目录名）
              comet/ Comet Native 运行时写的规格树（勿手工编辑）
openspec/     OpenSpec：specs/ 主规格（capability 行为契约）｜ changes/ 活跃变更 ｜ changes/archive/ 归档
.comet/ .codebuddy/ scripts/  工作流运行时 / agent 技能与命令 / 工程脚本
```

## 工程约定

1. **变更工作流**：Comet Classic 五阶段（open→design→build→verify→archive），用 `/comet-open` 开新变更；禁跳过工件直接写代码
2. **TDD**：先写失败测试（RED）再实现（GREEN），测试是可执行需求
3. **门禁**：`make check` 五项全绿；覆盖率 ≥80%
4. **宪法级红线**：发布前人工审批（HITL 不可关）；凭证只存密文；平台操作带频控/白名单；出站内容过 fail-closed 合规闸门；发布结果读回对账，未核实不报成功
5. **配置**：一切路径/密钥经 `src/zimeiti_api/config.py`（环境变量可覆盖，绝对锚定不依赖 cwd）
6. **已知遗留**（详见归档 design.md）：API 审批端点 profile 硬编码 xhs-main（接 gzh 前修）；发布读回恒 unverified（真实平台脚本在 real-account-verification 变更落地）

## 开发铁律（永远遵守，违反即返工）

> 以下原则由 2026-10-09 xhs 真账号走查的实战教训固化，Comet 项目记忆同步存档（constraint 类型，slug: memo-53b2924c / memo-1f7b8eec / memo-262993fa）。

1. **永远不要重复造轮子**：任何新功能实现前，必须先完成现成方案调研——顺序：本项目其他模块 → 本地兄弟项目（my-tools/xiaobei/Easel 等）→ GitHub 活跃维护的开源项目（按最近提交时间与真实用户量判断活跃度，clone 读源码验证，不轻信 README）。存在成熟实现时必须复用/接入/照抄，禁止自研已有成熟实现的部分。整段复用时**连结果判定、错误处理一起照抄**，禁止自造判定条件或"改良"上游逻辑。
2. **零假阳性**：平台/服务返回 success ≠ 真实成功。一切对外写入操作（发布/提交/上传）必须有独立读回验证（readback）或服务端证据；验证不过一律降级 unverified/失败，禁止冒报成功。
3. **失败先归因后动手**：禁止直接打补丁。流程：取证（抓包/截图/日志）→ 最小复现 → 根因定位 → 修复方案 → 举一反三审计同类问题。参考项目解决不了的，先怀疑自己是否漏看了它的机制，再怀疑站点改版。
4. **引用注明出处**：接入/借鉴外部代码时注明来源（项目 + 文件 + 符号）；自研与照抄的边界必须清晰可审计。
5. **调研先行**：动手写第一行实现代码之前，调研结论（候选项目、对比、选型理由）先落盘成文并经确认。
