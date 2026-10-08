"""Task 2.1 验收：checkpointer 可连接、可建表、可写入读出检查点。

依赖 Docker Postgres 运行中（docker compose up -d）。
"""

import pytest
from langgraph.checkpoint.base import CheckpointTuple, empty_checkpoint

pytestmark = pytest.mark.asyncio


async def test_checkpointer_roundtrip():
    from zimeiti_api.checkpoints import get_checkpointer

    async with get_checkpointer() as saver:
        thread = {"configurable": {"thread_id": "test-2.1", "checkpoint_ns": ""}}
        checkpoint = empty_checkpoint()
        metadata = {"source": "test", "step": 1}
        config = await saver.aput(
            thread, checkpoint, metadata, {"channel_values": {}, "channel_versions": {}}
        )
        assert config["configurable"]["thread_id"] == "test-2.1"
        tup = await saver.aget_tuple(thread)
        assert isinstance(tup, CheckpointTuple)
        assert tup.checkpoint["id"] == checkpoint["id"]
