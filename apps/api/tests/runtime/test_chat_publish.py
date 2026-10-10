"""web-chat-publish 验收：会话注册/流式端点/消息重建/发布中心入队幂等。"""

import json
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessageChunk, HumanMessage

from zimeiti_api.runtime import chat

# ── T1 会话注册 ────────────────────────────────────────────────────


class TestSessions:
    def test_create_and_list(self, tmp_path, monkeypatch):
        monkeypatch.setattr(chat, "registry_path", lambda: tmp_path / "cs.json")
        s = chat.create_session("xhs-main", "标题")
        assert s["thread_id"].startswith("chat-")
        assert chat.list_sessions()[0]["title"] == "标题"

    def test_get_session(self, tmp_path, monkeypatch):
        monkeypatch.setattr(chat, "registry_path", lambda: tmp_path / "cs.json")
        s = chat.create_session("xhs-main")
        assert chat.get_session(s["thread_id"])["account"] == "xhs-main"
        assert chat.get_session("ghost") is None


# ── T2/T3 流式端点（fake agent） ───────────────────────────────────


class FakeSaver:
    async def aget_tuple(self, config):

        class _Tup:
            checkpoint = {"channel_values": {"messages": [HumanMessage(content="你好")]}}

        return _Tup()


@asynccontextmanager
async def fake_checkpointer():
    yield FakeSaver()


class FakeAgent:
    """astream 双模式 fake：token 增量 + ask_human 中断。"""

    def __init__(self, with_interrupt: bool = True):
        self.with_interrupt = with_interrupt

    def astream(self, inp, config, stream_mode=None):
        async def gen():
            yield ("messages", (AIMessageChunk(content="好的"), {"langgraph_step": 1}))
            if self.with_interrupt:
                interrupt = SimpleNamespace(
                    value={
                        "action_requests": [
                            {"name": "ask_human", "args": {"question": "Q?", "options": "A|B"}}
                        ]
                    }
                )
                yield ("updates", {"__interrupt__": (interrupt,)})

        return gen()


@pytest.fixture
def profile_dir(tmp_path, monkeypatch):
    pdir = tmp_path / "profiles"
    acc = pdir / "xhs-main"
    acc.mkdir(parents=True)
    (acc / "profile.yaml").write_text(
        "account: xhs-main\npositioning: p\nstyle: s\naudience: a\n"
        "content_focus: c\nboundary: b\nplatform_rules: r\npreferences: p\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("zimeiti_api.content.profiles.DEFAULT_BASE_DIR", pdir)
    return pdir


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from zimeiti_api.app import create_app

    return TestClient(create_app())


@pytest.fixture
def chat_env(tmp_path, monkeypatch):
    """会话注册隔离 + fake checkpointer/agent/model。"""
    monkeypatch.setattr(chat, "registry_path", lambda: tmp_path / "cs.json")
    import zimeiti_api.core.models as models_mod
    import zimeiti_api.runtime.checkpoints as checkpoints_mod
    import zimeiti_api.runtime.graph as graph_mod

    monkeypatch.setattr(models_mod, "get_model", lambda: None)
    monkeypatch.setattr(checkpoints_mod, "get_checkpointer", fake_checkpointer)
    monkeypatch.setattr(graph_mod, "build_minimal_agent", lambda *args, **kw: FakeAgent())
    # hosted.pending 指向 tmp
    import zimeiti_api.runtime.hosted as hosted_mod

    monkeypatch.setattr(hosted_mod, "PENDING_PATH", tmp_path / "pending.json")
    return tmp_path


def _sse_frames(text: str) -> list[tuple[str, dict]]:
    frames = []
    for block in text.split("\n\n"):
        if not block.strip():
            continue
        ev = data = None
        for line in block.split("\n"):
            if line.startswith("event: "):
                ev = line[7:]
            elif line.startswith("data: "):
                data = json.loads(line[6:])
        if ev:
            frames.append((ev, data))
    return frames


class TestStreamEndpoint:
    def test_stream_tokens_and_interrupt(self, chat_env, client, tmp_path):
        s = chat.create_session("xhs-main")
        r = client.post(f"/api/chat/sessions/{s['thread_id']}/stream", json={"message": "你好"})
        assert r.status_code == 200
        frames = _sse_frames(r.text)
        types = [e for e, _ in frames]
        print("DBG types:", types)
        err = [d for e, d in frames if e == "error"]
        print("DBG error:", err)
        assert "token" in types and "interrupt" in types and "done" in types
        err = [d for e, d in frames if e == "error"]
        print("DBG error frame:", err)
        token_frames = [d for e, d in frames if e == "token"]
        assert any("好的" in t["text"] for t in token_frames)
        # interrupt 帧 → pending 登记 question
        pending = json.loads((tmp_path / "pending.json").read_text(encoding="utf-8"))
        assert pending[0]["thread_id"] == s["thread_id"]
        assert pending[0]["kind"] == "question"

    def test_empty_message_400(self, chat_env, client):
        s = chat.create_session("xhs-main")
        r = client.post(f"/api/chat/sessions/{s['thread_id']}/stream", json={"message": ""})
        assert r.status_code == 400

    def test_unknown_session_404(self, chat_env, client):
        r = client.post("/api/chat/sessions/ghost/stream", json={"message": "x"})
        assert r.status_code == 404


class TestMessagesEndpoint:
    def test_messages_from_checkpointer(self, chat_env, client):
        s = chat.create_session("xhs-main")
        r = client.get(f"/api/chat/sessions/{s['thread_id']}/messages")
        assert r.status_code == 200
        msgs = r.json()["messages"]
        assert msgs and msgs[0]["role"] == "human"

    def test_messages_404(self, chat_env, client):
        r = client.get("/api/chat/sessions/ghost/messages")
        assert r.status_code == 404
