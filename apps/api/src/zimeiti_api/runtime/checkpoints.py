"""LangGraph checkpointer 接入（Task 2.1）。

使用官方 langgraph-checkpoint-postgres 的 AsyncPostgresSaver，
连接串来自 config.DATABASE_URL。setup() 幂等创建所需表。
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from zimeiti_api.config import DATABASE_URL


@asynccontextmanager
async def get_checkpointer() -> AsyncIterator[AsyncPostgresSaver]:
    """获取已初始化的 Postgres checkpointer（用完自动释放连接）。"""
    async with AsyncPostgresSaver.from_conn_string(DATABASE_URL) as saver:
        await saver.setup()
        yield saver
