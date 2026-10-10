@echo off
REM zimeiti-ai 托管循环每日触发入口（Windows 计划任务调用）。
REM 触发各账号一轮「选题→创作」，中断在人工闸门等待审批（Web 审批页确认后发布）。
REM 依赖：uv 在系统 PATH；DEEPSEEK_API_KEY 在 apps/api/.env；Postgres 运行中。
REM 日志：apps/api/data/metrics/hosted_daily.jsonl。
REM 注意：审批恢复由 API 服务完成——计划任务机不含常驻 uvicorn 时，
REM   审批页不可用（后续可加 API 常驻或按需拉起）。
cd /d E:\Projects\zimeiti-ai\apps\api
uv run python -m zimeiti_api.hosted_daily >> data\metrics\hosted_daily.log 2>&1
