"""运营流程持久化（autonomous-flow）：flows / flow_runs / flow_steps 三表。

沿用 automations/store.py 的范式（同步 cursor + 幂等 DDL + user_id 命名空间）。
设计取舍：流程定义与执行记录分开两表，步骤级记录独立成表以便逐步追溯。
"""

from __future__ import annotations

import json
import time
import uuid
from contextlib import contextmanager
from typing import Any

from zimeiti_api.core import pg

_DDL = """
CREATE TABLE IF NOT EXISTS flows (
    seq       BIGSERIAL,
    id        TEXT NOT NULL,
    user_id   TEXT NOT NULL DEFAULT 'local',
    name      TEXT NOT NULL,
    steps     TEXT NOT NULL,                    -- JSON 数组（有序子集）
    schedule  TEXT NOT NULL DEFAULT '',         -- cron 五段式 或 HH:MM
    config    TEXT NOT NULL DEFAULT '{}',       -- JSON：topic/platform/draft_only...
    enabled   BOOLEAN NOT NULL DEFAULT TRUE,
    created   BIGINT NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, id)
);
CREATE TABLE IF NOT EXISTS flow_runs (
    seq        BIGSERIAL,
    id         TEXT NOT NULL,
    user_id    TEXT NOT NULL DEFAULT 'local',
    flow_id    TEXT NOT NULL,
    status     TEXT NOT NULL DEFAULT 'running', -- running/done/failed
    failed_step TEXT NOT NULL DEFAULT '',
    duration_ms INTEGER NOT NULL DEFAULT 0,
    started    BIGINT NOT NULL DEFAULT 0,
    finished   BIGINT NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, id)
);
CREATE TABLE IF NOT EXISTS flow_steps (
    seq         BIGSERIAL,
    run_id      TEXT NOT NULL,
    user_id     TEXT NOT NULL DEFAULT 'local',
    step        TEXT NOT NULL,
    idx         INTEGER NOT NULL,
    status      TEXT NOT NULL DEFAULT 'running', -- running/done/failed
    output_path TEXT NOT NULL DEFAULT '',
    summary     TEXT NOT NULL DEFAULT '',
    error       TEXT NOT NULL DEFAULT '',
    duration_ms INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, run_id, idx)
);
"""

_USER = "local"


@contextmanager
def _conn():
    with pg.connect() as conn:
        yield conn


def setup() -> None:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(_DDL)
        conn.commit()


def _json_loads(s: str, default: Any) -> Any:
    try:
        return json.loads(s) if s else default
    except Exception:  # noqa: BLE001
        return default


def create_flow(name: str, steps: list[str], schedule: str = "", config: dict | None = None) -> str:
    from .flows import validate_steps  # 局部导入避免循环（flows 无依赖）

    validate_steps(steps)
    fid = uuid.uuid4().hex[:12]
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO flows (id, user_id, name, steps, schedule, config, enabled, created)"
                " VALUES (%s, %s, %s, %s, %s, %s, TRUE, %s)",
                (
                    fid,
                    _USER,
                    name,
                    json.dumps(steps, ensure_ascii=False),
                    schedule,
                    json.dumps(config or {}, ensure_ascii=False),
                    int(time.time() * 1000),
                ),
            )
        conn.commit()
    return fid


def get_flow(flow_id: str) -> dict | None:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, steps, schedule, config, enabled FROM flows"
                " WHERE user_id=%s AND id=%s",
                (_USER, flow_id),
            )
            r = cur.fetchone()
    if not r:
        return None
    return {
        "id": r[0],
        "name": r[1],
        "steps": _json_loads(r[2], []),
        "schedule": r[3],
        "config": _json_loads(r[4], {}),
        "enabled": r[5],
    }


def list_flows() -> list[dict]:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, steps, schedule, config, enabled FROM flows"
                " WHERE user_id=%s ORDER BY created DESC",
                (_USER,),
            )
            rows = cur.fetchall()
    return [
        {
            "id": r[0],
            "name": r[1],
            "steps": _json_loads(r[2], []),
            "schedule": r[3],
            "config": _json_loads(r[4], {}),
            "enabled": r[5],
        }
        for r in rows
    ]


def delete_flow(flow_id: str) -> None:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM flows WHERE user_id=%s AND id=%s", (_USER, flow_id))
        conn.commit()


def list_runs(flow_id: str | None = None, limit: int = 20) -> list[dict]:
    """执行记录（含逐步明细），按开始时间倒序；limit 限制条数。"""
    lim = max(1, min(int(limit), 100))
    with _conn() as conn:
        with conn.cursor() as cur:
            if flow_id:
                cur.execute(
                    "SELECT id, flow_id, status, failed_step, duration_ms, started, finished"
                    " FROM flow_runs WHERE user_id=%s AND flow_id=%s"
                    " ORDER BY started DESC LIMIT %s",
                    (_USER, flow_id, lim),
                )
            else:
                cur.execute(
                    "SELECT id, flow_id, status, failed_step, duration_ms, started, finished"
                    " FROM flow_runs WHERE user_id=%s ORDER BY started DESC LIMIT %s",
                    (_USER, lim),
                )
            runs = cur.fetchall()
            out: list[dict] = []
            for r in runs:
                cur.execute(
                    "SELECT step, idx, status, output_path, summary, error, duration_ms"
                    " FROM flow_steps WHERE user_id=%s AND run_id=%s ORDER BY idx",
                    (_USER, r[0]),
                )
                steps = [
                    {
                        "step": s[0],
                        "index": s[1],
                        "status": s[2],
                        "output_path": s[3],
                        "summary": s[4],
                        "error": s[5],
                        "duration_ms": s[6],
                    }
                    for s in cur.fetchall()
                ]
                out.append(
                    {
                        "id": r[0],
                        "flow_id": r[1],
                        "status": r[2],
                        "failed_step": r[3],
                        "duration_ms": r[4],
                        "started": r[5],
                        "finished": r[6],
                        "steps": steps,
                    }
                )
    return out


def save_run(flow_id: str, res: dict) -> str:
    """落一次执行结果（flow_runs + flow_steps）。"""
    rid = uuid.uuid4().hex[:12]
    now = int(time.time() * 1000)
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO flow_runs (id, user_id, flow_id, status, failed_step, duration_ms,"
                " started, finished) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    rid,
                    _USER,
                    flow_id,
                    res.get("status", "failed"),
                    res.get("failed_step", ""),
                    int(res.get("duration_ms", 0)),
                    now,
                    now,
                ),
            )
            for s in res.get("steps", []):
                cur.execute(
                    "INSERT INTO flow_steps (run_id, user_id, step, idx, status, output_path,"
                    " summary, error, duration_ms) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        rid,
                        _USER,
                        s.get("step", ""),
                        int(s.get("index", 0)),
                        s.get("status", "failed"),
                        s.get("output_path", ""),
                        s.get("summary", ""),
                        s.get("error", ""),
                        int(s.get("duration_ms", 0)),
                    ),
                )
        conn.commit()
    return rid
