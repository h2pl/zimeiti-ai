"""Task 7.2 后端面：审批列表/确认/resume 的 HTTP API（Web 审批页依赖）。"""

import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage

pytestmark = pytest.mark.asyncio


class FakeToolModel(FakeMessagesListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


async def _start_cycle_with_pending_approval():
    from zimeiti_api import tools as tz
    from zimeiti_api.checkpoints import get_checkpointer
    from zimeiti_api.graph import build_minimal_agent
    from zimeiti_api.hosted import run_hosted_cycle

    tz.publish_calls.clear()
    model = FakeToolModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "publish", "args": {"topic": "审批流", "content": "正文"}, "id": "c1"}
                ],
            ),
            AIMessage(content="已发布"),
        ]
    )
    from zimeiti_api.publisher import PublishExecutor
    from langchain_core.tools import tool as lc_tool

    calls: list[str] = []

    @lc_tool
    def publish(topic: str, content: str) -> str:
        """stub publish。"""
        calls.append(topic)
        return f"published: {topic}"

    async with get_checkpointer() as saver:
        agent = build_minimal_agent(
            model=model,
            checkpointer=saver,
            profile={"account": "xhs-main", "positioning": "测试"},
            executor=PublishExecutor(allowed_accounts={"xhs-main"}),
            cycle_dir="outputs/xhs-main/test-7.2",
            tools=[publish],
        )
        result = await run_hosted_cycle(agent, "test-7.2", "发布审批流测试内容")
    assert "__interrupt__" in result


def test_approvals_api_flow():
    import asyncio

    from fastapi.testclient import TestClient

    from zimeiti_api.app import create_app

    asyncio.run(_start_cycle_with_pending_approval())

    # 确认端点的模型用 fake（隔离 LLM 依赖；真模型 resume 的兼容性单列 8.2 排查）
    def fake_model():
        return FakeToolModel(responses=[AIMessage(content="已发布")])

    import zimeiti_api.models as models_mod

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(models_mod, "get_model", fake_model)

    client = TestClient(create_app())
    # 1. 审批列表能看到待审批项
    resp = client.get("/api/approvals")
    assert resp.status_code == 200
    items = resp.json()
    assert any(i["thread_id"] == "test-7.2" for i in items)
    # 2. 确认 → resume → 发布完成
    resp = client.post("/api/approvals/test-7.2/confirm")
    assert resp.status_code == 200
    # 3. 确认后不再出现在待审批列表
    items = client.get("/api/approvals").json()
    assert not any(i["thread_id"] == "test-7.2" for i in items)
    # 4. 发布日志可查
    log = client.get("/api/publish-log").json()
    assert any(e.get("action") == "cycle_completed" for e in log)
    monkeypatch.undo()
