"""定时自动化与用量统计（model-resilience-cron）。"""

import time

import pytest

pytestmark = pytest.mark.skipif(
    __import__("os").environ.get("SKIP_PG_TESTS") == "1",
    reason="PG 不可用",
)


@pytest.fixture(autouse=True)
def clean():
    from zimeiti_api.automations import store as st
    from zimeiti_harness import usage

    st.setup()
    usage.setup()
    st._exec("DELETE FROM automations")
    st._exec("DELETE FROM automation_runs")
    usage._exec("DELETE FROM chat_usage")
    yield
    st._exec("DELETE FROM automations")
    st._exec("DELETE FROM automation_runs")
    usage._exec("DELETE FROM chat_usage")


def test_schedule_validate():
    from zimeiti_api.automations import scheduler

    now = int(time.time())
    nxt = scheduler.validate_schedule("08:30")
    assert nxt > now
    assert scheduler.validate_schedule("25:99") == 0
    assert scheduler.validate_schedule("*/5 * * * *") == 0  # cron 暂不支持


def test_crud_and_due():
    from zimeiti_api.automations import scheduler, store

    nxt = scheduler.validate_schedule("08:30")
    aid = store.create("每日出稿", "case", "08:30", "", nxt)
    items = store.list_all()
    assert any(a["id"] == aid for a in items)
    # 到点判定
    assert store.due(nxt + 1)
    assert not store.due(nxt - 1)
    # 租约抢占
    assert store.take_lease(aid, nxt + 1)
    assert not store.take_lease(aid, nxt + 1)  # 租约内不可重抢
    # 执行记录
    rid = store.run_start(aid)
    store.run_finish(rid, "done", "ok")
    runs = store.list_runs(aid)
    assert runs and runs[0]["status"] == "done"
    store.delete(aid)
    assert not any(a["id"] == aid for a in store.list_all())
    assert not store.list_runs(aid)


def test_usage_record_and_summary():
    from zimeiti_harness import usage

    usage.record("sess-u1", "t1", "gpt-4o-mini", 100, 200)
    usage.record("sess-u1", "t2", "gpt-4o-mini", 50, 80)
    s = usage.summary(session_key="sess-u1")
    assert s["total_prompt"] == 150
    assert s["total_completion"] == 280
    assert s["rows"][0]["turns"] == 2
    # 无用量元数据不记
    usage.record("sess-u1", "t3", "m", 0, 0)
    assert usage.summary(session_key="sess-u1")["rows"][0]["turns"] == 2


def test_usage_summary_all():
    from zimeiti_harness import usage

    usage.record("sess-u2", "t1", "m1", 10, 20)
    s = usage.summary()
    assert any(r["session_key"] == "sess-u2" for r in s["rows"])
