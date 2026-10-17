# Zimeiti AI — 你的 AI 自媒体人

单用户本地工作台：一个装备完整的 AI agent 驱动你的自媒体运营——**热点 → 收藏为选题 → 一键排期 → 对话创作 → 内容库 → 发布**。选题与创作严格同源，所有产物落盘可查。

> Agent harness 对齐 OpenClaw：真实文件系统、五层技能路由、白名单脚本执行、跨会话记忆、付费操作确认（HITL）、模型故障自愈、多 key 轮换、定时自动化、行为回归兜底。

## 功能总览

### 产品页面（Web）

| 页面 | 能做什么 |
|---|---|
| 工作台 | 今日热点 + 概览统计 + 用量卡片（token 与折算金额） |
| 热点雷达 | 抓取 AI 领域热点，一键收藏为选题 |
| 选题库 | 选题全生命周期：新建 / 编辑 / 排期 / 删除 |
| 内容日历 | 按周排期，选题到日 |
| 对话 | 与 agent 对话创作；会话管理；付费操作先确认 |
| 内容库 | 所有 AI 产物自动归档：稿件在线预览、素材查看、一键上传公众号草稿箱 |
| 账号 | 公众号等平台登录态管理，whoami 自检 |
| 自动化 | 定时任务：新建 / 启停 / 立即执行 / 执行记录；任务存 PG，重启不丢 |
| 设置 | 模型通道（多 key / fallback 链 / 子代理模型只读展示）+ 会话用量明细 |

### Agent 能力面

- **真实文件系统**：在 `outputs/`、`profiles/`、`skills/` 上做六件套文件操作，产物直接落盘
- **五层技能路由**：113 个技能目录自动注入索引，按「详细技能 → 场景包 → 层 → 通用」链路路由
- **白名单脚本执行**：`exec_script` 只跑注册表内脚本（6 个运营脚本），拒绝一切注入
- **跨会话记忆**：`memory_record` / `memory_search` 带溯源分级（owner/agent/system），compaction 前自动保底
- **付费操作确认**：付费媒体生成等先经 `ask_human` 或正文征询，**确认前不发起调用**；没有单价数据不编造金额
- **模型韧性**：连接错误/限流/5xx 自动切换——多 key 先轮换（`ZIMEITI_API_KEYS`），key 用尽再切备用模型（`ZIMEITI_FALLBACK_MODELS`，支持 `模型名@base_url` 跨厂商）；4xx（配置错误）直抛不掩盖
- **专属子代理**：`research`（只读，拒一切写）/ `draft`（仅放行 `outputs/`），可用便宜模型降档（`ZIMEITI_SUBAGENT_MODEL`）
- **结构化输出**：按 schema 建独立 graph（如选题六维评估），主对话不受约束
- **定时自动化**：case（跑运营脚本）/ prompt（走对话链路）两类任务，分钟级调度、执行租约防竞态、日志落 `outputs/_automations/`
- **用量统计**：按会话/模型记 token，有单价的模型折算金额（`≈ $0.0034`），无单价的如实标注

## Demo 展示

全部为真实界面 + 真实 LLM 录制（Playwright 驱动，可见虚拟光标 + 中文步骤横幅），
详见 [docs/demo/README.md](docs/demo/README.md)：

| 视频 | 内容 | 时长 |
|---|---|---|
| [brand-demo.mp4](docs/demo/brand-demo.mp4) | **品牌运营全流程**：热点收藏 → 排期 → 「做内容」对话创作 → 内容库 → 公众号草稿 | 3'26" |
| [01-profile-wizard.mp4](docs/demo/01-profile-wizard.mp4) | 首次使用：画像向导四步 | 36" |
| [02-chat-sessions.mp4](docs/demo/02-chat-sessions.mp4) | 对话创作与会话管理 | 1'04" |
| [03-ideas-crud.mp4](docs/demo/03-ideas-crud.mp4) | 选题库生命周期 | 32" |
| [04-outputs-browse.mp4](docs/demo/04-outputs-browse.mp4) | 内容库浏览与预览 | 18" |
| [05-automations-usage.mp4](docs/demo/05-automations-usage.mp4) | 定时自动化与用量统计 | ~40" |

## 快速开始

前置：Python 3.11+、Node 18+、[uv](https://docs.astral.sh/uv/)、Docker（PostgreSQL）。

```bash
# 1) 起 PostgreSQL（库名/账号见 apps/api/.env）
docker run -d --name zimeiti-postgres -p 5432:5432 \
  -e POSTGRES_USER=zimeiti -e POSTGRES_PASSWORD=zimeiti -e POSTGRES_DB=zimeiti-ai postgres:16

# 2) 配置模型通道
cp apps/api/.env apps/api/.env.local  # 或直接编辑 .env
#   必填：OPENAI_API_KEY（或 ZIMEITI_API_KEYS 多 key）
#   可选：OPENAI_BASE_URL / OPENAI_MODEL / ZIMEITI_FALLBACK_MODELS

# 3) 安装依赖 + 双端启动（API :8000 托管前端构建产物）
make install
make dev          # 或分开跑 make api / make web

# 4) 打开 http://localhost:8000（生产形态）或 :5173（前端 dev 热更）
```

无 `.env` / 无密钥时应用照常启动，对话优雅降级并如实提示——其余页面功能不受影响。

### 故障排查

**页面报「服务返回了 HTML 而非 JSON」**：API 请求没到后端——多半是 dev 代理失效
（`/api/*` 落进 vite 的 SPA 兜底返回了 index.html），或前后端版本不一致。

1. 自查：`curl http://localhost:8000/api/status` ——返回 JSON 说明后端正常，问题在前端链路
2. 处置：重启 `make dev`（vite 代理失效只能靠重启恢复）；或直接用生产形态 `http://localhost:8000`（后端托管前端构建产物，无代理层）

**页面报「后端代码已变更……请重启后端」**：后端进程启动后源码发生过变更
（重构移动了模块 / `git pull` 更新了代码）——长跑进程里的懒加载会按磁盘路径
找不到已移动的模块。**处置：重启后端**（Ctrl+C 后重新 `make api` / `make dev`）。
这是守卫给出的可行动错误，替代了原先的 `No module named ...` 天书。

### 环境变量

| 变量 | 作用 |
|---|---|
| `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `OPENAI_MODEL` | 主模型通道 |
| `ZIMEITI_API_KEYS` | 逗号分隔多 key——限流先换 key，key 用尽才切模型 |
| `ZIMEITI_FALLBACK_MODELS` | 备用模型链，`模型名@base_url` 支持跨厂商 |
| `ZIMEITI_EXPLICIT_MODEL` | 用户在设置里显式选择的模型；设 1 时严格不降级 |
| `ZIMEITI_SUBAGENT_MODEL` / `ZIMEITI_SUBAGENT_ENABLED` | 子代理模型降档 / 总开关 |
| `DATABASE_URL` | PostgreSQL 连接串（会话持久化/记忆/自动化/用量） |

## 测试与质量

```bash
make check         # 质量门禁五连：format → lint → types → security → tests(229)+coverage≥80
make evals         # agent 行为回归：5 条真实 LLM 探针（路由/付费门/记忆/fallback）；无密钥自动跳过
make e2e-browser   # 浏览器级双端对齐 E2E：12 场景 63 项（--scenarios S11 --target zimeiti 可选）
make verify        # openclaw 对齐归零脚本 + 技能校验 + skill 测试套件
```

E2E 双端对齐：zimeiti 与 easel 两个前端逐场景比对行为，差异要么归零、要么登记为预期 NOTE。

## 项目结构

```
apps/
  api/            FastAPI 后端（zimeiti_api/）
    runtime/        agent 装配：模型 fallback、子代理、结构化、白名单脚本
    memory/         跨会话记忆（溯源分级、注入去重）
    automations/    定时任务（调度器/存储/执行链路）
    content/        热点/选题/技能目录/画像
    governance/     付费门与确认链路
    platforms/      平台对接（公众号等）
  web/            React 前端（构建产物由 API 托管）
  e2e/            浏览器级双端 E2E（12 场景 + parity + coverage_map）
  scripts/        运营脚本与 demo 录制
  profiles/       用户画像（每账号一目录）
  outputs/        AI 产物落盘（内容库）
  skills/         五层技能库
docs/
  demo/           录制好的用户路径视频
  openspec/       规格与变更档案（specs 为主，changes/archive 为归档）
```

## 开发工作流

需求走 OpenSpec：`proposal → spec → design → tasks`，实现走 comet 全流程
（open → design → build(TDD) → verify → archive），每个变更留验证报告。
质量门禁 `make check` 是合入的硬前提；agent 行为靠 `make evals` 回归兜底。

## License

私有项目，未授权分发。
