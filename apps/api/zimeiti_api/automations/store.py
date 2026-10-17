"""定时自动化存储（model-resilience-cron，design D2/D3）。

PG 表 automations：任务配置持久化，服务重启不丢；next_run 持久化 + 执行租约
防重启竞态。任务执行与 API 进程同生命周期（本地场景，文档注明）。
"""

from __future__ import annotations

import time
import uuid
from contextlib import contextmanager
from typing import Any

from ..core import pg

_DDL = """
CREATE TABLE IF NOT EXISTS automations (
    seq       BIGSERIAL,
    id        TEXT NOT NULL,
    user_id   TEXT NOT NULL DEFAULT 'local',
    name      TEXT NOT NULL,
    kind      TEXT NOT NULL DEFAULT 'case',     -- case=运营脚本 / prompt=预置指令 / flow=运营流程
    schedule  TEXT NOT NULL,                    -- cron 五段式 或 HH:MM 每日时刻
    payload   TEXT NOT NULL DEFAULT '',         -- case=脚本参数 / prompt=指令文本
    enabled   BOOLEAN NOT NULL DEFAULT TRUE,
    last_run  BIGINT NOT NULL DEFAULT 0,
    next_run  BIGINT NOT NULL DEFAULT 0,
    lease     BIGINT NOT NULL DEFAULT 0,        -- 执行租约到期时间（防重启竞态）
    created   BIGINT NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, id)
);
CREATE TABLE IF NOT EXISTS automation_runs (
    seq       BIGSERIAL,
    id        TEXT NOT NULL,
    user_id   TEXT NOT NULL DEFAULT 'local',
    auto_id   TEXT NOT NULL,
    status    TEXT NOT NULL DEFAULT 'running',  -- running/done/failed
    summary   TEXT NOT NULL DEFAULT '',
    started   BIGINT NOT NULL DEFAULT 0,
    finished  BIGINT NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, id)
);
"""

_LEASE_SECONDS = 30 * 60  # 执行租约：超时未续约的任务可被重新拾取


@contextmanager
def _conn():
    with pg.connect() as conn:
        yield conn


def _exec(sql: str, params: tuple | None = None) -> None:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
        conn.commit()


def setup() -> None:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(_DDL)
        conn.commit()


def _row(r: tuple) -> dict:
    return {
        "id": r[0],
        "name": r[1],
        "kind": r[2],
        "schedule": r[3],
        "payload": r[4],
        "enabled": r[5],
        "last_run": r[6],
        "next_run": r[7],
        "created": r[8],
    }


def list_all() -> list[dict]:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, kind, schedule, payload, enabled, last_run, next_run, created"
                " FROM automations ORDER BY created DESC"
            )
            return [_row(r) for r in cur.fetchall()]


def create(name: str, kind: str, schedule: str, payload: str = "", next_run: int = 0) -> str:
    aid = uuid.uuid4().hex[:12]
    _exec(
        "INSERT INTO automations (id, name, kind, schedule, payload, next_run, created)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (aid, name, kind, schedule, payload, int(next_run), int(time.time())),
    )
    return aid


_UPDATABLE = {"name", "enabled", "schedule", "payload", "next_run", "last_run", "lease"}


def update(aid: str, **fields: Any) -> bool:
    if not fields:
        return False
    bad = set(fields) - _UPDATABLE
    if bad:
        raise ValueError(f"不可更新列: {bad}")
    sets = ", ".join(f"{k} = %s" for k in fields)
    _exec(
        f"UPDATE automations SET {sets} WHERE id = %s",  # nosec B608  列名白名单+值参数化
        (*fields.values(), aid),
    )
    return True


def delete(aid: str) -> bool:
    _exec("DELETE FROM automations WHERE id = %s", (aid,))
    _exec("DELETE FROM automation_runs WHERE auto_id = %s", (aid,))
    return True


def due(now: int) -> list[dict]:
    """到点且租约过期的任务（重启后过期租约自动重排）。"""
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, kind, schedule, payload, enabled, last_run, next_run, created"
                " FROM automations WHERE enabled AND next_run > 0 AND next_run <= %s"
                " AND lease < %s",
                (int(now), int(now)),
            )
            return [_row(r) for r in cur.fetchall()]


def take_lease(aid: str, now: int) -> bool:
    """抢占执行租约（仅当租约仍过期时成功）。"""
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE automations SET lease = %s WHERE id = %s AND lease < %s",
                (int(now) + _LEASE_SECONDS, aid, int(now)),
            )
            n = cur.rowcount
        conn.commit()
    return n > 0


def run_start(auto_id: str) -> str:
    rid = uuid.uuid4().hex[:12]
    _exec(
        "INSERT INTO automation_runs (id, auto_id, status, started) VALUES (%s, %s, 'running', %s)",
        (rid, auto_id, int(time.time())),
    )
    return rid


def run_finish(rid: str, status: str, summary: str) -> None:
    _exec(
        "UPDATE automation_runs SET status = %s, summary = %s, finished = %s WHERE id = %s",
        (status, summary[:2000], int(time.time()), rid),
    )


def list_runs(auto_id: str | None = None, limit: int = 20) -> list[dict]:
    sql = (
        "SELECT r.id, r.auto_id, a.name, r.status, r.summary, r.started, r.finished"
        " FROM automation_runs r LEFT JOIN automations a ON a.id = r.auto_id"
    )
    params: tuple = ()
    if auto_id:
        sql += " WHERE r.auto_id = %s"
        params = (auto_id,)
    sql += " ORDER BY r.started DESC LIMIT %s"
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (*params, int(limit)))
            return [
                {
                    "id": r[0],
                    "auto_id": r[1],
                    "name": r[2],
                    "status": r[3],
                    "summary": r[4],
                    "started": r[5],
                    "finished": r[6],
                }
                for r in cur.fetchall()
            ]
