"""执行审计（Task 2.4）：托管循环每个自动动作留痕，JSONL 追加制。"""

import json
import os
from datetime import UTC, datetime
from pathlib import Path

from zimeiti_api.config import AUDIT_PATH


def _audit_file() -> Path:
    return Path(os.environ.get("AUDIT_PATH", AUDIT_PATH))


def record(action: str, **detail) -> dict:
    entry = {"ts": datetime.now(UTC).isoformat(), "action": action, **detail}
    f = _audit_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    with f.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def list_entries() -> list[dict]:
    f = _audit_file()
    if not f.exists():
        return []
    with f.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]
