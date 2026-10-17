"""记忆存储层（agent-memory-system）。

PG 两张表：
- memory_entries：内容 + 溯源分级（origin_class：owner=用户明确陈述 / agent=agent
  凝练 / system=系统事件）+ scope（curated/episodic）+ importance + tags
- memory_injections：注入去重日志（recall-loop 预防——同一会话已注入的条目
  不再重复返回；新会话可重新注入，跨会话复用正是目的）

业务操作用同步 psycopg（与 pg.py 其余业务函数同范式）。
"""

from __future__ import annotations

import time
import uuid
from contextlib import contextmanager
from typing import Any

from zimeiti_api.core import pg

ORIGINS = ("owner", "agent", "system")  # 白名单：模型无法经 prose 写入任意 origin
SCOPES = ("curated", "episodic")
_FLUSH_THRESHOLD = 30  # 消息数超过才 flush（design D3）
_FLUSH_TAIL = 6  # 取最后 N 条
_FLUSH_CHARS = 500  # 每条截断字符数

_DDL = """
CREATE TABLE IF NOT EXISTS memory_entries (
    seq          BIGSERIAL,
    id           TEXT NOT NULL,
    user_id      TEXT NOT NULL DEFAULT 'local',
    content      TEXT NOT NULL,
    origin_class TEXT NOT NULL DEFAULT 'agent',
    scope        TEXT NOT NULL DEFAULT 'curated',
    importance   INTEGER NOT NULL DEFAULT 5,
    tags         TEXT[] NOT NULL DEFAULT '{}',
    created      BIGINT NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, id)
);
CREATE TABLE IF NOT EXISTS memory_injections (
    session_key TEXT NOT NULL,
    entry_id    TEXT NOT NULL,
    injected    BIGINT NOT NULL DEFAULT 0,
    PRIMARY KEY (session_key, entry_id)
);
"""


@contextmanager
def _conn():
    with pg.connect() as conn:  # 复用数据层同步连接上下文
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


def record(
    content: str,
    origin: str = "agent",
    importance: int = 5,
    tags: list[str] | None = None,
    scope: str = "curated",
) -> str:
    """记录一条记忆。origin 必须在 ORIGINS 白名单（防 prose 注入伪造溯源）。"""
    if origin not in ORIGINS:
        raise ValueError(f"origin 必须是 {ORIGINS} 之一（收到 {origin!r}）")
    if scope not in SCOPES:
        raise ValueError(f"scope 必须是 {SCOPES} 之一（收到 {scope!r}）")
    eid = uuid.uuid4().hex[:12]
    _exec(
        "INSERT INTO memory_entries (id, content, origin_class, scope, importance, tags, created)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (eid, content.strip(), origin, scope, int(importance), tags or [], int(time.time())),
    )
    return eid


def search(
    query: str, session_key: str | None = None, limit: int = 8, scope: str | None = None
) -> list[dict]:
    """检索记忆（子串匹配，按 importance+时间排序）；同会话已注入的条目过滤。"""
    sql = (
        "SELECT id, content, origin_class, scope, importance, tags, created"
        " FROM memory_entries WHERE content ILIKE %s"
    )
    params: list[Any] = [f"%{query.strip()}%"]
    if scope:
        sql += " AND scope = %s"
        params.append(scope)
    if session_key:
        sql += " AND id NOT IN (SELECT entry_id FROM memory_injections WHERE session_key = %s)"
        params.append(session_key)
    sql += " ORDER BY importance DESC, created DESC LIMIT %s"
    params.append(int(limit))
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()
    return [
        {
            "id": r[0],
            "content": r[1],
            "origin": r[2],
            "scope": r[3],
            "importance": r[4],
            "tags": list(r[5] or []),
            "created_at": r[6],
        }
        for r in rows
    ]


def mark_injected(session_key: str, entry_id: str) -> None:
    _exec(
        "INSERT INTO memory_injections (session_key, entry_id, injected) VALUES (%s, %s, %s)"
        " ON CONFLICT DO NOTHING",
        (session_key, entry_id, int(time.time())),
    )


def is_injected(session_key: str, entry_id: str) -> bool:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM memory_injections WHERE session_key = %s AND entry_id = %s",
                (session_key, entry_id),
            )
            return cur.fetchone() is not None


def delete_session_injections(session_key: str) -> None:
    """会话删除时级联清理（注入日志随会话生命周期）。"""
    _exec("DELETE FROM memory_injections WHERE session_key = %s", (session_key,))
