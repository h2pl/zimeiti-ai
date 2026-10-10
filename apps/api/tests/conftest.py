"""pytest 全局配置。

Windows 下 psycopg async 必须用 SelectorEventLoop——
在 import 阶段全局设置（比 event_loop_policy fixture 更可靠，pytest-asyncio 1.x 已弃用后者）。
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path as _P

import pytest

if sys.platform == "win32":
    from asyncio import WindowsSelectorEventLoopPolicy

    asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())

# 测试的可变产物（审计/待审批注册表）写入临时目录，避免污染仓库文件
_TEST_STATE = tempfile.mkdtemp(prefix="zimeiti-test-")
os.environ["AUDIT_PATH"] = os.path.join(_TEST_STATE, "audit.jsonl")
os.environ.setdefault("ZIMEITI_MASTER_KEY", "test-master-key-not-production")


import zimeiti_api.runtime.hosted as _hosted  # noqa: E402  # 有意后置：需先设置测试环境变量

_hosted.PENDING_PATH = _P(_TEST_STATE) / "pending_approvals.json"


# ─── ops-metrics：PG 测试底座（复用项目 Postgres，隔离 schema） ──────────────

METRICS_TEST_SCHEMA = "zimeiti_metrics_test"


@pytest.fixture
def metrics_db():
    """一次性 PG 版 MetricsDB：每个用例前清空测试 schema 的表，互不污染。"""
    import psycopg

    from zimeiti_api.config import DATABASE_URL
    from zimeiti_api.operations.metrics import MetricsDB

    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(f"CREATE SCHEMA IF NOT EXISTS {METRICS_TEST_SCHEMA}")
    dsn = f"{DATABASE_URL}?options=-csearch_path%3D{METRICS_TEST_SCHEMA}"
    db = MetricsDB(dsn=dsn)
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(f"SET search_path TO {METRICS_TEST_SCHEMA}")
        conn.execute(
            "TRUNCATE metric_snapshots, collection_errors, publish_events RESTART IDENTITY"
        )
    yield db
