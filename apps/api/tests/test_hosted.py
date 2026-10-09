"""Task 2.3/2.4 验收：托管循环触发、跨进程断点恢复、执行审计。

模拟进程重启：用两个独立的 graph 实例 + 同一 checkpointer。
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_hosted_cycle_interrupt_recovery_and_audit():
    from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
    from langchain_core.messages import AIMessage

    from zimeiti_api import hosted
    from zimeiti_api import tools as tz
    from zimeiti_api.checkpoints import get_checkpointer
    from zimeiti_api.graph import build_minimal_agent

    tz.publish_calls.clear()

    class FakeToolModel(FakeMessagesListChatModel):
        def bind_tools(self, tools, **kwargs):
            return self

    model = FakeToolModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "publish",
                        "args": {"topic": "断点恢复", "content": "正文"},
                        "id": "c1",
                    }
                ],
            ),
            AIMessage(content="已发布"),
        ]
    )

    async with get_checkpointer() as saver:
        # 第一次运行：实例 1（模拟进程 A）
        agent_a = build_minimal_agent(model=model, checkpointer=saver)
        thread_id = "test-2.3"
        result = await hosted.run_hosted_cycle(agent_a, thread_id, "发布断点恢复内容")
        assert "__interrupt__" in result
        # 审批前无发布
        assert tz.publish_calls == []
        # 审计已记录（托管循环启动 + 等待审批）
        entries = hosted.audit_list()
        assert any(e["action"] == "cycle_started" for e in entries)
        assert any(e["action"] == "awaiting_approval" for e in entries)

        # 第二次运行：实例 2（模拟进程重启后恢复），同一 checkpointer
        agent_b = build_minimal_agent(model=model, checkpointer=saver)
        final = await hosted.resume_after_approval(agent_b, thread_id, approved=True)

        # 发布恰好执行一次（断点恢复不重复执行已完成步骤）
        assert tz.publish_calls == ["断点恢复"]
        # 审计包含恢复与完成记录
        entries = hosted.audit_list()
        assert any(e["action"] == "cycle_completed" for e in entries)
        assert final["messages"][-1].content == "已发布"
