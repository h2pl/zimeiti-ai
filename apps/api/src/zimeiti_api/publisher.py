"""发布执行器（Task 6.1，宪法原则 III：风控护栏前置 fail-closed）。

统一发布入口：频控 → 白名单 → 凭证检查 → 才允许调用平台函数。
platform_call 由上层注入（真实脚本 / 测试 mock），执行器绝不直接碰平台。
"""

from dataclasses import dataclass, field
from datetime import date

from zimeiti_api.credentials import decrypt_secret


class RateLimitExceeded(Exception):
    """超出单账号单日发布上限。"""


class AccountNotAllowed(Exception):
    """账号不在发布白名单。"""


@dataclass
class PublishExecutor:
    daily_limit: int = 1
    allowed_accounts: set[str] = field(default_factory=set)
    _published_today: dict[str, int] = field(default_factory=dict)
    _day: date = field(default_factory=date.today)

    def _roll_day(self) -> None:
        if self._day != date.today():
            self._day = date.today()
            self._published_today.clear()

    def publish(
        self,
        account: str,
        draft: dict,
        platform_call=None,
        credentials_sealed: str = "",
    ) -> dict:
        """发布一个草稿。返回 {"platform_result": ..., "readback": ...}。

        检查顺序（任一失败即拒绝，平台函数零调用）：
        1. 白名单  2. 频控  3. 凭证
        """
        self._roll_day()
        if account not in self.allowed_accounts:
            raise AccountNotAllowed(f"账号 {account} 不在发布白名单")
        if self._published_today.get(account, 0) >= self.daily_limit:
            published = self._published_today[account]
            raise RateLimitExceeded(
                f"账号 {account} 今日已发布 {published} 篇，达到上限 {self.daily_limit}"
            )
        if not credentials_sealed:
            raise ValueError("缺少加密凭证：发布前必须提供平台凭证（宪法 II fail-closed）")
        decrypt_secret(credentials_sealed)  # 凭证无效会在此时抛异常

        platform_call = platform_call or self._default_platform_call
        result = platform_call(account, draft)
        self._published_today[account] = self._published_today.get(account, 0) + 1
        # 真实路由器契约（Task 1.1）：返回 {"platform_result", "readback"} 三档结果，
        # 必须透传其 outcome——A5 演练发现此处曾硬编码 unverified，导致生产审计
        # 永远记 unverified（W1 复发）。非 dict 返回（测试占位）才降级 unverified。
        if isinstance(result, dict) and "readback" in result:
            return result
        return {"platform_result": result, "readback": "unverified"}

    @staticmethod
    def _default_platform_call(account: str, draft: dict) -> str:
        # 真实平台脚本在 real-account-verification 接线；默认占位仅供测试
        return "submitted"
