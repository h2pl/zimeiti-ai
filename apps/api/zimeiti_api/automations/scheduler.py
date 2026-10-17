"""定时自动化调度与执行（model-resilience-cron）。

进程内每分钟 tick：拾取到点任务（租约防重）→ 执行（case=to_thread 跑运营
脚本；prompt=ask_sync 走对话链路）→ 落 automation_runs + outputs/_automations/。
任务持久化在 PG，服务重启不丢；执行与 API 进程同生命周期（本地场景）。
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from pathlib import Path

from ..core.paths import PROJECT_ROOT
from . import store

_TICK = 60  # 秒
_task: asyncio.Task | None = None
_LOG_DIR = PROJECT_ROOT / "outputs" / "_automations"


def _next_run(schedule: str, now: int) -> int:
    """HH:MM → 今日/明日该时刻；cron 五段式暂只支持每日时刻（本地场景）。"""
    schedule = schedule.strip()
    if ":" in schedule and len(schedule) <= 5:
        hh, mm = schedule.split(":")
        target = time.localtime(now)
        cand = time.mktime(
            (target.tm_year, target.tm_mon, target.tm_mday, int(hh), int(mm), 0, 0, 0, -1)
        )
        if cand <= now:
            cand += 86400
        return int(cand)
    # cron 五段式：不支持，返回 0（调用方校验时拒绝）
    return 0


def validate_schedule(schedule: str) -> int:
    """返回 next_run；不支持或非法返回 0。"""
    schedule = (schedule or "").strip()
    if ":" in schedule and len(schedule) <= 5:
        try:
            hh, mm = schedule.split(":")
            if not (0 <= int(hh) <= 23 and 0 <= int(mm) <= 59):
                return 0
        except Exception:
            return 0
        return _next_run(schedule, int(time.time()))
    return 0  # cron 表达式后续扩展


async def _run_one(a: dict) -> None:
    rid = store.run_start(a["id"])
    log = _LOG_DIR / f"{a['id']}-{rid}.log"
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        if a["kind"] == "case":
            summary = await asyncio.to_thread(_run_case, a["payload"], log)
        else:
            summary = await _run_prompt(a["payload"], log)
        store.run_finish(rid, "done", summary)
    except Exception as e:  # noqa: BLE001   任务失败落日志不拖垮调度循环
        store.run_finish(rid, "failed", str(e)[:500])
        try:
            log.write_text(f"FAILED: {e}", encoding="utf-8")
        except Exception:
            pass


def _run_case(payload: str, log: Path) -> str:
    """跑运营 case（复用 run_brand_case.main 的入网逻辑：payload=--skip-draft 等参数）。"""
    import subprocess
    import sys

    api_dir = PROJECT_ROOT / "api"
    script = api_dir.parent / "scripts" / "run_brand_case.py"
    args = [sys.executable, str(script), *payload.split()]
    r = subprocess.run(
        args,
        cwd=str(api_dir),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=1800,
    )
    out = (r.stdout or "")[-4000:]
    log.write_text(out + "\n--- stderr ---\n" + (r.stderr or "")[-1000:], encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError(f"case 退出码 {r.returncode}: {(r.stderr or '')[:200]}")
    return out[-500:]


# agent 入口由组装层注入（harness-business-split D3，对齐 personas.set_enhance_runtime 范式）；
# scheduler 源码不得 import harness 的 agent 入口（tests/test_layering.py 机械守卫）。
_ask_sync: Callable[[str, str], str] | None = None


def set_ask_sync(fn: Callable[[str, str], str]) -> None:
    """注入 agent 同步对话入口（app.py 组装层调用一次）。"""
    global _ask_sync
    _ask_sync = fn


async def _run_prompt(payload: str, log: Path) -> str:
    """预置 prompt 走对话链路（ask_sync 投主循环）。"""
    if _ask_sync is None:
        raise RuntimeError("agent 入口未注入（组装层未调用 set_ask_sync）")
    reply = await asyncio.get_running_loop().run_in_executor(
        None, _ask_sync, f"auto-{int(time.time())}", payload
    )
    log.write_text(reply or "", encoding="utf-8")
    return (reply or "")[:500]


async def _loop() -> None:
    while True:
        try:
            now = int(time.time())
            for a in store.due(now):
                if not store.take_lease(a["id"], now):
                    continue
                await _run_one(a)
                nxt = _next_run(a["schedule"], int(time.time())) or 0
                store.update(a["id"], last_run=now, next_run=nxt, lease=0)
        except Exception:  # noqa: BLE001  调度循环自身异常不退出
            pass
        await asyncio.sleep(_TICK)


def start() -> None:
    global _task
    if _task is None or _task.done():
        _task = asyncio.get_running_loop().create_task(_loop())


def stop() -> None:
    global _task
    if _task is not None and not _task.done():
        _task.cancel()
    _task = None
