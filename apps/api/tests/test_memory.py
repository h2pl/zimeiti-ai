"""agent 记忆系统（agent-memory-system）。

TDD RED：zimeiti_harness.memory 尚不存在；实现后 GREEN。
存储层测试直连 PG（与 test_pg 系列同前提：本地 PG 可用）。
"""

import pytest

pytestmark = pytest.mark.skipif(
    __import__("os").environ.get("SKIP_PG_TESTS") == "1",
    reason="PG 不可用",
)

MOD = "zimeiti_harness.memory"


@pytest.fixture()
def store():
    from zimeiti_harness.memory import store as st

    st.setup()
    # 清出干净测试床
    st._exec("DELETE FROM memory_entries")
    st._exec("DELETE FROM memory_injections")
    yield st
    st._exec("DELETE FROM memory_entries")
    st._exec("DELETE FROM memory_injections")


def test_record_and_search(store):
    store.record("用户偏好短段落排版", origin="owner", importance=8, tags=["style"])
    store.record("一次性规格：本次 800 字", origin="agent", importance=2, tags=[])
    hits = store.search("排版", limit=5)
    assert any("短段落" in h["content"] for h in hits)
    # 检索结果带溯源标注
    assert all("origin" in h and "created_at" in h for h in hits)


def test_origin_whitelist(store):
    with pytest.raises(ValueError):
        store.record("x", origin="untrusted-prose", importance=5)


def test_injection_dedup(store):
    store.record("封面用克莱因蓝", origin="owner", importance=7)
    hits = store.search("封面", limit=5)
    eid = hits[0]["id"]
    assert store.is_injected("sess-a", eid) is False
    store.mark_injected("sess-a", eid)
    assert store.is_injected("sess-a", eid) is True
    # 同会话过滤已注入；新会话不过滤
    assert all(h["id"] != eid for h in store.search("封面", session_key="sess-a"))
    assert any(h["id"] == eid for h in store.search("封面", session_key="sess-b"))


def test_episodic_flush_writes(store):
    from zimeiti_harness.memory.flush import flush_if_long

    messages = [{"role": "user", "content": f"第{i}条消息" * 50} for i in range(40)]
    n = flush_if_long("sess-flush", messages)
    assert n >= 1
    hits = store.search("消息", session_key=None, scope="episodic")
    assert hits and hits[0]["origin"] == "system"


def test_flush_skips_short(store):
    from zimeiti_harness.memory.flush import flush_if_long

    assert flush_if_long("sess-short", [{"role": "user", "content": "短"}]) == 0


def test_cascade_delete_session(store):
    store.record("级联测试", origin="owner", importance=6)
    eid = store.search("级联", limit=1)[0]["id"]
    store.mark_injected("sess-del", eid)
    store.delete_session_injections("sess-del")
    assert store.is_injected("sess-del", eid) is False
