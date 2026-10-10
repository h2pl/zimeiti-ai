"""hosted_daily 每日触发验收：待审批堆积跳过、单账号失败不中断、日志落盘。"""

import asyncio
import json

import pytest

from zimeiti_api import hosted_daily


@pytest.fixture
def fake_run(monkeypatch):
    """同步 runner 替代 asyncio.run（协程内无 await，直接驱动）。"""

    def _run(coro):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    monkeypatch.setattr(hosted_daily.asyncio, "run", _run)


def test_daily_skips_accounts_with_pending(monkeypatch, fake_run):
    monkeypatch.setattr(hosted_daily, "_pending_accounts", lambda: {"xhs-main"})
    called = []

    async def fake_trigger(account):
        called.append(account)
        return {"account": account, "interrupted": True}

    monkeypatch.setattr(hosted_daily, "trigger_for_account", fake_trigger)
    runs = hosted_daily.run_daily(["xhs-main", "gzh-main"])
    assert runs[0] == {"account": "xhs-main", "skipped": "已有待审批项"}
    assert runs[1] == {"account": "gzh-main", "interrupted": True}
    assert called == ["gzh-main"]  # 堆积账号绝不重复触发


def test_daily_single_account_failure_continues(monkeypatch, tmp_path, fake_run):
    monkeypatch.setattr(hosted_daily, "_pending_accounts", lambda: set())
    monkeypatch.setattr(hosted_daily, "_log_path", lambda: tmp_path / "h.jsonl")

    async def fake_trigger(account):
        if account == "xhs-main":
            raise RuntimeError("模型超时")
        return {"account": account, "interrupted": True}

    monkeypatch.setattr(hosted_daily, "trigger_for_account", fake_trigger)
    runs = hosted_daily.run_daily(["xhs-main", "gzh-main"])
    assert "模型超时" in runs[0]["error"]
    assert runs[1] == {"account": "gzh-main", "interrupted": True}
    # 运行日志落盘（可观测）
    rec = json.loads((tmp_path / "h.jsonl").read_text(encoding="utf-8").strip())
    assert rec["runs"][0]["account"] == "xhs-main"


def test_daily_log_appends(tmp_path, monkeypatch, fake_run):
    monkeypatch.setattr(hosted_daily, "_pending_accounts", lambda: set())
    monkeypatch.setattr(hosted_daily, "_log_path", lambda: tmp_path / "h.jsonl")

    async def fake_trigger(account):
        return {"account": account, "interrupted": True}

    monkeypatch.setattr(hosted_daily, "trigger_for_account", fake_trigger)
    hosted_daily.run_daily(["xhs-main"])
    hosted_daily.run_daily(["xhs-main"])
    lines = (tmp_path / "h.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
