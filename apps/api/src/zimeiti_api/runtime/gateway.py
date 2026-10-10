"""常驻网关（托管形态核心，对标 openclaw gateway 的常驻+进程内定时器形态）。

参考: xiaobei/openclaw 的 gateway——一个常驻进程（Docker 内 PID 1，restart
unless-stopped）内嵌定时器（heartbeat/cron）按点唤醒 agent turn，审批走
「推送+异步确认」。本项目对应形态：

  uv run python -m zimeiti_api.runtime.gateway   # 一条命令，无人值守

  ┌─ FastAPI 审批 API + /health（同进程，审批页天然可用）────────────┐
  │  APScheduler（AsyncIOScheduler，调度内核用现成轮子——              │
  │  misfire_grace_time/coalesce/时区/持久化语义不再手搓）            │
  │   ├─ 07:30 hosted_daily_async  → 选题+创作 → 中断等审批          │
  │   └─ 08:30 ops_daily（worker 线程跑，隔离 sync Playwright）      │
  └──────────────────────────────────────────────────────────────┘

依赖选型记录：APScheduler 3.x 稳定线（4.0 仍是 pre-release 官方不建议上生产）；
LangGraph Platform 有原生 cron 但自托管要 license 且需整体迁移（调研记录
2026-10-10）；aegra（开源替代）待多 agent 后台运行需求出现后再评估。

幂等：每任务每天至多执行一次（last_run 日期持久化 data/state/gateway.json）；
网关错过时间点启动后补跑（catch-up，is_due 判定），运行中错过的触发由
APScheduler 的 misfire_grace_time（1h）+ coalesce 兜底。
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# 任务注册表：name → 触发时刻与执行体选择（执行体见 _run_job）
_JOBS: dict[str, dict[str, int]] = {
    "health_check": {"hour": 7, "minute": 0},
    "hosted_content": {"hour": 7, "minute": 30},
    "ops_data": {"hour": 8, "minute": 30},
}

MISFIRE_GRACE_S = 3600  # 运行中错过的触发，1 小时内补跑一次（coalesce 合并）


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
    """补跑判定（纯函数，便于单测）：今天已跑过 → 不跑；过了触发点 → 跑。"""
    if last_run.get(name) == now.strftime("%Y-%m-%d"):
        return False
    cfg = _JOBS[name]
    return (now.hour, now.minute) >= (cfg["hour"], cfg["minute"])


def _save_last_run(name: str, last_run: dict[str, str], path: Path | None = None) -> None:
    p = path or _state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    last_run[name] = datetime.now().strftime("%Y-%m-%d")
    p.write_text(json.dumps(last_run, ensure_ascii=False, indent=2), encoding="utf-8")


def _trigger_path() -> Path:
    from zimeiti_api.config import DATA_DIR

    return Path(DATA_DIR) / "state" / "ops-trigger.json"


async def _consume_manual_triggers() -> list[str]:
    """消费手动触发标记（API 与网关可能不同进程，标记文件是唯一通道）。

    原子消费：先 rename 到 .consuming 再处理（评审 W1——避免「执行期间新触发
    被 unlink 吞掉」的竞态窗口）；消费期间的新写入留在原文件下一轮处理。
    """
    p = _trigger_path()
    if not p.exists():
        return []
    consumed = p.with_suffix(".json.consuming")
    try:
        p.replace(consumed)  # 原子接管
    except OSError:
        return []  # 其他进程正在消费
    try:
        triggers = json.loads(consumed.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        consumed.unlink(missing_ok=True)
        return []
    ran = []
    for name in list(triggers):
        if name in _JOBS:
            await _run_job(name)
            ran.append(name)
    consumed.unlink(missing_ok=True)
    return ran


async def _trigger_consumer_loop():
    """手动触发消费循环（随 lifespan 启动，30s 间隔）。"""
    from zimeiti_api.core import audit

    while True:
        try:
            await _consume_manual_triggers()
        except Exception:  # noqa: BLE001
            audit.record("gateway_trigger_consumer_error")
        await asyncio.sleep(30)


async def _run_job(name: str) -> dict[str, Any]:
    """执行单个任务（先落 last_run 再执行：失败不无限重试，次日再跑）。"""
    from zimeiti_api.core import audit

    _save_last_run(name, _load_last_run())
    audit.record("gateway_job_started", job=name)
    try:
        if name == "hosted_content":
            from zimeiti_api.runtime.hosted_daily import run_daily_async

            runs = await run_daily_async()
            return {"job": name, "runs": runs}
        if name == "health_check":
            from zimeiti_api.runtime.health import run_health_check

            return {"job": name, "report": run_health_check()}
        if name == "ops_data":
            from zimeiti_api.operations.daily import run_daily
            from zimeiti_api.operations.metrics import MetricsDB

            # sync Playwright（xhs 看板）不能进主循环——放 worker 线程
            ops_run = await asyncio.to_thread(lambda: run_daily(MetricsDB()))
            # 晨报（P0⑦）：巡检态 + 当日任务摘要
            from zimeiti_api.core import notify
            from zimeiti_api.governance import platform_state
            from zimeiti_api.runtime.health import build_morning_digest

            digest = build_morning_digest(
                {
                    "accounts": {
                        a: {"ok": platform_state.is_enabled(a)}
                        for a in platform_state.DEFAULT_ACCOUNTS
                    }
                },
                {"ops_data": {"runs": ops_run}},
            )
            notify.send("morning_digest", digest)
            return {"job": name, "runs": ops_run}
        if name == "publish_queue_scan":
            from zimeiti_api.governance.queue import run_due

            return {"job": name, "results": run_due()}
        return {"job": name, "error": f"未知任务 {name}"}
    except Exception as exc:  # noqa: BLE001 - 任务失败记录后继续调度
        audit.record("gateway_job_failed", job=name, error=str(exc)[:300])
        return {"job": name, "error": str(exc)[:300]}


async def catchup_missed_jobs() -> list[str]:
    """启动补跑：进程关停期间错过的任务立即执行一次（cron catch-up 简化语义）。"""
    now = datetime.now()
    last_run = _load_last_run()
    ran = []
    for name in _JOBS:
        if is_due(name, now, last_run):
            await _run_job(name)
            ran.append(name)
    return ran


def _build_scheduler() -> AsyncIOScheduler:
    """构建调度器（每日 CronTrigger；内核语义交给 APScheduler，不再手搓循环）。"""
    from zimeiti_api.core import audit

    scheduler = AsyncIOScheduler()
    for name, cfg in _JOBS.items():
        scheduler.add_job(
            _run_job,
            CronTrigger(hour=cfg["hour"], minute=cfg["minute"]),
            args=[name],
            id=name,
            name=name,
            coalesce=True,  # 积压多次触发合并为一次
            misfire_grace_time=MISFIRE_GRACE_S,
            max_instances=1,  # 上一次没跑完不允许并发重入
        )
    from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED, EVENT_JOB_MISSED

    scheduler.add_listener(
        lambda event: audit.record(
            "gateway_job_error" if event.exception else "gateway_job_executed",
            job=getattr(event, "job_id", None),
        ),
        EVENT_JOB_ERROR | EVENT_JOB_EXECUTED | EVENT_JOB_MISSED,
    )
    # 发布排期队列扫描（P0⑤）：间隔扫描，到期条目派发发布（已审批内容）
    from apscheduler.triggers.interval import IntervalTrigger

    scheduler.add_job(
        _run_job,
        IntervalTrigger(seconds=120),
        args=["publish_queue_scan"],
        id="publish_queue_scan",
        name="publish_queue_scan",
        max_instances=1,
    )
    return scheduler


def create_gateway_app():
    """网关 = 审批 API + APScheduler 调度器（lifespan 启动补跑+定时任务）。"""
    from contextlib import asynccontextmanager

    from zimeiti_api.app import create_app
    from zimeiti_api.core import audit

    @asynccontextmanager
    async def lifespan(app):
        # 环境变量 ZIMEITI_GATEWAY=0 可关闭调度（纯 API 模式，测试用）
        if os.environ.get("ZIMEITI_GATEWAY", "1") == "1":
            from zimeiti_api.governance import platform_state

            platform_state.ensure_defaults()  # 首次显式初始化（此后缺失/损坏 fail-closed 全停）
            missed = await catchup_missed_jobs()
            if missed:
                audit.record("gateway_catchup", jobs=missed)
            scheduler = _build_scheduler()
            scheduler.start()
            app.state.scheduler = scheduler
            yield
            scheduler.shutdown(wait=False)
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
    raise SystemExit(main())
