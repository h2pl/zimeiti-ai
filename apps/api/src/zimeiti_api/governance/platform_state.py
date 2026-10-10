"""平台启停开关（P0⑦）。

参考: xiaobei published-track 的 platform-state.json——每平台一个 enabled 开关，
损坏/缺失 fail-closed 判 disabled，定时任务只对启用平台跑。登录失效时由
risk.handle_platform_error 自动停用，人工重登后手动（或 CLI）恢复。

fail-closed 语义：ensure_defaults 显式创建文件后才视为可信；此后文件缺失或
损坏一律判全停（宁可不跑，不可带着坏登录态硬闯）。
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

DEFAULT_ACCOUNTS = ("xhs-main", "gzh-main")


def _state_path() -> Path:
    from zimeiti_api.config import DATA_DIR

    return Path(DATA_DIR) / "state" / "platform-state.json"


def _load(path: Path | None = None) -> dict[str, Any] | None:
    """读取状态；缺失/损坏返回 None（fail-closed 信号）。"""
    p = path or _state_path()
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    return data if isinstance(data, dict) else None


def ensure_defaults(accounts: tuple[str, ...] = DEFAULT_ACCOUNTS, path: Path | None = None) -> None:
    """首次初始化：显式创建全部启用（此后文件丢失/损坏即 fail-closed 全停）。"""
    p = path or _state_path()
    if p.exists():
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now().isoformat(timespec="seconds")
    data = {a: {"enabled": True, "reason": "initial", "updated_at": now} for a in accounts}
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def is_enabled(account: str, path: Path | None = None) -> bool:
    """启用判定（fail-closed）：文件缺失/损坏/账号缺省 → False。"""
    data = _load(path)
    if data is None:
        return False
    entry = data.get(account)
    if not isinstance(entry, dict):
        return False
    return entry.get("enabled") is True


def set_enabled(account: str, enabled: bool, reason: str = "", path: Path | None = None) -> None:
    p = path or _state_path()
    data = _load(p) or {}
    data[account] = {
        "enabled": enabled,
        "reason": reason,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    from zimeiti_api.core import audit

    audit.record("platform_state_changed", account=account, enabled=enabled, reason=reason)


def disabled_accounts(
    accounts: tuple[str, ...] = DEFAULT_ACCOUNTS, path: Path | None = None
) -> list[str]:
    return [a for a in accounts if not is_enabled(a, path)]
