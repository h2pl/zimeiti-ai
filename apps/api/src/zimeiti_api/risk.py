"""平台风控信号分级与错误分类（P0①③）。

参考: xiaobei crews/main/skills/_shared/relay-sign.ts 的判定体系（血泪教训制度化）：

- **软风控判定必须在登录墙之前**——速度型软风控页（error_code=300017/300031，
  「请求太频繁」等）会重定向到 website-login/error 路径，误归登录墙会触发
  无谓的重登循环（登录态本身是好的）。
- 登录墙特征：期望 JSON 却返回 HTML 登录页（<head>/<body>/<title> 开头）、
  login URL、401。
- 动作绑定：login_wall → 停用平台 + 通知（严禁 cookie 注入造会话，见
  platform_state）；soft_block → 冷却 30 分钟不重试（xiaobei 纪律）；
  transient → 留痕等下一轮；unknown → 留痕继续（单条失败不拖垮链路）。
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from zimeiti_api import audit

# 软风控（强信号优先：error_code；文案仅兜底）
SOFT_BLOCK_RE = re.compile(
    r"error_code=(?:300017|300031)|安全限制|访问链接异常|请求太频繁|访问频次异常",
    re.IGNORECASE,
)
# 登录墙：HTML 登录页特征 + login URL + 会话失效文案
LOGIN_WALL_RE = re.compile(
    r"<head\b|<body\b|<title\b|/login\b|请.{0,4}登录|未登录|登录已过期|登录态失效",
    re.IGNORECASE,
)
TRANSIENT_RE = re.compile(r"timeout|timed out|connection|暂时|重试", re.IGNORECASE)

COOLDOWN_MINUTES = 30  # xiaobei 纪律：触发风控降级 30 分钟不重试


def classify(text: str, status: int | None = None) -> str:
    """分级平台错误信号：soft_block / login_wall / transient / unknown。

    判定顺序对齐 xiaobei relay-sign.ts：软风控先于登录墙（软风控页可能带
    login 样式的重定向 URL，误判会引发重登循环）。
    """
    text = text or ""
    if SOFT_BLOCK_RE.search(text) or status == 429:
        return "soft_block"
    if LOGIN_WALL_RE.search(text) or status == 401:
        return "login_wall"
    if status is not None and 500 <= status < 600:
        return "transient"
    if TRANSIENT_RE.search(text):
        return "transient"
    return "unknown"


def _cooldown_path() -> Path:  # type: ignore[name-defined]
    from zimeiti_api.config import DATA_DIR

    return Path(DATA_DIR) / "state" / "risk-cooldown.json"


def set_cooldown(account: str, minutes: int = COOLDOWN_MINUTES) -> str:
    """软风控冷却：until 时间内该账号的取数/发布动作跳过（不重试）。"""
    p = _cooldown_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    state: dict[str, Any] = {}
    if p.exists():
        try:
            state = json.loads(p.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            state = {}
    until = (datetime.now() + timedelta(minutes=minutes)).isoformat(timespec="seconds")
    state[account] = {"until": until, "reason": "soft_block"}
    p.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    audit.record("risk_cooldown_set", account=account, until=until)
    return until


def in_cooldown(account: str, now: datetime | None = None) -> bool:
    p = _cooldown_path()
    if not p.exists():
        return False
    try:
        state = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return False
    entry = state.get(account) or {}
    until = entry.get("until", "")
    if not until:
        return False
    now = now or datetime.now()
    return now.isoformat(timespec="seconds") < until


def handle_platform_error(account: str, scope: str, text: str, status: int | None = None) -> str:
    """统一错误处置：分级 → 绑定动作 → 返回级别。取数/发布路径共用。

    动作（对齐 xiaobei 纪律）：
    - login_wall：停用平台 + 通知（等人工白天重登，绝不自动造会话）
    - soft_block：冷却 30 分钟
    - transient/unknown：仅留痕（调用方继续，不中断链路）
    """
    level = classify(text, status)
    if level == "login_wall":
        from zimeiti_api import notify, platform_state

        platform_state.set_enabled(account, False, f"登录失效：{scope}")
        notify.send(
            "login_wall",
            f"[{account}] 登录失效（{scope}），已停用该平台，请人工重登后启用：{text[:200]}",
        )
    elif level == "soft_block":
        set_cooldown(account)
        from zimeiti_api import notify

        notify.send(
            "soft_block",
            f"[{account}] 触发软风控（{scope}），冷却 {COOLDOWN_MINUTES} 分钟：{text[:200]}",
        )
    audit.record("risk_classified", account=account, scope=scope, level=level)
    return level
