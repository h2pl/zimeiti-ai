---
comet_change: api-error-clarity
---

# 验证报告：api-error-clarity（API 非 JSON 响应可读报错）

## 用户报障根因（取证记录）

| 步骤 | 结果 |
|---|---|
| `curl :8000/api/usage` | 正常 JSON → **后端无恙** |
| `curl :5173/api/usage`（运行中的 vite） | `<!doctype html>` → 代理未生效 |
| 全新起 vite（:5199，同一配置文件） | 正常 JSON → 配置本身正确 |
| 结论 | 运行中 dev 实例的坏状态；`request()` 对「200+HTML」抛原始异常放大了排查成本 |

## Spec 场景核对

| Scenario | 结果 | 证据 |
|---|---|---|
| 代理失效返回 HTML → 可行动错误 | ✅ | 探针（route 注入 `<!doctype html>` 到 /api/usage）：卡片显示「用量加载失败：服务返回了 HTML 而非 JSON（/api/usage?days=30）——API 代理/后端未就绪，或前后端版本不一致。请重启 make dev（或改用 http://localhost:8000 生产形态）后刷新页面。」三要素断言（含 HTML 描述/无原始异常/含重启指引）全 PASS |
| 正常 JSON 不受影响 | ✅ | 58 个调用点走原路径；make check 229 passed；E2E 全量 63/63（见下） |

## 自动化验证

- **探针**：`apps/scripts/probe_api_error.py` PASS（三断言）
- **tsc + vite build**：通过
- **make check**：exit 0，229 passed（后端零改动，确认无回归）
- **E2E 全量**：63/63、双端差异 0（修复不影响正常链路）
- **端点面核查**：SSE（chat/stream 用 getReader）与文件预览/下载不经 `request()`，无误杀面

## 过程发现

- 探针首版 FAIL 的时序坑已记录：工作台是默认页，首次 fetch 早于 route 注册，
  探针需在注册后 `reload` 才能命中拦截——已写进脚本注释。

## 遗留说明（非本变更范围）

- 用户当前运行中的 vite（:5173）仍是坏状态——**重启 make dev 即恢复**；
  修复后即使再遇到同类故障，界面给出的是可行动指引而非原始异常。
