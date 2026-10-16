"""归因数据源（agent-ops-workflow）：发布/草稿创建成功的最小落盘记录。

设计决策 D2：不做微信阅读数拉取（需凭据+定时任务），先落「发布事实」——
agent 的 ops-review 层读它做复盘；无记录时如实报告。记录按
``outputs/_analytics/<platform>/<date>.json`` 追加，按 media_id 幂等。
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from ..core.paths import OUTPUTS_DIR

_ANALYTICS_DIR = OUTPUTS_DIR / "_analytics"

_MEDIA_ID_RE = re.compile(r"^[\w\-]{1,128}$")


def _safe_path_component(raw: str, *, max_len: int = 64) -> str:
    """平台名/文件名防路径穿越：仅保留安全字符，拒空。"""
    cleaned = re.sub(r"[^\w\-]", "", str(raw))
    if not cleaned or len(cleaned) > max_len:
        raise ValueError(f"非法路径组件: {raw!r}")
    return cleaned


def _content_rel(raw: str) -> str:
    """内容路径必须是相对路径（拒绝对路径/穿越）。"""
    s = str(raw).replace("\\", "/")
    if s.startswith("/") or ".." in s.split("/") or Path(s).is_absolute():
        raise ValueError(f"content_path 必须是相对路径: {raw!r}")
    return s.lstrip("./")


def record_publish(
    platform: str,
    content_path: str,
    media_id: str,
    status: str = "pending-feedback",
    *,
    title: str | None = None,
) -> Path:
    """追加一条发布记录，返回当日记录文件路径。同 media_id 幂等。"""
    if not _MEDIA_ID_RE.match(str(media_id)):
        raise ValueError(f"media_id 非法: {media_id!r}")
    pf_dir = _ANALYTICS_DIR / _safe_path_component(platform)
    pf_dir.mkdir(parents=True, exist_ok=True)
    day_file = pf_dir / f"{date.today().isoformat()}.json"

    records: list[dict] = []
    if day_file.exists():
        try:
            records = json.loads(day_file.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001  历史文件损坏则重建，不堵发布链路
            records = []
    if any(r.get("media_id") == media_id for r in records):
        return day_file

    records.append(
        {
            "media_id": media_id,
            "content_path": _content_rel(content_path),
            "status": _safe_path_component(status, max_len=32),
            "published_at": date.today().isoformat(),
            "title": title,
        }
    )
    tmp = day_file.with_suffix(".tmp")
    tmp.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(day_file)
    return day_file


def read_records(platform: str) -> list[dict]:
    """读取该平台全部日期的发布记录（按日期升序）。"""
    pf_dir = _ANALYTICS_DIR / _safe_path_component(platform)
    if not pf_dir.is_dir():
        return []
    out: list[dict] = []
    for f in sorted(pf_dir.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001  坏文件跳过，复盘不因单文件失败中断
            continue
        out.extend(r for r in data if isinstance(r, dict))
    return out
