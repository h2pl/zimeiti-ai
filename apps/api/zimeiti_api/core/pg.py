"""PostgreSQL 数据层（pg-data-layer 变更）。

落地「记录型数据进 PG、文档型数据留文件」的取舍（变更 brief：
docs/comet/changes/pg-data-layer/brief.md）：

进 PG：会话历史（chat_sessions/chat_messages）、LangGraph checkpoints
（AsyncPostgresSaver，thread_id 命名空间隔离）、HITL pending（hitl_pending）、
ideas、schedule_items。
留文件：画像 md、技能 SKILL.md、登录标记/发布状态/cookies、outputs 媒体
（见 brief「保留文件」节，本模块不触及）。

多租户预留：所有业务表带 user_id（本地版 DEFAULT 'local'）；Phase 3 多租户
化时填值而非改表。checkpoint 表为 langgraph 官方表（无 user_id 列），经
thread_id = "<user_id>:<session_key>" 命名空间隔离。

连接：DATABASE_URL 环境变量（可由 .env 提供；app.py 的 dotenv 加载先于
本模块首次调用——故一律懒解析，不在 import 期读环境）。
缺省值对应新建专用库 zimeiti-ai（角色/口令沿用旧 zimeiti 默认值）。

Windows 注意：psycopg 异步不能用默认 ProactorEventLoop，须
WindowsSelectorEventLoopPolicy——由 app.py 在 import 期设置（旧 zimeiti
踩坑结论，psycopg 3.3 实测仍如此）。

业务操作用同步 psycopg（agent_runtime 的历史/待答函数本就在异步上下文里
同步调用，切换存储后签名不变）；checkpointer 因 langgraph 异步图必须用
AsyncPostgresSaver。
"""

from __future__ import annotations

import json
import os
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import psycopg

DEFAULT_DATABASE_URL = "postgresql://zimeiti:zimeiti_dev@localhost:5432/zimeiti-ai"
DEFAULT_USER = "local"
PENDING_TTL_SECONDS = 30 * 60  # 与文件版 agent_runtime.TTL_SECONDS 一致


def database_url() -> str:
    """懒解析连接串：dotenv 可能在模块 import 之后才加载。"""
    return os.environ.get("DATABASE_URL") or DEFAULT_DATABASE_URL


@contextmanager
def connect() -> Iterator[psycopg.Connection]:
    """同步连接上下文（本地单用户低并发，按操作建连；psycopg 连接建立约毫秒级）。"""
    conn = psycopg.connect(database_url(), connect_timeout=5)
    try:
        yield conn
    finally:
        conn.close()


# ---------- DDL（幂等） ----------

_DDL = [
    """
    CREATE TABLE IF NOT EXISTS chat_sessions (
        user_id     TEXT NOT NULL DEFAULT 'local',
        session_key TEXT NOT NULL,
        created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
        PRIMARY KEY (user_id, session_key)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS chat_messages (
        id          BIGSERIAL PRIMARY KEY,
        user_id     TEXT NOT NULL DEFAULT 'local',
        session_key TEXT NOT NULL,
        role        TEXT NOT NULL,
        content     TEXT NOT NULL,
        created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_chat_messages_session "
    "ON chat_messages (user_id, session_key, id)",
    """
    CREATE TABLE IF NOT EXISTS hitl_pending (
        question_id TEXT PRIMARY KEY,
        user_id     TEXT NOT NULL DEFAULT 'local',
        session_key TEXT NOT NULL,
        payload     JSONB NOT NULL,
        created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ideas (
        seq     BIGSERIAL,
        id      TEXT NOT NULL,
        user_id TEXT NOT NULL DEFAULT 'local',
        title   TEXT NOT NULL DEFAULT '未命名选题',
        note    TEXT NOT NULL DEFAULT '',
        source  TEXT NOT NULL DEFAULT '',
        status  TEXT NOT NULL DEFAULT 'pending',
        created BIGINT NOT NULL DEFAULT 0,
        PRIMARY KEY (user_id, id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS schedule_items (
        seq       BIGSERIAL,
        id        TEXT NOT NULL,
        user_id   TEXT NOT NULL DEFAULT 'local',
        title     TEXT NOT NULL DEFAULT '未命名',
        date      TEXT NOT NULL DEFAULT '',
        platform  TEXT NOT NULL DEFAULT '',
        time      TEXT NOT NULL DEFAULT '',
        status    TEXT NOT NULL DEFAULT 'idea',
        note      TEXT NOT NULL DEFAULT '',
        kind      TEXT NOT NULL DEFAULT 'content',
        url       TEXT NOT NULL DEFAULT '',
        source    TEXT NOT NULL DEFAULT 'manual',
        event_type TEXT NOT NULL DEFAULT '',
        end_date  TEXT NOT NULL DEFAULT '',
        PRIMARY KEY (user_id, id)
    )
    """,
]


def setup() -> None:
    """建表（幂等）。重复执行不报错、不丢数据。"""
    with connect() as conn:
        for stmt in _DDL:
            conn.execute(stmt)
        conn.commit()


def verify() -> tuple[bool, str]:
    """连通性校验：返回 (ok, 错误信息)。供启动 fail-fast 用。"""
    try:
        with connect() as conn:
            conn.execute("SELECT 1")
        return True, ""
    except Exception as e:  # noqa: BLE001 - 启动校验需要兜底所有连接错误
        return False, f"{type(e).__name__}: {e}"


# ---------- checkpointer（langgraph 官方 PG saver） ----------

_CHECKPOINTER: Any = None
_POOL: Any = None


async def setup_checkpointer() -> Any:
    """创建（并缓存）AsyncPostgresSaver + 连接池，建好 checkpoint 表。

    参考: langgraph-checkpoint-postgres AsyncPostgresSaver。官方
    from_conn_string 用 autocommit=True 建连（其 MIGRATIONS 含
    CREATE INDEX CONCURRENTLY，不能跑在事务块里），pool 连接经 configure
    对齐同样参数（autocommit / prepare_threshold=0 / dict_row）。
    不直接用 from_conn_string 是因为它是上下文管理器、生命周期绑定
    with 块；这里要随应用常驻，故自持 AsyncConnectionPool。
    """
    global _CHECKPOINTER, _POOL
    if _CHECKPOINTER is not None:
        return _CHECKPOINTER
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from psycopg.rows import dict_row
    from psycopg_pool import AsyncConnectionPool

    async def _configure(conn):
        conn.prepare_threshold = 0
        conn.row_factory = dict_row
        await conn.set_autocommit(True)  # 异步连接的 autocommit 只读，须 await set；
        # 对齐官方 from_conn_string（setup 的 CONCURRENTLY 禁事务）

    _POOL = AsyncConnectionPool(database_url(), open=False, configure=_configure)
    await _POOL.open(wait=True, timeout=10)
    saver = AsyncPostgresSaver(_POOL)
    await saver.setup()
    _CHECKPOINTER = saver
    return saver


async def close_checkpointer() -> None:
    global _CHECKPOINTER, _POOL
    if _POOL is not None:
        await _POOL.close()
    _CHECKPOINTER, _POOL = None, None


def get_checkpointer() -> Any:
    """已缓存的 checkpoint saver（未初始化返回 None；正常路径由 lifespan 先 setup）。"""
    return _CHECKPOINTER


def thread_id(session_key: str, user_id: str = DEFAULT_USER) -> str:
    """checkpoint thread_id：租户命名空间隔离（本地版即 '<local>:<key>'）。"""
    return f"{user_id}:{session_key}"


# ---------- 会话历史 ----------


def session_touch(session_key: str, user_id: str = DEFAULT_USER) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO chat_sessions (user_id, session_key) VALUES (%s, %s)
            ON CONFLICT (user_id, session_key) DO UPDATE SET updated_at = now()
            """,
            (user_id, session_key),
        )
        conn.commit()


def messages_load(session_key: str, user_id: str = DEFAULT_USER) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT role, content FROM chat_messages "
            "WHERE user_id=%s AND session_key=%s ORDER BY id",
            (user_id, session_key),
        ).fetchall()
    return [{"role": r[0], "content": r[1]} for r in rows]


def messages_save(session_key: str, messages: list[dict], user_id: str = DEFAULT_USER) -> None:
    """整表替换语义（与文件版一致：落盘历史整体重写）。"""
    with connect() as conn:
        with conn.transaction():
            conn.execute(
                "DELETE FROM chat_messages WHERE user_id=%s AND session_key=%s",
                (user_id, session_key),
            )
            for m in messages:
                if m.get("content"):
                    conn.execute(
                        "INSERT INTO chat_messages (user_id, session_key, role, content) "
                        "VALUES (%s,%s,%s,%s)",
                        (user_id, session_key, m.get("role", "user"), m["content"]),
                    )
            conn.execute(
                """
                INSERT INTO chat_sessions (user_id, session_key) VALUES (%s, %s)
                ON CONFLICT (user_id, session_key) DO UPDATE SET updated_at = now()
                """,
                (user_id, session_key),
            )


def session_delete(session_key: str, user_id: str = DEFAULT_USER) -> bool:
    """删除会话全部状态：消息 + 会话行。checkpoint 由调用方经 adelete_thread 删。"""
    with connect() as conn:
        with conn.transaction():
            cur_msgs = conn.execute(
                "DELETE FROM chat_messages WHERE user_id=%s AND session_key=%s",
                (user_id, session_key),
            )
            cur_sess = conn.execute(
                "DELETE FROM chat_sessions WHERE user_id=%s AND session_key=%s",
                (user_id, session_key),
            )
    return bool((cur_msgs.rowcount or 0) + (cur_sess.rowcount or 0))


def session_exists(session_key: str, user_id: str = DEFAULT_USER) -> bool:
    """导入脚本幂等判断：会话已存在即视为已导入（消息随会话成批导入）。"""
    with connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM chat_sessions WHERE user_id=%s AND session_key=%s",
            (user_id, session_key),
        ).fetchone()
    return row is not None


# ---------- HITL pending（带 TTL，与文件版语义一致） ----------


def pending_set(
    question_id: str, session_key: str, payload: dict, user_id: str = DEFAULT_USER
) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO hitl_pending (question_id, user_id, session_key, payload)
            VALUES (%s,%s,%s,%s)
            ON CONFLICT (question_id) DO UPDATE SET payload=EXCLUDED.payload, created_at=now()
            """,
            (
                question_id,
                user_id,
                session_key,
                json.dumps(payload, ensure_ascii=False),
            ),
        )
        conn.commit()


def pending_del(question_id: str) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM hitl_pending WHERE question_id=%s", (question_id,))
        conn.commit()


def pending_delete_by_session(session_key: str, user_id: str = DEFAULT_USER) -> int:
    """删除某 session 的全部 pending（删会话时联动清尽，A9）。返回删除行数。"""
    with connect() as conn:
        cur = conn.execute(
            "DELETE FROM hitl_pending WHERE user_id=%s AND session_key=%s",
            (user_id, session_key),
        )
        conn.commit()
    return cur.rowcount or 0


def pending_exists(question_id: str) -> bool:
    """导入脚本幂等判断（不做过期过滤：过期行覆写无副作用，但不重复计数）。"""
    with connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM hitl_pending WHERE question_id=%s", (question_id,)
        ).fetchone()
    return row is not None


def _pending_alive_where() -> str:
    # noqa: UP031 —— %s 是 psycopg 占位符不是 %-format，禁止改 f-string
    return "created_at > now() - interval '%s seconds'" % PENDING_TTL_SECONDS  # noqa: UP031


def pending_load(user_id: str = DEFAULT_USER) -> dict:
    """全部未过期 pending（TTL 过滤在 SQL 侧做）。"""
    with connect() as conn:
        rows = conn.execute(
            f"SELECT question_id, payload FROM hitl_pending "
            f"WHERE user_id=%s AND {_pending_alive_where()}",  # nosec B608 —— WHERE 片段为模块级常量函数（int TTL），用户值走 %s 参数化
            (user_id,),
        ).fetchall()
    return {r[0]: r[1] for r in rows}


def pending_get(question_id: str, user_id: str = DEFAULT_USER) -> dict | None:
    with connect() as conn:
        row = conn.execute(
            f"SELECT payload FROM hitl_pending "
            f"WHERE question_id=%s AND user_id=%s AND {_pending_alive_where()}",  # nosec B608 —— WHERE 片段为模块级常量函数（int TTL），用户值走 %s 参数化
            (question_id, user_id),
        ).fetchone()
    return row[0] if row else None


def pending_status(question_ids: list[str], user_id: str = DEFAULT_USER) -> dict[str, dict]:
    if not question_ids:
        return {}
    with connect() as conn:
        rows = conn.execute(  # nosec B608 —— 常量 WHERE 片段 + ANY(%s) 参数化
            f"SELECT question_id FROM hitl_pending "
            f"WHERE user_id=%s AND question_id = ANY(%s) AND {_pending_alive_where()}",  # nosec B608 —— WHERE 片段为模块级常量（int TTL），用户值走 %s 参数化
            (user_id, question_ids),
        ).fetchall()
    alive = {r[0] for r in rows}
    return {qid: {"status": "pending" if qid in alive else "not_found"} for qid in question_ids}


# ---------- ideas ----------


def ideas_list(user_id: str = DEFAULT_USER) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, title, note, source, status, created FROM ideas "
            "WHERE user_id=%s ORDER BY seq DESC",
            (user_id,),
        ).fetchall()
    return [
        {
            "id": r[0],
            "title": r[1],
            "note": r[2],
            "source": r[3],
            "status": r[4],
            "created": r[5],
        }
        for r in rows
    ]


def ideas_insert(item: dict, user_id: str = DEFAULT_USER) -> dict:
    row = {
        "id": item.get("id") or uuid.uuid4().hex[:12],
        "title": item.get("title", ""),
        "note": item.get("note", ""),
        "source": item.get("source", ""),
        "status": item.get("status", "pending"),
        "created": item.get("created") or int(time.time()),
    }
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO ideas (id, user_id, title, note, source, status, created)
            VALUES (%(id)s,%(user_id)s,%(title)s,%(note)s,%(source)s,%(status)s,%(created)s)
            ON CONFLICT (user_id, id) DO NOTHING
            """,
            {**row, "user_id": user_id},
        )
        conn.commit()
    return row


def ideas_update(iid: str, fields: dict, user_id: str = DEFAULT_USER) -> dict | None:
    allowed = {"title", "note", "source", "status"}
    sets = {k: v for k, v in fields.items() if k in allowed}
    if not sets:
        return None
    assignments = ", ".join(f"{k}=%({k})s" for k in sets)
    with connect() as conn:
        row = conn.execute(
            f"UPDATE ideas SET {assignments} WHERE user_id=%(user_id)s AND id=%(id)s "  # nosec B608 —— 列名经白名单过滤、值走 %(k)s 参数化，无注入面
            "RETURNING id, title, note, source, status, created",
            {**sets, "user_id": user_id, "id": iid},
        ).fetchone()
        conn.commit()
    if not row:
        return None
    return {
        "id": row[0],
        "title": row[1],
        "note": row[2],
        "source": row[3],
        "status": row[4],
        "created": row[5],
    }


def ideas_delete(iid: str, user_id: str = DEFAULT_USER) -> bool:
    with connect() as conn:
        cur = conn.execute("DELETE FROM ideas WHERE user_id=%s AND id=%s", (user_id, iid))
        conn.commit()
    return bool(cur.rowcount)


# ---------- schedule ----------

_SCHEDULE_FIELDS = (
    "title",
    "date",
    "platform",
    "time",
    "status",
    "note",
    "kind",
    "url",
    "source",
    "event_type",
    "end_date",
)


def _schedule_row(r) -> dict:
    return {
        "id": r[0],
        "title": r[1],
        "date": r[2],
        "platform": r[3],
        "time": r[4],
        "status": r[5],
        "note": r[6],
        "kind": r[7],
        "url": r[8],
        "source": r[9],
        "event_type": r[10],
        "end_date": r[11],
    }


def schedule_list(user_id: str = DEFAULT_USER) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, title, date, platform, time, status, note, "
            "kind, url, source, event_type, end_date "
            "FROM schedule_items WHERE user_id=%s ORDER BY seq",
            (user_id,),
        ).fetchall()
    return [_schedule_row(r) for r in rows]


def schedule_insert(item: dict, user_id: str = DEFAULT_USER) -> dict:
    row = {"id": item.get("id") or uuid.uuid4().hex[:12]}
    for f in _SCHEDULE_FIELDS:
        row[f] = item.get(f, "")
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO schedule_items (id, user_id, title, date, platform, time, status,
                                        note, kind, url, source, event_type, end_date)
            VALUES (%(id)s,%(user_id)s,%(title)s,%(date)s,%(platform)s,%(time)s,%(status)s,
                    %(note)s,%(kind)s,%(url)s,%(source)s,%(event_type)s,%(end_date)s)
            ON CONFLICT (user_id, id) DO NOTHING
            """,
            {**row, "user_id": user_id},
        )
        conn.commit()
    return row


def schedule_update(sid: str, fields: dict, user_id: str = DEFAULT_USER) -> dict | None:
    sets = {k: v for k, v in fields.items() if k in _SCHEDULE_FIELDS}
    if not sets:
        return None
    assignments = ", ".join(f"{k}=%({k})s" for k in sets)
    with connect() as conn:
        row = conn.execute(
            f"UPDATE schedule_items SET {assignments} WHERE user_id=%(user_id)s AND id=%(id)s "  # nosec B608 —— 列名经白名单过滤、值走 %(k)s 参数化，无注入面
            "RETURNING id, title, date, platform, time, status, "
            "note, kind, url, source, event_type, end_date",
            {**sets, "user_id": user_id, "id": sid},
        ).fetchone()
        conn.commit()
    return _schedule_row(row) if row else None


def schedule_delete(sid: str, user_id: str = DEFAULT_USER) -> bool:
    with connect() as conn:
        cur = conn.execute("DELETE FROM schedule_items WHERE user_id=%s AND id=%s", (user_id, sid))
        conn.commit()
    return bool(cur.rowcount)


# ---------- 整表替换（read-modify-write 调用方的 PG 等价，事务内 DELETE+INSERT） ----------


def ideas_replace_all(items: list[dict], user_id: str = DEFAULT_USER) -> None:
    """整表替换 ideas。

    调用方传入的是展示序（最新在前）；BIGSERIAL 按插入序递增，故反序插入，
    使列表首项拿到最大 seq，读回 ORDER BY seq DESC 才能还原原顺序。
    """
    with connect() as conn:
        with conn.transaction():
            conn.execute("DELETE FROM ideas WHERE user_id=%s", (user_id,))
            for it in reversed(items):
                conn.execute(
                    """
                    INSERT INTO ideas (id, user_id, title, note, source, status, created)
                    VALUES (%(id)s,%(user_id)s,%(title)s,%(note)s,%(source)s,%(status)s,%(created)s)
                    """,
                    {
                        "id": it.get("id") or uuid.uuid4().hex[:12],
                        "user_id": user_id,
                        "title": it.get("title", ""),
                        "note": it.get("note", ""),
                        "source": it.get("source", ""),
                        "status": it.get("status", "pending"),
                        "created": it.get("created") or 0,
                    },
                )


def schedule_replace_all(items: list[dict], user_id: str = DEFAULT_USER) -> None:
    """整表替换 schedule（调用方传入追加序，正序插入即可保序）。"""
    with connect() as conn:
        with conn.transaction():
            conn.execute("DELETE FROM schedule_items WHERE user_id=%s", (user_id,))
            for it in items:
                row = {"id": it.get("id") or uuid.uuid4().hex[:12], "user_id": user_id}
                for f in _SCHEDULE_FIELDS:
                    row[f] = it.get(f, "")
                conn.execute(
                    """
                    INSERT INTO schedule_items (id, user_id, title, date, platform, time, status,
                                                note, kind, url, source, event_type, end_date)
                    VALUES (%(id)s,%(user_id)s,%(title)s,%(date)s,%(platform)s,%(time)s,%(status)s,
                            %(note)s,%(kind)s,%(url)s,%(source)s,%(event_type)s,%(end_date)s)
                    """,
                    row,
                )
