"""运行时设置（web-pages-batch T1）：data/state/settings.json 持久化。

notify.py 每次发送时读取 notify_webhook_url（env ZIMEITI_NOTIFY_WEBHOOK
优先级更高，保持向后兼容）。读写带容错；写入仅白名单键。
"""

import json
from pathlib import Path
from typing import Any

ALLOWED_KEYS = {"notify_webhook_url"}


def settings_path() -> Path:
    from zimeiti_api.config import DATA_DIR

    return Path(DATA_DIR) / "state" / "settings.json"


def get_settings(path: Path | None = None) -> dict[str, Any]:
    p = path or settings_path()
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (ValueError, OSError):
        return {}


def update_settings(updates: dict[str, Any], path: Path | None = None) -> dict[str, Any]:
    """白名单键更新；未知键与非法值拒绝（fail-closed，评审 C2）。

    notify_webhook_url：空串合法（=关闭通知）；非空必须 http(s):// 开头
    （将被 requests.post 直接作为目标，拒绝任意字符串）。
    """
    unknown = [k for k in updates if k not in ALLOWED_KEYS]
    if unknown:
        raise ValueError(f"未知设置项: {unknown}")
    url = str(updates.get("notify_webhook_url", "")).strip()
    if url and not (url.startswith("http://") or url.startswith("https://")):
        raise ValueError("notify_webhook_url 必须以 http:// 或 https:// 开头")
    current = get_settings(path)
    current.update(updates)
    p = path or settings_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    return current


def get_setting(key: str, default: str = "", path: Path | None = None) -> str:
    return str(get_settings(path).get(key, default))
