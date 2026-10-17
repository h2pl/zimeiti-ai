"""无人值守护栏（autonomous-guardrails）：重试 / 熔断 / 预算 / 自主模式 HITL。

诚实原则（与项目一致）：预算不可计量时**放行**而非臆造拦截；需人工确认的动作
**标记 blocked 并继续**，绝不在无人时偷偷执行付费/发布类动作（D1/D2/D3）。
"""

from __future__ import annotations

import time
from collections.abc import Callable

# 可重试异常类型：瞬时故障（网络/限流/超时）
_RETRYABLE_EXC = (ConnectionError, TimeoutError, OSError)

# 需人工确认的特征词（保守识别：宁可多标 blocked，也不自作主张放行）
_NEEDS_CONFIRM_MARKERS = (
    "人工确认",
    "需要确认",
    "待确认",
    "pending",
    "ask_human",
    "已挂起",
    "付费",
    "扣费",
    "不可逆",
)


def is_retryable(exc: BaseException) -> bool:
    """可重试判定：瞬时故障可重试，配置性/参数性错误不重试（重试无意义）。"""
    if isinstance(exc, _RETRYABLE_EXC):
        return True
    # ValueError / EntryNotInjected 等属配置或调用错误，重试不会变好
    return False


def retry_call(fn: Callable[[], str], tries: int = 2, backoff: float = 0.0) -> str:
    """按次数重试（退避递增）。最后一次失败抛出原异常。"""
    last: BaseException | None = None
    for i in range(max(0, int(tries)) + 1):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001   按类型决定是否继续
            last = e
            if not is_retryable(e) or i == int(tries):
                raise
            if backoff:
                time.sleep(backoff * (i + 1))
    raise last if last else RuntimeError("重试逻辑异常")


class CircuitBreaker:
    """连续失败熔断：达阈值跳闸（流程停用），成功后计数归零。"""

    def __init__(self, threshold: int = 3) -> None:
        self.threshold = max(1, int(threshold))
        self.consecutive_failures = 0
        self.tripped = False
        self.reason = ""

    def record_failure(self, reason: str = "") -> None:
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.threshold:
            self.tripped = True
            self.reason = reason or f"连续失败 {self.consecutive_failures} 次"

    def record_success(self) -> None:
        self.consecutive_failures = 0
        self.tripped = False
        self.reason = ""


class BudgetGuard:
    """当日预算护栏：超过上限拦截；不可计量（None）放行——不臆造金额。"""

    def __init__(self, daily_limit_usd: float | None = None) -> None:
        self.daily_limit_usd = daily_limit_usd

    def check(self, spent_usd: float | None) -> bool:
        """True=放行，False=拦截。"""
        if self.daily_limit_usd is None:
            return True
        if spent_usd is None:  # 无单价数据 → 不可计量，放行
            return True
        return float(spent_usd) < float(self.daily_limit_usd)


class AutonomyPolicy:
    """自主模式 HITL 策略：需确认动作标 blocked（不阻塞），其余自动放行。"""

    def __init__(self, markers: tuple[str, ...] = _NEEDS_CONFIRM_MARKERS) -> None:
        self.markers = markers

    def classify(self, output: str) -> str:
        """按结果侧特征判定：blocked（待人工确认）/ auto（自动放行）。"""
        low = (output or "").lower()
        for m in self.markers:
            if m.lower() in low:
                return "blocked"
        return "auto"


_budget_provider: Callable[[], dict] | None = None


def set_budget_provider(fn: Callable[[], dict] | None) -> None:
    """注入用量提供者（组装层接线；本包不 import harness，分层纪律）。"""
    global _budget_provider
    _budget_provider = fn


def status() -> dict:
    """护栏状态汇总（供 /api/autonomous/status）：熔断态、预算用量、blocked 清单。

    数据取不到时如实标注 unavailable/unknown，不编造。
    """
    out: dict = {"available": True, "blocked": [], "circuit": {}, "budget": {}}
    try:
        from . import store as _st

        flows = _st.list_flows()
        out["circuit"] = {
            "disabled_flows": [
                {"id": f["id"], "name": f["name"]} for f in flows if not f.get("enabled", True)
            ]
        }
    except Exception as e:  # noqa: BLE001
        out["available"] = False
        out["circuit"] = {"error": str(e)[:200]}

    if _budget_provider is None:
        out["budget"] = {"unknown": "用量提供者未注入"}
    else:
        try:
            out["budget"] = _budget_provider()
        except Exception as e:  # noqa: BLE001
            out["budget"] = {"error": str(e)[:200]}
    return out
