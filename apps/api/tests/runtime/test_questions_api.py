"""ask_human 问题卡片 API 验收（P1⑧，Easel gateway_questions 对标）。"""

import asyncio

import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from langchain_core.tools import tool as lc_tool


class FakeToolModel(FakeMessagesListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


def _build_question_flow():
    """构造「ask_human 中断 → respond 回答 → 完成」的测试循环。"""
    from zimeiti_api.governance.publisher import PublishExecutor
    from zimeiti_api.runtime.checkpoints import get_checkpointer
    from zimeiti_api.runtime.graph import build_minimal_agent
    from zimeiti_api.runtime.hosted import run_hosted_cycle

    @lc_tool
    def noop() -> str:
        """无操作工具（占位）。"""
        return "ok"

    model = FakeToolModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "ask_human",
                        "args": {"question": "标题选哪个？", "options": "A|B"},
                        "id": "q1",
                    }
                ],
            ),
            AIMessage(content="好的，按人选的标题执行"),
        ]
    )

    async def _run():
        async with get_checkpointer() as saver:
            agent = build_minimal_agent(
                model=model,
                checkpointer=saver,
                profile={"account": "xhs-main", "positioning": "测试"},
                executor=PublishExecutor(allowed_accounts={"xhs-main"}),
                cycle_dir="outputs/xhs-main/test-question",
                tools=[noop],
            )
            result = await run_hosted_cycle(agent, "test-question-8", "请提问", account="xhs-main")
            return result

    return _run()


def test_question_card_flow():

    from fastapi.testclient import TestClient

    from zimeiti_api.app import create_app

    asyncio.run(_build_question_flow())

    client = TestClient(create_app())
    items = client.get("/api/approvals").json()
    q = [i for i in items if i["thread_id"] == "test-question-8"]
    assert q and q[0]["kind"] == "question"
    assert q[0]["question"] == "标题选哪个？"
    assert q[0]["options"] == ["A", "B"]

    # 审批端点对提问类型必须拒绝（工具体永不执行——回答走 respond 端点）
    resp = client.post("/api/approvals/test-question-8/confirm")
    assert resp.status_code == 400

    # 应答端点（重新构造一个提问流验证 respond；恢复端点的模型打桩——隔离 LLM）
    import zimeiti_api.core.models as models_mod

    def fake_model():
        return FakeToolModel(responses=[AIMessage(content="好的，按 B 执行")])

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(models_mod, "get_model", fake_model)
    asyncio.run(_build_question_flow())
    resp = client.post("/api/questions/test-question-8/answer", json={"message": "选 B"})
    monkeypatch.undo()
    assert resp.status_code == 200
    items = client.get("/api/approvals").json()
    assert not any(i["thread_id"] == "test-question-8" for i in items)

    # 空回答拒绝
    asyncio.run(_build_question_flow())
    resp = client.post("/api/questions/test-question-8/answer", json={"message": "  "})
    assert resp.status_code == 400
