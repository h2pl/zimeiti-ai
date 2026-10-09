"""Task 2.2 验收：最小执行图在发布工具处 interrupt，确认后 resume 完成。

用 Fake 模型避免真实 LLM 调用；checkpointer 用真 Postgres。
"""

import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command

pytestmark = pytest.mark.asyncio


async def test_publish_interrupt_and_resume():
    from zimeiti_api import tools as tz
    from zimeiti_api.checkpoints import get_checkpointer
    from zimeiti_api.graph import build_minimal_agent

    tz.publish_calls.clear()
    calls = tz.publish_calls

    class FakeToolModel(FakeMessagesListChatModel):
        # langchain v1 的 create_agent 会调用 bind_tools；fake 模型恒等返回即可
        def bind_tools(self, tools, **kwargs):
            return self

    model = FakeToolModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "publish",
                        "args": {"topic": "测试", "content": "正文"},
                        "id": "call_1",
                    }
                ],
            ),
            AIMessage(content="已发布"),
        ]
    )

    async with get_checkpointer() as saver:
        agent = build_minimal_agent(model=model, checkpointer=saver)
        config = {"configurable": {"thread_id": "test-2.2", "checkpoint_ns": ""}}

        result = await agent.ainvoke({"messages": [HumanMessage("发布测试内容")]}, config=config)
        # 第一次运行应在 publish 工具处中断等待审批
        assert "__interrupt__" in result
        assert calls == []  # 未审批，不产生真实发布

        # 用户批准 → resume
        result2 = await agent.ainvoke(
            Command(resume={"decisions": [{"type": "approve"}]}), config=config
        )
        assert calls == ["测试"]
        assert result2["messages"][-1].content == "已发布"
