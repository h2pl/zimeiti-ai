"""会话用量统计（model-resilience-cron，design D4：只记 token 不换算钱）。

chat_usage 表按会话/轮次/模型记录 prompt/completion token；/api/usage 可查。
"""

from __future__ import annotations

import time
import uuid
from contextlib import contextmanager

from .core import pg

_DDL = """
CREATE TABLE IF NOT EXISTS chat_usage (
    seq               BIGSERIAL,
    id                TEXT NOT NULL,
    user_id           TEXT NOT NULL DEFAULT 'local',
    session_key       TEXT NOT NULL,
    turn_id           TEXT NOT NULL DEFAULT '',
    model             TEXT NOT NULL DEFAULT '',
    prompt_tokens     INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    created           BIGINT NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, id)
);
"""


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


def record(
    session_key: str, turn_id: str, model: str, prompt_tokens: int, completion_tokens: int
) -> None:
    if prompt_tokens <= 0 and completion_tokens <= 0:
        return  # 无用量元数据（部分端点不返回）不记
    _exec(
        "INSERT INTO chat_usage (id, session_key, turn_id, model, prompt_tokens,"
        " completion_tokens, created) VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (
            uuid.uuid4().hex[:12],
            session_key,
            turn_id,
            model or "",
            int(prompt_tokens),
            int(completion_tokens),
            int(time.time()),
        ),
    )


def summary(session_key: str | None = None, days: int = 30) -> dict:
    """按会话/日期范围汇总。"""
    where = "WHERE created > %s"
    params: list = [int(time.time()) - days * 86400]
    if session_key:
        where += " AND session_key = %s"
        params.append(session_key)
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT session_key, model, SUM(prompt_tokens), SUM(completion_tokens),"  # nosec B608  固定片段+参数化
                f" COUNT(*) FROM chat_usage {where} GROUP BY session_key, model"
                f" ORDER BY 5 DESC LIMIT 100",
                tuple(params),
            )
            rows = cur.fetchall()

    # 金额折算（model-cost-rotation D4）：行级「可得则计、不可得则 None」；
    # 总计=已知行之和；存在未知行时 cost_usd_partial=True（不把 None 当 0）。
    try:
        from .runtime.pricing import cost_usd

        priced = [(r, cost_usd(r[1], r[2] or 0, r[3] or 0)) for r in rows]
    except Exception:  # noqa: BLE001   定价模块不可用时退回纯 token 视图
        priced = [(r, None) for r in rows]
    known = [c for _, c in priced if c is not None]
    partial = len(known) < len(priced)
    return {
        "rows": [
            {
                "session_key": r[0],
                "model": r[1],
                "prompt_tokens": r[2],
                "completion_tokens": r[3],
                "turns": r[4],
                "cost_usd": c,
            }
            for (r, c) in priced
        ],
        "total_prompt": sum(r[2] or 0 for r in rows),
        "total_completion": sum(r[3] or 0 for r in rows),
        "cost_usd": round(sum(known), 6) if known else None,
        "cost_usd_partial": partial,
    }
