"""pytest 全局配置。

1. Windows 下 psycopg async 需要 SelectorEventLoop。
2. DB 集成测试前置检查：Docker/Postgres 未就绪时自动等待（最多 30s），
   超时则以明确报错失败——而不是抛出晦涩的连接异常。
"""

import asyncio
import sys
import time

import pytest

if sys.platform == "win32":
    from asyncio import WindowsSelectorEventLoopPolicy

    @pytest.fixture
    def event_loop_policy():
        return WindowsSelectorEventLoopPolicy()


def _postgres_ready() -> tuple[bool, str]:
    """探针：Postgres 是否可接受连接。返回 (是否就绪, 错误信息)。"""
    try:
        import psycopg

        from zimeiti_api.config import DATABASE_URL

        with psycopg.connect(DATABASE_URL, connect_timeout=3):
            return True, ""
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


@pytest.fixture(scope="session", autouse=True)
def _wait_postgres():
    """session 级前置检查：等待 Postgres 就绪（最多 30s）。"""
    deadline = time.time() + 30
    last_err = ""
    while time.time() < deadline:
        ok, err = _postgres_ready()
        if ok:
            return
        last_err = err
        time.sleep(2)
    pytest.exit(
        "\n[预检失败] Postgres 未就绪（等了 30s）。\n"
        "请先启动：docker compose up -d\n"
        f"最后一次连接错误：{last_err}",
        returncode=3,
    )
