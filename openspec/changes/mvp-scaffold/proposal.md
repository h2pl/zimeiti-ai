# Why

自媒体内容运营（选题→写文案→多平台发布→互动）每周占用大量重复劳动，现有方式是零散工具（ChatGPT 写文案 + 平台后台手动发），链路不打通、无沉淀、无自动化。LLM 能力、skills/MCP 生态与两个可参考的开源项目（Easel、xiaobei）均已成熟，现在具备用 agent 替代执行的条件。需求详情见 `docs/prd/zimeiti-ai-prd.md`（北极星指标：每周运营时间节省）。

# What Changes

- 新建 zimeiti-ai 最小闭环骨架：**选题 → 图文创作 → 双平台（小红书 + 公众号）发布**，含发布前人工审批（HITL）与发布结果读回对账
- 建立单仓库四目录工程结构：`apps/api`（后端服务与 agent 运行时）、`apps/web`（工作台/审批界面）、`packages/skills`、`mcp/`（占位）
- 建立账号画像机制（小红书 + 公众号两账号的定位/风格/受众配置，驱动创作）
- 建立托管循环骨架：定时/事件触发的最小自治执行图（执行状态持久化、断点可恢复），审批点外自动运行
- 建立基础设施：docker-compose（Postgres + pgvector）、凭证加密存储设施

# Capabilities

## New Capabilities

- `account-profile`: 账号画像的配置、存储与创作时注入——定位/风格/受众/平台规则/偏好红线，作为个性化创作的依据
- `topic-discovery`: 选题辅助——热点/竞品信息输入 → 产出选题卡（含推荐理由），由人工挑选进入创作
- `content-creation`: 图文创作——基于选定选题与账号画像，产出小红书笔记草稿与公众号文章草稿（含封面文案），风格符合画像
- `platform-publishing`: 平台发布——发布前 HITL 审批、自动化发布到小红书与公众号、读回对账（verified/unverified/failed 档位，未核实不报成功）
- `hosted-loop`: 托管循环——定时/事件触发的最小自治执行图，审批点自动阻断等待人工确认，状态可恢复

## Modified Capabilities

（无——首版新建，尚无既有 capability）

# Impact

- 全新代码库：`apps/api`、`apps/web`、`packages/skills`、`mcp/`、`docker-compose.yml`
- 外部依赖：Playwright + Chromium（平台发布自动化）、Postgres + pgvector、LLM 网关（LiteLLM，含百炼/DeepSeek 等国内可达 provider）
- 平台风控面：小红书/公众号自动化发布属风控敏感操作，实现必须内置宪法原则 III 的护栏（频控/白名单/禁伪造登录态）与原则 I 的发布前 HITL
- 不影响：无既有系统（首个变更）
