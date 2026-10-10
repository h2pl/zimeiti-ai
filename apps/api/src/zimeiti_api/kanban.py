"""选题看板（P1⑪，参考: Easel IdeasPage 三态 Kanban + CalendarPage 内容日历）。

数据面：候选选题卡来自各托管 cycle 的 state.json（cards），状态流转存
data/state/topics-kanban.json（title → status），默认「待做」。
状态语义：待做（已发现未选）→ 进行中（已选定/创作中）→ 已完成（已发布）。
"""

import json
from pathlib import Path
from typing import Any

STATUSES = ("待做", "进行中", "已完成")


def _kanban_path() -> Path:
    from zimeiti_api.config import DATA_DIR

    return Path(DATA_DIR) / "state" / "topics-kanban.json"


def _load_overrides(path: Path | None = None) -> dict[str, str]:
    p = path or _kanban_path()
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (ValueError, OSError):
        return {}


def set_status(title: str, status: str, path: Path | None = None) -> bool:
    if status not in STATUSES:
        raise ValueError(f"非法状态 {status}（允许 {STATUSES}）")
    p = path or _kanban_path()
    overrides = _load_overrides(p)
    overrides[title] = status
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(overrides, ensure_ascii=False, indent=2), encoding="utf-8")
    return True


def collect_cards(
    outputs_dir: Path | str, path: Path | None = None
) -> dict[str, list[dict[str, Any]]]:
    """扫描全部 cycle state.json 的选题卡 → 三态看板（title 去重，保留最新 reason）。"""
    overrides = _load_overrides(path)
    seen: dict[str, dict[str, Any]] = {}
    root = Path(outputs_dir)
    if root.exists():
        for state_file in sorted(root.glob("*/*/state.json")):
            try:
                state = json.loads(state_file.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                continue
            for card in state.get("cards") or []:
                title = card.get("title", "")
                if not title or title in seen:
                    continue
                seen[title] = {
                    "title": title,
                    "reason": card.get("reason", ""),
                    "direction": card.get("direction", ""),
                    "source": str(state_file.parent.name),
                }
    board: dict[str, list[dict[str, Any]]] = {s: [] for s in STATUSES}
    for title, card in seen.items():
        status = overrides.get(title, "待做")
        if status in board:
            board[status].append(card)
    return board


def calendar_events(db: Any) -> list[dict[str, Any]]:
    """内容日历数据面：发布事件按日期排序（来源 MetricsDB，消费只读）。"""
    events = db.list_events()
    return [
        {
            "date": e["publish_date"],
            "title": e["title"],
            "platform": e["platform"],
            "status": e["status"],
        }
        for e in sorted(events, key=lambda e: e["publish_date"], reverse=True)
    ]
