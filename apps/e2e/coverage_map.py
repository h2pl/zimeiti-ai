"""API 路径簇 → 浏览器场景映射（运行末打印）。

有 UI 入口的路径 → 场景覆盖；无 UI 入口的路径 → 显式登记由 API 级
parity（apps/scripts/e2e_parity_check.py，57 项）覆盖。
"""

COVERAGE_MAP = {
    "GET /api/status": "S1/S2",
    "GET /api/trends（外部数据源）": "S10（条件断言）",
    "POST/GET/PUT/DELETE /api/ideas": "S3",
    "POST/GET/DELETE /api/schedule": "S4",
    "POST /api/chat/stream（SSE，mock LLM）+ 会话管理": "S5",
    "GET /api/personas + 画像创建（mock LLM 增强）/删除": "S7",
    "GET /api/outputs + GET /api/output/{path}": "S6",
    "GET /api/accounts/{platform}/whoami": "S8",
    "GET /api/env + 设置面板模型通道": "S9",
    "GET /api/upload/limits": "S5（上传面板挂载即取）",
    "POST /api/upload*": "无浏览器旅程（文件选择器原生对话框）→ API parity 覆盖",
    "POST /api/chat/question/*（HITL 问答）": "依赖中断注入 → API parity 覆盖",
    "login/publish/wechat/analytics（平台扫码与发布后端）": "无浏览器旅程（外部平台凭据）→ API parity 覆盖",
    "skills 执行 / profile-build 深链": "S7 覆盖画像向导链路；技能执行为后台任务 → API parity 覆盖",
    "POST/GET/PATCH/DELETE /api/automations* + run-now": "S11",
    "GET /api/usage + 工作台/设置用量卡片": "S12",
    "/api/flows CRUD + /api/flows/runs + /api/autonomous/status + 自主运营页": "S13",
    "memory_record/search（跨会话记忆）": "无独立 UI（agent 工具）→ evals 行为层 test_04 覆盖",
    "exec_script（白名单脚本）": "无独立 UI（agent 工具）→ evals 行为层 + 单测覆盖",
    "模型 fallback / key 轮换": "运行时机制（无 UI）→ 单测 + evals 行为层 test_05 覆盖",
    "子代理 task / 结构化输出": "运行时机制（无 UI）→ 单测 + 探针覆盖",
}
