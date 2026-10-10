"""评审修复验证：build_default_tools 默认工具集端到端链路。

覆盖 discover→select→create(合规)→publish 全链，不再走 stub 旁路。
真模型由 FakeToolModel 替身（确定性 JSON）；发布执行器用记录型 platform_call。
"""

import json
import uuid

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from zimeiti_api.core.credentials import encrypt_secret
from zimeiti_api.governance import platform_state
from zimeiti_api.governance.publisher import PublishExecutor
from zimeiti_api.runtime.checkpoints import get_checkpointer
from zimeiti_api.runtime.graph import build_minimal_agent
from zimeiti_api.runtime.hosted import resume_after_approval, run_hosted_cycle


@pytest.fixture(autouse=True)
def _platform_enabled(monkeypatch, tmp_path):
    """平台启停门禁（P0⑦）：单测显式初始化为启用（fail-closed 缺文件=全停）。"""
    monkeypatch.setattr(
        "zimeiti_api.governance.platform_state._state_path", lambda: tmp_path / "ps.json"
    )
    platform_state.ensure_defaults()


PROFILE = {
    "account": "xhs-main",
    "positioning": "职场干货",
    "style": "轻松",
    "audience": "互联网人",
    "platform_rules": "标题≤20字",
    "preferences": "不夸大",
}

GOOD_JSON = json.dumps(
    {
        "xhs": {
            "title": "AI 提效 3 招",
            "body": "正文内容" * 10,
            "tags": ["AI"],
            "cover_copy": "效率翻倍",
        },
        "gzh": {"title": "深度：AI 工作流", "body": "长文内容" * 20, "summary": "聊聊 AI 提效"},
    },
    ensure_ascii=False,
)

BAD_JSON = json.dumps(
    {
        "xhs": {
            "title": "稳赚不赔的项目",
            "body": "百分百涨粉" * 10,
            "tags": [],
            "cover_copy": "暴富",
        },
        "gzh": {"title": "稳赚不赔", "body": "躺赚" * 20, "summary": "稳赚"},
    },
    ensure_ascii=False,
)


class SeqModel(BaseChatModel):
    """确定性顺序模型：不循环，响应与调用严格一一对应；支持 sync/async 与 bind_tools。"""

    responses: list
    cursor: int = 0

    @property
    def _llm_type(self) -> str:
        return "seq-fake"

    def bind_tools(self, tools, **kwargs):
        return self

    def _next(self) -> AIMessage:
        if self.cursor < len(self.responses):
            msg = self.responses[self.cursor]
        else:
            msg = AIMessage(content="（响应已耗尽）")
        self.cursor += 1
        return msg

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        return ChatResult(generations=[ChatGeneration(message=self._next())])

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        return self._generate(messages)


def _agent(model, checkpointer, tmp_path, platform_router):
    executor = PublishExecutor(daily_limit=5, allowed_accounts={"xhs-main"})
    return build_minimal_agent(
        model=model,
        checkpointer=checkpointer,
        profile=PROFILE,
        executor=executor,
        cycle_dir=tmp_path / "cycle",
        output_root=tmp_path / "outputs",
        platform_router=platform_router,  # 注入记录型路由器（生产默认 real_platform_router）
    )


def test_full_chain_happy_path(tmp_path, monkeypatch):
    import asyncio

    asyncio.run(_full_chain_happy_path(tmp_path, monkeypatch))


async def _full_chain_happy_path(tmp_path, monkeypatch):
    """默认工具集全链：选题发现→人工挑选→创作→合规通过→审批→发布。"""
    platform_calls: list[str] = []

    import zimeiti_api.platforms.xhs as xhs_mod

    class FakeXhsPub:
        def __init__(self, storage_state=None, selectors=None):
            pass

        def publish(self, draft, page=None):
            return "submitted"

        def readback(self, title, page=None):
            return "verified"

    monkeypatch.setattr(xhs_mod, "XhsPublisher", FakeXhsPub)

    def recording_router(account, draft):
        title = draft["title"] if isinstance(draft, dict) else draft.title
        platform_calls.append(title)
        return {"platform_result": "submitted", "readback": "verified"}

    model = SeqModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "discover_topics",
                        "args": {"manual_direction": "AI 提效指南"},
                        "id": "t1",
                    }
                ],
            ),
            AIMessage(
                content="",
                tool_calls=[{"name": "select_topic", "args": {"title": "AI 提效指南"}, "id": "t2"}],
            ),
            AIMessage(content="", tool_calls=[{"name": "create_drafts", "args": {}, "id": "t3"}]),
            AIMessage(content=GOOD_JSON),
            AIMessage(content="", tool_calls=[{"name": "publish", "args": {}, "id": "t4"}]),
            AIMessage(content="发布完成"),
        ]
    )

    # 凭证库：tmp 目录 + 环境变量（工具内部经 decrypt_secret 读取）
    cred_dir = tmp_path / "_credentials"
    cred_dir.mkdir()
    (cred_dir / "xhs-main.sealed").write_text(encrypt_secret("fake-cookie"), encoding="utf-8")
    monkeypatch.setenv("ZIMEITI_CREDENTIALS_DIR", str(cred_dir))

    async with get_checkpointer() as saver:
        # platform_stub 通过 monkeypatch 注入 PublishExecutor 默认平台调用？
        # 否——直接在 executor 层替换：这里改用子类记录
        agent = _agent(model, saver, tmp_path, recording_router)
        thread_id = f"chain-1-{uuid.uuid4().hex[:8]}"
        cycle = await run_hosted_cycle(agent, thread_id, "做一期 AI 提效内容并发布")
        # 选题与发布都是人工闸门：首轮应停在 select_topic 中断
        assert "__interrupt__" in cycle

        res = await resume_after_approval(agent, thread_id, approved=True)
        assert "__interrupt__" in res  # 创作完成 → 停在发布审批

        final = await resume_after_approval(agent, thread_id, approved=True)
        assert final["messages"][-1].content == "发布完成"
        assert platform_calls == ["AI 提效 3 招"]

        # 草稿落盘 + 可追溯 + 合规结论
        out_dir = tmp_path / "outputs" / "xhs-main"
        drafts_files = list(out_dir.glob("*/drafts.json"))
        assert len(drafts_files) == 1
        data = json.loads(drafts_files[0].read_text(encoding="utf-8"))
        assert data["topic"] == "AI 提效指南"
        assert data["compliance"]["passed"] is True


def test_compliance_block_prevents_publish(tmp_path, monkeypatch):
    import asyncio

    asyncio.run(_compliance_block(tmp_path, monkeypatch))


async def _compliance_block(tmp_path, monkeypatch):
    """合规未通过的草稿：publish 工具必须拒绝执行。"""
    platform_calls: list[str] = []

    import zimeiti_api.platforms.xhs as xhs_mod

    class FakeXhsPub:
        def __init__(self, storage_state=None, selectors=None):
            pass

        def publish(self, draft, page=None):
            return "submitted"

        def readback(self, title, page=None):
            return "verified"

    monkeypatch.setattr(xhs_mod, "XhsPublisher", FakeXhsPub)

    def recording_router(account, draft):
        title = draft["title"] if isinstance(draft, dict) else draft.title
        platform_calls.append(title)
        return {"platform_result": "submitted", "readback": "verified"}

    model = SeqModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "discover_topics",
                        "args": {"manual_direction": "暴富项目"},
                        "id": "t1",
                    }
                ],
            ),
            AIMessage(
                content="",
                tool_calls=[{"name": "select_topic", "args": {"title": "暴富项目"}, "id": "t2"}],
            ),
            AIMessage(content="", tool_calls=[{"name": "create_drafts", "args": {}, "id": "t3"}]),
            AIMessage(content=BAD_JSON),
            AIMessage(content="", tool_calls=[{"name": "publish", "args": {}, "id": "t4"}]),
            AIMessage(content="好的，不发布"),
        ]
    )
    cred_dir = tmp_path / "_credentials"
    cred_dir.mkdir()
    (cred_dir / "xhs-main.sealed").write_text(encrypt_secret("fake-cookie"), encoding="utf-8")
    monkeypatch.setenv("ZIMEITI_CREDENTIALS_DIR", str(cred_dir))

    async with get_checkpointer() as saver:
        agent = _agent(model, saver, tmp_path, recording_router)
        thread_id = f"chain-2-{uuid.uuid4().hex[:8]}"
        await run_hosted_cycle(agent, thread_id, "做一期暴富内容并发布")
        final = await resume_after_approval(agent, thread_id, approved=True)
        # 创作被合规阻断后，publish 工具调用返回拒绝信息（不产生平台动作）
        assert platform_calls == []
        assert "不可发布" in str([m.content for m in final["messages"]])


def test_selection_gate_blocks_creation(tmp_path):
    """未挑选选题时 create_drafts 工具必须阻断（C4 闸门）。"""
    from zimeiti_api.runtime.tools import build_default_tools

    model = SeqModel(responses=[AIMessage(content="{}")])
    tools = build_default_tools(
        PROFILE,
        model,
        PublishExecutor(allowed_accounts={"xhs-main"}),
        tmp_path / "cycle",
    )
    create = {t.name: t for t in tools}["create_drafts"]
    result = create.invoke({})
    assert "尚未挑选选题" in result


def _diag_tmp():
    import pathlib
    import tempfile

    return pathlib.Path(tempfile.mkdtemp(prefix="diag5-")) / "cycle"
