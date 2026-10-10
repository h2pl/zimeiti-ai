@echo off
REM zimeiti-ai 每日运营定时任务入口（Windows 计划任务调用）。
REM 依赖：uv 在系统 PATH；凭证在 apps/api/.env；Postgres 运行中（docker compose up -d）。
REM 日志：apps/api/data/metrics/ops_daily.jsonl（每次运行一条 JSON）。
cd /d E:\Projects\zimeiti-ai\apps\api
uv run python -m zimeiti_api.ops_daily >> data\metrics\ops_daily.log 2>&1
