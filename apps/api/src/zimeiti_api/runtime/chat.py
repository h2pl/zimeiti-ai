"""对话会话注册（web-chat-publish T1）。

会话即 LangGraph thread_id（checkpointer 持久化）；注册表仅存元数据
（data/state/chat-sessions.json）供清单展示与中断卡片关联账号。
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


def registry_path() -> Path:
    from zimeiti_api.config import DATA_DIR

    return Path(DATA_DIR) / "state" / "chat-sessions.json"


def _load(path: Path | None = None) -> list[dict[str, Any]]:
    p = path or registry_path()
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (ValueError, OSError):
        return []


def create_session(account: str, title: str = "", path: Path | None = None) -> dict[str, Any]:
    entry = {
        "thread_id": f"chat-{uuid.uuid4().hex[:12]}",
        "account": account,
        "title": title.strip() or "新对话",
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    sessions = _load(path)
    sessions.append(entry)
    p = path or registry_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(sessions, ensure_ascii=False, indent=2), encoding="utf-8")
    return entry


def get_session(thread_id: str, path: Path | None = None) -> dict[str, Any] | None:
    for s in _load(path):
        if s["thread_id"] == thread_id:
            return s
    return None


def list_sessions(path: Path | None = None) -> list[dict[str, Any]]:
    return list(reversed(_load(path)))  # 最近在前
