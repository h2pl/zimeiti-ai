"""P1 批次 2 验收：ask_human 问题卡片（P1⑧）/ 选题看板与日历（P1⑪）。"""

import json

import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from langchain_core.tools import tool as lc_tool

from zimeiti_api import kanban

# ── 看板/日历纯函数（P1⑪） ─────────────────────────────────────────


class TestKanban:
    def test_collect_and_move(self, tmp_path, monkeypatch):
        outputs = tmp_path / "outputs"
        cycle = outputs / "xhs-main" / "cycle-1"
        cycle.mkdir(parents=True)
        (cycle / "state.json").write_text(
            json.dumps(
                {
                    "cards": [
                        {"title": "选题A", "reason": "r", "direction": "d"},
                        {"title": "选题B", "reason": "r", "direction": "d"},
                    ]
                }
            ),
            encoding="utf-8",
        )
        kb_file = tmp_path / "kb.json"
        monkeypatch.setattr(kanban, "_kanban_path", lambda: kb_file)

        board = kanban.collect_cards(outputs)
        assert [c["title"] for c in board["待做"]] == ["选题A", "选题B"]

        kanban.set_status("选题A", "进行中")
        board = kanban.collect_cards(outputs)
        assert [c["title"] for c in board["进行中"]] == ["选题A"]
        assert [c["title"] for c in board["待做"]] == ["选题B"]

    def test_invalid_status_rejected(self, tmp_path, monkeypatch):
        monkeypatch.setattr(kanban, "_kanban_path", lambda: tmp_path / "kb.json")
        with pytest.raises(ValueError):
            kanban.set_status("t", "乱写")

    def test_collect_dedup_and_corrupt_state(self, tmp_path, monkeypatch):
        outputs = tmp_path / "outputs"
        for name in ("cycle-1", "cycle-2"):
            d = outputs / "xhs-main" / name
            d.mkdir(parents=True)
        (outputs / "xhs-main" / "cycle-1" / "state.json").write_text(
            json.dumps({"cards": [{"title": "T", "reason": "old", "direction": "d"}]}),
            encoding="utf-8",
        )
        (outputs / "xhs-main" / "cycle-2" / "state.json").write_text("{broken", encoding="utf-8")
        board = kanban.collect_cards(outputs)
        assert len(board["待做"]) == 1 and board["待做"][0]["reason"] == "old"

    def test_calendar_events_readonly(self):
        class FakeDB:
            def list_events(self):
                return [
                    {
                        "publish_date": "2026-10-10",
                        "title": "B",
                        "platform": "gzh-main",
                        "status": "ok",
                    },
                    {
                        "publish_date": "2026-10-09",
                        "title": "A",
                        "platform": "xhs-main",
                        "status": "ok",
                    },
                ]

        ev = kanban.calendar_events(FakeDB())
        assert ev[0]["date"] == "2026-10-10"  # 按日期倒序
        assert set(ev[0]) == {"date", "title", "platform", "status"}


# ── ask_human 问题卡片端到端（P1⑧） ────────────────────────────────


class FakeToolModel(FakeMessagesListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


def _build_question_flow():
    """构造「ask_human 中断 → respond 回答 → 完成」的测试循环。"""
    from zimeiti_api.checkpoints import get_checkpointer
    from zimeiti_api.graph import build_minimal_agent
    from zimeiti_api.hosted import run_hosted_cycle
    from zimeiti_api.publisher import PublishExecutor

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
    import asyncio

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
    import zimeiti_api.models as models_mod

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
