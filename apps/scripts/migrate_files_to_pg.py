"""一次性导入：旧文件数据 -> PostgreSQL（pg-data-layer 变更，验收 A5）。

导入对象（均为迁 PG 前的文件主存储）：
- apps/sessions/<key>.json        -> chat_sessions + chat_messages
- apps/sessions/pending_questions.json -> hitl_pending（超 TTL 的过期项跳过）
- apps/outputs/_ideas.json        -> ideas
- apps/outputs/_schedule.json     -> schedule_items

幂等：会话按 session_key 判重（已存在即跳过，消息随会话成批导入）；
ideas/schedule 按 (user_id, id) 判重；pending 按 question_id 判重。
重复执行不产生重复记录，报告 导入/跳过 计数。

用法（需用 apps/api 的 venv 运行——依赖 psycopg；路径默认相对本脚本解析）：
    apps/api/.venv/Scripts/python.exe apps/scripts/migrate_files_to_pg.py [--apps-root <path>] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

APPS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APPS_ROOT / "api"))

from zimeiti_api.core import pg  # noqa: E402  （path 注入后再 import）


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def migrate(apps_root: Path, dry_run: bool = False,
            user_id: str = pg.DEFAULT_USER) -> dict:
    sessions_dir = apps_root / "sessions"
    outputs_dir = apps_root / "outputs"
    imported = {"sessions": 0, "messages": 0, "pending": 0, "ideas": 0, "schedule": 0}
    skipped = {"sessions": 0, "pending": 0, "ideas": 0, "schedule": 0}

    # 1) 会话历史：每个 <key>.json 一个会话（跳过 pending_questions.json 本身）
    if sessions_dir.is_dir():
        for f in sorted(sessions_dir.glob("*.json")):
            if f.name == "pending_questions.json":
                continue
            key = f.stem
            data = _load_json(f)
            msgs = data.get("messages", []) if isinstance(data, dict) else []
            if not isinstance(msgs, list):
                msgs = []
            if pg.session_exists(key, user_id=user_id):
                skipped["sessions"] += 1
                continue
            if dry_run:
                imported["sessions"] += 1
                imported["messages"] += len([m for m in msgs if m.get("content")])
                continue
            pg.messages_save(key, msgs, user_id=user_id)   # 事务内 DELETE+INSERT+建会话行
            imported["sessions"] += 1
            imported["messages"] += len([m for m in msgs if m.get("content")])

    # 2) HITL pending：过期项（超 TTL）不导
    pf = sessions_dir / "pending_questions.json"
    if pf.is_file():
        raw = _load_json(pf)
        if isinstance(raw, dict):
            now = time.time()
            for qid, payload in raw.items():
                if not isinstance(payload, dict):
                    continue
                if now - payload.get("created_at", now) >= pg.PENDING_TTL_SECONDS:
                    continue
                if pg.pending_exists(qid):
                    skipped["pending"] += 1
                    continue
                if not dry_run:
                    pg.pending_set(qid, payload.get("thread_id", ""), payload, user_id=user_id)
                imported["pending"] += 1

    # 3) ideas：按 (user_id, id) 判重
    ideas_file = outputs_dir / "_ideas.json"
    if ideas_file.is_file():
        items = _load_json(ideas_file)
        if isinstance(items, list):
            existing = {i["id"] for i in pg.ideas_list(user_id=user_id)} if not dry_run else set()
            for it in items:
                if not isinstance(it, dict) or not it.get("id"):
                    continue
                if it["id"] in existing:
                    skipped["ideas"] += 1
                    continue
                if not dry_run:
                    pg.ideas_insert(it, user_id=user_id)
                existing.add(it["id"])
                imported["ideas"] += 1

    # 4) schedule_items：按 (user_id, id) 判重
    sched_file = outputs_dir / "_schedule.json"
    if sched_file.is_file():
        items = _load_json(sched_file)
        if isinstance(items, list):
            existing = {i["id"] for i in pg.schedule_list(user_id=user_id)} if not dry_run else set()
            for it in items:
                if not isinstance(it, dict) or not it.get("id"):
                    continue
                if it["id"] in existing:
                    skipped["schedule"] += 1
                    continue
                if not dry_run:
                    pg.schedule_insert(it, user_id=user_id)
                existing.add(it["id"])
                imported["schedule"] += 1

    return {"imported": imported, "skipped": skipped}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apps-root", default=str(APPS_ROOT),
                    help="apps 目录（含 sessions/ 与 outputs/），默认相对本脚本解析")
    ap.add_argument("--dry-run", action="store_true", help="只报告将导入什么，不写库")
    args = ap.parse_args()

    ok, err = pg.verify()
    if not ok:
        print(f"PostgreSQL 不可用: {err}\nDATABASE_URL = {pg.database_url()}", file=sys.stderr)
        return 2

    result = migrate(Path(args.apps_root), dry_run=args.dry_run)
    tag = "[dry-run] " if args.dry_run else ""
    print(f"{tag}导入: {result['imported']}")
    print(f"{tag}跳过: {result['skipped']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
