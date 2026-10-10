"""gateway 常驻网关验收：到期判定幂等、任务执行 last_run 落盘、APScheduler 注册。"""

import json
import threading
from datetime import datetime

import pytest

from zimeiti_api.runtime import gateway
from zimeiti_api.runtime.gateway import is_due


def test_is_due_basic():
    now = datetime(2026, 10, 10, 7, 31)
    # 未跑过 + 已过 07:30 → 到期
    assert is_due("hosted_content", now, {}) is True
    # 今天已跑过 → 不再跑（幂等）
    assert is_due("hosted_content", now, {"hosted_content": "2026-10-10"}) is False
    # 未到触发点 → 不跑
    assert is_due("hosted_content", datetime(2026, 10, 10, 7, 29), {}) is False
    # 另一个任务时间不同（08:30）
    assert is_due("ops_data", now, {}) is False
    assert is_due("ops_data", datetime(2026, 10, 10, 8, 30), {}) is True


def test_is_due_catchup_after_restart():
    """网关重启补跑：昨天跑过、今天已过点 → 再跑（cron catch-up 简化语义）。"""
    now = datetime(2026, 10, 11, 9, 0)
    assert is_due("hosted_content", now, {"hosted_content": "2026-10-10"}) is True


@pytest.mark.asyncio
async def test_run_job_records_last_run_and_executes(tmp_path, monkeypatch):
    """执行任务前先落 last_run（失败不无限重试，次日再跑），并真实调用执行体。"""
    state_file = tmp_path / "gateway.json"
    called = []

    async def fake_run_daily_async():
        called.append("hosted")
        return [{"account": "xhs-main", "interrupted": True}]

    monkeypatch.setattr(gateway, "_load_last_run", lambda p=None: {})
    monkeypatch.setattr(gateway, "_state_path", lambda: state_file)
    monkeypatch.setattr("zimeiti_api.runtime.hosted_daily.run_daily_async", fake_run_daily_async)
    result = await gateway._run_job("hosted_content")
    assert result["runs"][0]["account"] == "xhs-main"
    assert called == ["hosted"]
    state = json.loads(state_file.read_text(encoding="utf-8"))
    assert state["hosted_content"] == datetime.now().strftime("%Y-%m-%d")

    # 执行体抛异常 → 记 error 不炸，last_run 已落（当日不重试）
    async def boom():
        raise RuntimeError("PG 连不上")

    monkeypatch.setattr("zimeiti_api.runtime.hosted_daily.run_daily_async", boom)
    monkeypatch.setattr(gateway, "_load_last_run", lambda p=None: {})
    result = await gateway._run_job("hosted_content")
    assert "PG 连不上" in result["error"]


@pytest.mark.asyncio
async def test_ops_data_runs_in_worker_thread(tmp_path, monkeypatch):
    """ops_data 的 sync Playwright 必须在 worker 线程执行（隔离事件循环）。"""
    seen_threads = []
    monkeypatch.setattr(gateway, "_load_last_run", lambda p=None: {})
    monkeypatch.setattr(gateway, "_state_path", lambda: tmp_path / "gateway.json")

    def fake_run_daily(db):
        seen_threads.append(threading.current_thread() is not threading.main_thread())
        return []

    monkeypatch.setattr("zimeiti_api.operations.daily.run_daily", fake_run_daily)
    monkeypatch.setattr("zimeiti_api.operations.metrics.MetricsDB", lambda: object())
    await gateway._run_job("ops_data")
    assert seen_threads == [True]  # 在 worker 线程执行，而非主协程线程


def test_build_scheduler_registers_jobs():
    """APScheduler 内核：双任务按 CronTrigger 注册，misfire/coalesce 语义齐备。"""
    scheduler = gateway._build_scheduler()
    for name, cfg in gateway._JOBS.items():
        job = scheduler.get_job(name)
        assert job is not None
        assert job.coalesce is True
        assert job.max_instances == 1
        assert job.misfire_grace_time == gateway.MISFIRE_GRACE_S
        from apscheduler.triggers.cron import CronTrigger

        assert str(job.trigger) == str(CronTrigger(hour=cfg["hour"], minute=cfg["minute"]))


@pytest.mark.asyncio
async def test_catchup_missed_jobs(tmp_path, monkeypatch):
    """启动补跑：错过的任务立即执行一次并记录 last_run；已跑过的不重复。"""
    state_file = tmp_path / "gateway.json"
    monkeypatch.setattr(gateway, "_state_path", lambda: state_file)

    class FakeDateTime(datetime):
        @classmethod
        def now(cls):
            return datetime(2026, 10, 10, 9, 0)  # 双任务均已过点

    monkeypatch.setattr(gateway, "datetime", FakeDateTime)

    executed = []

    async def fake_run_job(name):
        executed.append(name)
        gateway._save_last_run(name, gateway._load_last_run())
        return {"job": name}

    monkeypatch.setattr(gateway, "_run_job", fake_run_job)

    ran = await gateway.catchup_missed_jobs()
    assert ran == ["health_check", "hosted_content", "ops_data"]

    # 再补跑一次：last_run 已是今天 → 不重复
    ran2 = await gateway.catchup_missed_jobs()
    assert ran2 == []
    assert executed == ["health_check", "hosted_content", "ops_data"]
