"""Task 7.2 后端面：审批列表/确认/resume 的 HTTP API（Web 审批页依赖）。"""

import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage

pytestmark = pytest.mark.asyncio


class FakeToolModel(FakeMessagesListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


async def _start_cycle_with_pending_approval():
    from zimeiti_api.runtime import tools as tz
    from zimeiti_api.runtime.checkpoints import get_checkpointer
    from zimeiti_api.runtime.graph import build_minimal_agent
    from zimeiti_api.runtime.hosted import run_hosted_cycle

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
    from langchain_core.tools import tool as lc_tool

    from zimeiti_api.governance.publisher import PublishExecutor

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
        result = await run_hosted_cycle(agent, "test-7.2", "发布审批流测试内容", account="xhs-main")
    assert "__interrupt__" in result


def test_approvals_api_flow():
    import asyncio

    from fastapi.testclient import TestClient

    from zimeiti_api.app import create_app

    asyncio.run(_start_cycle_with_pending_approval())

    # 确认端点的模型用 fake（隔离 LLM 依赖；真模型 resume 的兼容性单列 8.2 排查）
    def fake_model():
        return FakeToolModel(responses=[AIMessage(content="已发布")])

    import zimeiti_api.content.profiles as profiles_mod
    import zimeiti_api.core.models as models_mod

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(models_mod, "get_model", fake_model)
    # 捕获恢复端点实际加载的账号画像（修复遗留：不再硬编码 xhs-main）
    loaded_accounts: list[str] = []
    real_load_profile = profiles_mod.load_profile

    def spy_load_profile(account: str):
        loaded_accounts.append(account)
        return real_load_profile(account)

    monkeypatch.setattr(profiles_mod, "load_profile", spy_load_profile)

    client = TestClient(create_app())
    # 1. 审批列表能看到待审批项（含 account，Web 页据此区分平台）
    resp = client.get("/api/approvals")
    assert resp.status_code == 200
    items = resp.json()
    assert any(i["thread_id"] == "test-7.2" for i in items)
    assert any(i.get("account") == "xhs-main" for i in items)
    # 2. 确认 → resume（用 pending 记录的账号画像）→ 发布完成
    resp = client.post("/api/approvals/test-7.2/confirm")
    assert resp.status_code == 200
    assert loaded_accounts == ["xhs-main"]
    # 3. 确认后不再出现在待审批列表
    items = client.get("/api/approvals").json()
    assert not any(i["thread_id"] == "test-7.2" for i in items)
    # 4. 发布日志可查
    log = client.get("/api/publish-log").json()
    assert any(e.get("action") == "cycle_completed" for e in log)
    monkeypatch.undo()


def test_confirm_reregisters_pending_on_second_interrupt():
    """双闸门回归（2026-10-10 托管 E2E 实测缺陷）：

    恢复后模型再次调用 publish → 命中第二个中断，待审批队列必须重新登记，
    否则循环在发布闸门永久卡死（审批页看不到、confirm 404）。
    测试安全：publish 工具对空 state 返回「没有可发布的草稿」，无真实外发。
    """
    import asyncio

    from fastapi.testclient import TestClient

    from zimeiti_api.app import create_app

    asyncio.run(_start_cycle_with_pending_approval())  # 闸门#1：publish 中断

    def fake_model_after_approve():
        # 恢复闸门#1 后，模型继续调用 publish → 应命中闸门#2
        return FakeToolModel(
            responses=[
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "publish",
                            "args": {},
                            "id": "c2",
                        }
                    ],
                )
            ]
        )

    import zimeiti_api.core.models as models_mod

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(models_mod, "get_model", fake_model_after_approve)

    client = TestClient(create_app())
    resp = client.post("/api/approvals/test-7.2/confirm")
    assert resp.status_code == 200
    # 关键断言：第二个中断已重新登记到待审批队列
    items = client.get("/api/approvals").json()
    assert any(i["thread_id"] == "test-7.2" for i in items), "双闸门第二次中断未重登记"

    # 第二次确认：无工具调用 → 循环完成，pending 清空
    def fake_model_final():
        return FakeToolModel(responses=[AIMessage(content="已发布")])

    monkeypatch.setattr(models_mod, "get_model", fake_model_final)
    resp = client.post("/api/approvals/test-7.2/confirm")
    assert resp.status_code == 200
    items = client.get("/api/approvals").json()
    assert not any(i["thread_id"] == "test-7.2" for i in items)
    monkeypatch.undo()
