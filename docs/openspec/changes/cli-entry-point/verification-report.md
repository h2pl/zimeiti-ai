---
comet_change: cli-entry-point
---

# 验证报告：cli-entry-point（命令行入口）

## Spec 场景核对

| Scenario | 结果 | 证据 |
|---|---|---|
| 流式对话（token 逐段打印） | ✅（单测层） | `test_sse_parses_frames`（token/activity/error/[DONE] 帧解析）；`_cmd_chat` 帧分发；真实 LLM 对话未跑（成本纪律，留用户首次使用） |
| 服务不可达 → 可行动错误 + 非 0 退出 | ✅ | 单测 `test_exit_code_contract`（stderr 含「无法连接」+「make api」）；探针直连 `127.0.0.1:9` 实测退出码 1 |
| flows 新建后列表可见 | ✅ | 探针：`flows new` 回显 id → `flows` 列表含中文步骤徽标（发现/选题） |
| 执行记录逐步可见 | ✅ | 探针 `runs` 输出含步骤级状态；路由修复后才真正可用（见下） |
| flows run 明示成本 | ✅ | `fr.add_argument` help 文本「会真实消耗模型额度」；README 同步 |
| `--help` 列出子命令 | ✅ | 探针断言 chat/flows/runs/usage 均在帮助输出中 |

## 探针抓出的两个真 bug（本变更最重要的产出）

### 1. `--base` 位置限制
`zimeiti runs --base X` 报 `unrecognized arguments`——argparse 要求全局参数在
子命令前。修：common 父解析器 + `default=SUPPRESS`（子命令未指定时不覆盖顶层
值）。三种写法（前/后/缺省）均有测试固化（`test_base_accepts_both_positions`）。

### 2. `/api/flows/runs` 被动态路由吞掉（既有缺陷，autonomous ①④ 留下）
`/api/flows/{flow_id}` 注册在 `/api/flows/runs` 与 `/api/flows/steps/catalog`
**之前**——FastAPI 按注册顺序匹配，两个静态路由永远 404「流程不存在」。
**Web 页面的 `.catch(() => [])` 静默吞掉了这个错误**，所以「最近执行」面板
从 autonomous-observability 上线起就从未显示过数据，E2E 也因容错而全绿。

修：静态路由提前 + 新增 `tests/test_route_ordering.py` 遮蔽守卫。**牙齿已验证**：
把路由改回旧顺序，守卫当即报红（`GET /api/flows/runs 被更早注册的
GET /api/flows/{flow_id} 遮蔽`）；清 `__pycache__` 后复测确认（首次验证受
pyc 缓存干扰出现「漏报」假象，已排除）。

## 自动化验证

- **单测 10 项**（客户端错误翻译/连接失败指引/SSE 帧/命令树/参数解析/退出码/
  --base 位置/路由守卫）
- **端到端探针 PASS**（真实服务 + 真实 CLI 子进程）：--help / 连接失败退出码 1 /
  flows 新建→列表→删除 / runs / usage；**刻意不跑 chat 与 flows run**（真实消耗）
- **make check**：exit 0，**278 passed**（bandit B310 对 `urllib.urlopen` 按仓库
  既有 nosec 范式豁免并注明理由——本地 CLI 连用户指定后端，非网络输入面）
- **E2E 全量**：13 场景 **69/69**、双端差异 0（路由顺序修复后无回归）
- 连带：补提交此前漏 add 的 `probe_autonomous_guardrails.py`

## 已知边界

- `chat` 的**真实 LLM 端到端**未在探针中执行（成本纪律）——SSE 帧解析与错误
  分发有单测覆盖，首次真实对话留待用户验证
- 交互式 REPL、IM 通道均不在本变更范围（后者用户已确认先不做）
