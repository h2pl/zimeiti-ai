"""常驻网关（托管形态核心，对标 openclaw gateway 的常驻+进程内定时器形态）。

参考: xiaobei/openclaw 的 gateway——一个常驻进程（Docker 内 PID 1，restart
unless-stopped）内嵌定时器（heartbeat/cron）按点唤醒 agent turn，审批走
「推送+异步确认」。本项目对应形态：

  uv run python -m zimeiti_api.gateway   # 一条命令，无人值守

  ┌─ FastAPI 审批 API + /health（同进程，审批页天然可用）────────────┐
  │  调度器（asyncio 后台任务，进程内 setTimeout 式）                │
  │   ├─ 07:30 hosted_daily_async  → 选题+创作 → 中断等审批          │
  │   └─ 08:30 ops_daily（线程内跑，隔离 sync Playwright 事件循环）  │
  └──────────────────────────────────────────────────────────────┘

与 Windows 计划任务方案（scripts/run_*.bat）的关系：网关是主形态（自包含、
无需外部调度器）；计划任务脚本保留为「不开常驻进程」的降级方案。

幂等：每任务每天至多执行一次（last_run 日期持久化 data/state/gateway.json）；
网关中途重启后当天已跑任务不重跑，错过时间点则在启动后补跑（对齐 cron
catch-up 语义的简化版）。
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

CHECK_INTERVAL_S = 60

# 任务注册表：name → (每日触发时间 HH:MM, 异步执行体)
# - hosted_content：触发托管循环（async，进程内直接 await）
# - ops_data：运营取数+校准（sync Playwright，须放 worker 线程隔离事件循环）
_JOBS: dict[str, tuple[str, Any]] = {
    "hosted_content": ("07:30", None),  # 执行体在 _run_job 内延迟导入
    "ops_data": ("08:30", None),
}


def _state_path() -> Path:
    from zimeiti_api.config import DATA_DIR

    return Path(DATA_DIR) / "state" / "gateway.json"


def _load_last_run(path: Path | None = None) -> dict[str, str]:
    p = path or _state_path()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return {}
    return {}


def is_due(name: str, now: datetime, last_run: dict[str, str]) -> bool:
    """到期判定（纯函数，便于单测）：今天已跑过 → 不跑；过了触发点 → 跑。"""
    if last_run.get(name) == now.strftime("%Y-%m-%d"):
        return False
    hh, mm = _JOBS[name][0].split(":")
    return (now.hour, now.minute) >= (int(hh), int(mm))


def _save_last_run(name: str, last_run: dict[str, str], path: Path | None = None) -> None:
    p = path or _state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    last_run[name] = datetime.now().strftime("%Y-%m-%d")
    p.write_text(json.dumps(last_run, ensure_ascii=False, indent=2), encoding="utf-8")


async def _run_job(name: str) -> dict[str, Any]:
    """执行单个任务（先落 last_run 再执行：失败不无限重试，次日再跑）。"""
    from zimeiti_api import audit

    _save_last_run(name, _load_last_run())
    audit.record("gateway_job_started", job=name)
    try:
        if name == "hosted_content":
            from zimeiti_api.hosted_daily import run_daily_async

            runs = await run_daily_async()
            return {"job": name, "runs": runs}
        if name == "ops_data":
            from zimeiti_api.ops_daily import run_daily
            from zimeiti_api.ops_metrics import MetricsDB

            # sync Playwright（xhs 看板）不能进主循环——放 worker 线程
            ops_run = await asyncio.to_thread(lambda: run_daily(MetricsDB()))
            return {"job": name, "runs": ops_run}
        return {"job": name, "error": f"未知任务 {name}"}
    except Exception as exc:  # noqa: BLE001 - 任务失败记录后继续调度循环
        from zimeiti_api import audit as _audit

        _audit.record("gateway_job_failed", job=name, error=str(exc)[:300])
        return {"job": name, "error": str(exc)[:300]}


async def scheduler_loop(state_path: Path | None = None, check_interval: int = CHECK_INTERVAL_S):
    """调度主循环（对标 openclaw heartbeat-runner 的 setTimeout 循环）。"""
    from zimeiti_api import audit

    audit.record("gateway_scheduler_started", jobs=list(_JOBS))
    while True:
        try:
            now = datetime.now()
            last_run = _load_last_run(state_path)
            for name in _JOBS:
                if is_due(name, now, last_run):
                    result = await _run_job(name)
                    audit.record(
                        "gateway_job_finished",
                        **{
                            "job": name,
                            "ok": "error" not in result,
                        },
                    )
        except Exception:  # noqa: BLE001 - 调度循环永不退出
            from zimeiti_api import audit as _audit

            _audit.record("gateway_scheduler_error")
        await asyncio.sleep(check_interval)


def create_gateway_app():
    """网关 = 审批 API + 进程内调度器（lifespan 启动后台任务）。"""
    from contextlib import asynccontextmanager

    from zimeiti_api.app import create_app

    @asynccontextmanager
    async def lifespan(app):
        # 环境变量 ZIMEITI_GATEWAY=0 可关闭调度（纯 API 模式，测试用）
        if os.environ.get("ZIMEITI_GATEWAY", "1") == "1":
            task = asyncio.create_task(scheduler_loop())
            yield
            task.cancel()
        else:
            yield

    return create_app(lifespan=lifespan)


def main() -> int:
    from dotenv import load_dotenv

    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    load_dotenv()

    import uvicorn

    uvicorn.run(create_gateway_app(), host="127.0.0.1", port=8000)
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main())
