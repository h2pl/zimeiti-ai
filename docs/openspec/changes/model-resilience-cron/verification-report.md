---
comet_change: model-resilience-cron
---

# 验证报告：model-resilience-cron（模型韧性与定时自动化）

## Spec 场景逐条核对

| Requirement / Scenario | 结果 | 证据 |
|---|---|---|
| 模型 fallback —— 主模型故障自动切换 | ✅ | 端到端探针：主模型指向坏端点（127.0.0.1:59999）→ 日志 `[model-fallback] 主模型 deepseek-chat 失败（OpenAIConnectionError），切换第 1 个备用模型` → 备用 DeepSeek 正常回复「收到收到」，全程 14s |
| 模型 fallback —— 明示选择不降级 | ✅ | 单测 + `ZIMEITI_EXPLICIT_MODEL` 分支（仅返回主模型，不包装） |
| 模型 fallback —— 4xx 不切换 | ✅ | 单测 `test_no_switch_on_4xx`（401 直抛，备用模型不被调用） |
| 定时自动化 —— 每日定时出稿 | ✅ | 探针：创建 08:00 case 任务 → next_run 已算；手动后台触发 → automation_runs 出现记录 |
| 定时自动化 —— 重启后任务仍在 | ✅ | 探针：创建 → 杀进程重启 → 列表仍含该任务（PG 持久化 + next_run 持久化） |
| 用量统计 —— 查询会话用量 | ✅ | 探针：`/api/usage` 返回 prompt 12587 / completion 1 token（模型名兜底为主模型名） |

## 关键实现发现（值得记录）

1. **FallbackChatModel 必须是 `BaseChatModel` 子类**：deepagents `resolve_model` 按
   `isinstance(model, BaseChatModel)` 分发，非子类会被当作 `"provider:model"` 字符串
   spec 走 `init_chat_model` 而崩溃（实测）。
2. **fallback 必须落在 private impl**：langchain 真实调用路径是 `_astream/_agenerate/
   _generate`，公开 `astream/invoke` 覆写不会被走到（实测：只覆写公开方法时切换不触发）。
3. **产物类型契约**：`_astream` 须产出 `ChatGenerationChunk`（子模型公开 astream 给的是
   `AIMessageChunk`），`_agenerate` 须返回 `ChatResult`——否则下游 `chunk.message` /
   `generation_info` 访问即 AttributeError（实测并修复）。
4. **bind_tools 必须整链绑定**，否则工具绑定后 fallback 语义丢失。
5. **跨厂商 fallback 需 `模型名@base_url`**：同凭据切换只对「同厂商换模型」有意义。

## 自动化验证

- **单测**：`tests/test_model_fallback.py` 7 项 + `tests/test_automations.py` 4 项 RED→GREEN
- **全量测试**：191 passed
- **`make check`**：全绿（exit 0，经 comet check run 登记）
- **浏览器 E2E S05**：8/8 通过、双端差异 0

## 结论

主模型故障不再中断对话；定时任务持久化可重启；用量首次可查。**建议通过。**
