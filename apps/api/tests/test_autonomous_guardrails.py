"""autonomous-guardrails：无人值守护栏（重试/熔断/预算/自主模式 HITL）。

覆盖规格四条：
- 步骤级重试（可重试异常重试、配置性错误不重试）
- 连续失败熔断（达阈值停用、成功后归零）
- 预算护栏（超上限即停、无单价放行不拦截）
- 自主模式 HITL 策略（需确认动作标 blocked 不阻塞、后续步骤继续）
"""

from __future__ import annotations

import pytest

from zimeiti_autonomous import guardrails as gr
from zimeiti_autonomous import runner as rn
from zimeiti_autonomous.runner import EntryNotInjected


@pytest.fixture(autouse=True)
def _reset():
    rn.set_agent_entry(None)
    yield
    rn.set_agent_entry(None)


# ── 1. 重试 ────────────────────────────────────────────────────────────────
def test_retryable_exception_is_retried():
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("抖动")
        return "ok"

    out = gr.retry_call(fn, tries=2, backoff=0)
    assert out == "ok" and calls["n"] == 3


def test_config_error_not_retried():
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        raise EntryNotInjected("agent 入口未注入")

    with pytest.raises(EntryNotInjected):
        gr.retry_call(fn, tries=3, backoff=0)
    assert calls["n"] == 1, "配置性错误不得重试"


def test_is_retryable_classification():
    assert gr.is_retryable(ConnectionError("x"))
    assert gr.is_retryable(TimeoutError("x"))
    assert not gr.is_retryable(EntryNotInjected("x"))
    assert not gr.is_retryable(ValueError("参数错"))


# ── 2. 熔断 ────────────────────────────────────────────────────────────────
def test_circuit_breaker_trips_and_resets():
    cb = gr.CircuitBreaker(threshold=3)
    cb.record_failure()
    cb.record_failure()
    assert not cb.tripped
    cb.record_failure()
    assert cb.tripped, "连续 3 次失败应熔断"
    cb.record_success()
    assert not cb.tripped and cb.consecutive_failures == 0, "成功后计数归零"


# ── 3. 预算护栏 ────────────────────────────────────────────────────────────
def test_budget_guard_blocks_when_over():
    guard = gr.BudgetGuard(daily_limit_usd=1.0)
    assert guard.check(1.5) is False, "超预算应拦截"
    assert guard.check(0.5) is True


def test_budget_guard_passes_when_unknown():
    """无单价数据（None）→ 放行，不臆造拦截。"""
    guard = gr.BudgetGuard(daily_limit_usd=1.0)
    assert guard.check(None) is True


# ── 4. 自主模式 HITL 策略 ──────────────────────────────────────────────────
def test_policy_marks_blocked_for_needs_confirmation():
    pol = gr.AutonomyPolicy()
    assert pol.classify("需要人工确认后发布，已挂起 pending") == "blocked"
    assert pol.classify("已生成初稿，等待下一步") == "auto"


def test_runner_marks_blocked_and_continues(tmp_path):
    """需确认动作不阻塞：标 blocked 且后续步骤继续跑完。"""

    def entry(sk: str, msg: str) -> str:
        if "produce" in sk:
            return "需要人工确认后发布（pending）"
        return "产出"

    rn.set_agent_entry(entry)
    res = rn.run_flow(
        flow_id="f-block",
        name="阻塞流程",
        steps=["produce", "review"],
        config={"guardrails": True},
        archive_root=tmp_path,
    )
    # blocked 不算失败：流程整体仍继续到下一步
    assert res["status"] == "done", f"blocked 不应阻断流程：{res}"
    blocked = [s for s in res["steps"] if s["status"] == "blocked"]
    assert len(blocked) == 1 and blocked[0]["step"] == "produce"
    assert [s["step"] for s in res["steps"]] == ["produce", "review"]


def test_runner_retries_then_fails(tmp_path):
    """重试上限后仍失败 → 该步 failed，记录重试次数。"""
    calls = {"n": 0}

    def entry(sk: str, msg: str) -> str:
        calls["n"] += 1
        raise ConnectionError("一直抖")

    rn.set_agent_entry(entry)
    res = rn.run_flow(
        flow_id="f-retry",
        name="重试流程",
        steps=["discover"],
        config={"guardrails": True, "retry": 2},
        archive_root=tmp_path,
    )
    assert res["status"] == "failed"
    assert res["steps"][0]["retries"] == 2
    assert calls["n"] == 3  # 首试 + 2 次重试


def test_guardrails_can_be_disabled(tmp_path):
    """关闭护栏：不重试（保持 ① 的失败即停语义，便于确定性测试）。"""
    calls = {"n": 0}

    def entry(sk: str, msg: str) -> str:
        calls["n"] += 1
        raise ConnectionError("抖")

    rn.set_agent_entry(entry)
    rn.run_flow(
        flow_id="f-off",
        name="关护栏",
        steps=["discover"],
        config={"guardrails": False},
        archive_root=tmp_path,
    )
    assert calls["n"] == 1
