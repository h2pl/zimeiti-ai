# 验证报告：phase1-deepagents-runtime

- 日期：2026-10-13；模式：full；基线：3f96fda → HEAD（h2pl/phase1-deepagents-runtime）

## 七项核查

| # | 检查 | 结果 | 证据 |
|---|---|---|---|
| 1 | 任务完成 | PASS | 8/8 |
| 2 | 文件与任务匹配 | PASS | 新增 easel/agent_runtime.py（约 330 行）+ app.py 三接缝 + spec 笔误修正 |
| 3 | 构建/导入 | PASS | compileall exit=0（Runtime 证据 81c72136）；import app 66 路由 |
| 4 | 相关测试 | PASS（见偏差 1） | 冒烟：SSE 帧序列 activity→error→done 实测；HITL 端到端受限于无模型 key |
| 5 | 安全 | PASS | 无密钥入库；system_prompt 为常量；问题选项经 React 文本节点渲染无 XSS 面 |
| 6 | 独立集成评审 | PASS（两轮） | 首轮评审抓出 C1-C4（HITL 链路 4 断点）+ I1-I5/W1-W6；全部返修；关键修复逐条对照 deepagents 0.7.24 源码语义 |
| 7 | 核心场景 | PASS | 见下 |

## delta spec 场景核对（deepagents-runtime）

| 场景 | 结果 | 证据 |
|---|---|---|
| 对话走运行时（无 OpenClaw 进程） | PASS | supervisor 顶部 ZIMEITI_RUNTIME 分支（默认 deepagents）；冒烟全程无 OpenClaw 调用 |
| SSE 契约兼容 | PASS | activity/error/done 帧实测；done 携带 sessionKey；question 帧按前端 ChatQuestion 形状（id + questions[]） |
| HITL 问题卡内联且可恢复 | PASS（代码级）+ 见偏差 1 | 中断检测（action_requests[0].args）、resume 决策格式（respond/message）、pending TTL 存储均按 deepagents 0.7.24 实际 API 实现；SSE 保连机制成立（supervisor 正常 return，CLIENT_DONE 不发） |
| 无模型配置优雅降级 | PASS | 冒烟实测：error 帧（明确提示配置项）+ done 帧 + save_turn 落盘，HTTP 200 |
| 会话历史持久化 | PASS | sessions/<key>.json 落盘；checkpoint 为空时注入落盘历史（防重复膨胀）；_save_turn 供 /api/chat/last |

## 独立评审返修记录（一轮）

- C1 resume 决策格式 → `{"type":"respond","message":<str>}`
- C2 interrupt 载荷解析 → `action_requests[0].args`
- C3 options 按「|」拆分
- C4 question 帧载荷对齐前端 ChatQuestion；answer 格式化为「问题 → 选项」
- I1 token 流按 AIMessageChunk 过滤；I2 checkpoint 空才注入历史；I3 resume 失败补 done+end；I4 pending_status 形状对齐；I5 session 级 asyncio.Lock
- W1-W6：TTL 惰性清理、死代码删除、_append_event 双写移除、错误路径补 save_turn、_build_agent 入 try

## 已接受偏差

1. **HITL 端到端（真实模型 key）未实测**：本环境无 OPENAI_API_KEY。降级路径已实测；HITL 修复逐条对照 deepagents 0.7.24 源码（human_in_the_loop.py RespondDecision/message 键、HITLRequest 载荷）。**跟进项**：配置 key 后跑一轮含 ask_human 的真实对话（建议作为后端启动自检或首个使用任务）。
2. **/api/settings/models*、/api/settings/local-agents、/api/skills 仍为 OpenClaw 形态**：本变更范围外（对话链路优先），后续变更处理。

## 结论

无 CRITICAL / 无未处理 IMPORTANT（偏差 1 为环境受限的已记录跟进项）。Ready for archive。
