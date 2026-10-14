"""pg-data-layer 测试夹具。

测试直连本地 PostgreSQL（DATABASE_URL 缺省库 zimeiti-ai）。PG 不可达时
fixture 断言失败而非跳过——验收要求测试真实运行（comet verify 不允许
skipped 计为通过）。每个测试用独立 user_id 命名空间（多租户维度的另一用途），
结束后清理，不污染本地版 'local' 数据。
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path

import pytest

API_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_DIR))

from zimeiti_api.core import pg  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def pg_ready():
    ok, err = pg.verify()
    assert ok, f"测试需要本地 PostgreSQL 可达（DATABASE_URL={pg.database_url()}）：{err}"


@pytest.fixture
def uid():
    """独立租户命名空间 + 用后清理。"""
    u = f"test-{uuid.uuid4().hex[:8]}"
    yield u
    with pg.connect() as conn:
        with conn.transaction():
            conn.execute("DELETE FROM chat_messages WHERE user_id=%s", (u,))
            conn.execute("DELETE FROM chat_sessions WHERE user_id=%s", (u,))
            conn.execute("DELETE FROM ideas WHERE user_id=%s", (u,))
            conn.execute("DELETE FROM schedule_items WHERE user_id=%s", (u,))
            conn.execute("DELETE FROM hitl_pending WHERE user_id=%s", (u,))
