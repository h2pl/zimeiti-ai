"""专属子代理与结构化输出（agent-subagents-output）。

断言的是「子代理的角色边界」：
- 工具面：不传 tools → 继承文件工具，但拿不到 ask_human / exec_script / memory_*
  （主 agent 的私有工具），越权面在装配处收死
- 写权限：research 全拒写；draft 仅放行 outputs/**
- 开关与模型：ZIMEITI_SUBAGENT_ENABLED=false 关闭；模型必传（deepagents 校验），
  ZIMEITI_SUBAGENT_MODEL 配置了才降档
"""

import inspect
import os

import pytest

from zimeiti_harness.runtime import agent_runtime as ar


@pytest.fixture(autouse=True)
def _env():
    saved = {
        k: os.environ.get(k)
        for k in ("ZIMEITI_SUBAGENT_ENABLED", "ZIMEITI_SUBAGENT_MODEL", "OPENAI_API_KEY")
    }
    os.environ.setdefault("OPENAI_API_KEY", "test-key")
    yield
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


@pytest.fixture()
def subs():
    return ar._build_subagents()


def test_two_subagents_defined(subs):
    assert {s["name"] for s in subs} == {"research", "draft"}


def test_subagents_have_no_private_tools(subs):
    """子代理不得拿到 ask_human / exec_script / memory_*（越权面）。"""
    for s in subs:
        names = {getattr(t, "name", "") for t in (s.get("tools") or [])}
        for bad in ("ask_human", "exec_script", "memory_record", "memory_search"):
            assert bad not in names, f"{s['name']} 不应含 {bad}"


def test_research_cannot_write(subs):
    research = next(s for s in subs if s["name"] == "research")
    perms = research.get("permissions") or []
    assert any(p.mode == "deny" and "/**" in p.paths for p in perms), "research 必须拒全部写操作"
    assert not any(p.mode == "allow" for p in perms), "research 不应有任何放行"


def test_draft_writes_only_outputs(subs):
    draft = next(s for s in subs if s["name"] == "draft")
    perms = draft.get("permissions") or []
    allow = [p for p in perms if p.mode == "allow"]
    deny = [p for p in perms if p.mode == "deny"]
    assert allow and all(any("outputs" in path for path in p.paths) for p in allow), (
        "draft 的放行范围必须限定在 outputs/"
    )
    assert deny, "draft 必须有兜底拒绝"


def test_model_required_and_downgrade(subs, monkeypatch):
    """spec 必须含 model（deepagents 校验）；配了便宜模型才降档。"""
    for s in subs:
        assert s.get("model") is not None

    monkeypatch.setenv("ZIMEITI_SUBAGENT_MODEL", "cheap-model")
    cheap_subs = ar._build_subagents()
    assert all(s["model"] == "cheap-model" for s in cheap_subs)


def test_disabled_switch(monkeypatch):
    monkeypatch.setenv("ZIMEITI_SUBAGENT_ENABLED", "false")
    assert ar._build_subagents() == []


def test_schemas_available():
    from zimeiti_harness.runtime import schemas

    ev = schemas.TopicEvaluation(
        dimensions={"赛道匹配": 9, "差异化": 7},
        overall=78,
        verdict="做",
        advice=["避开揭穿豆包的角度"],
    )
    assert ev.overall == 78 and ev.verdict == "做"
    assert ev.dimensions["赛道匹配"] == 9


def test_main_agent_is_not_structured():
    """主 agent 不得启用结构化输出——图级配置会约束所有输出。

    查 kwargs 形式（`response_format=`），避免把注释里的同名文字误判为传参。
    """
    assert "response_format=" not in inspect.getsource(ar._build_agent)


def test_structured_entry_registers_schema():
    """chat_structured 只受理已注册 schema，未注册须报错（防静默降级）。"""
    import asyncio

    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    async def run():
        try:
            await ar.chat_structured("no_such_schema", "x")
        except ValueError as e:
            assert "未注册" in str(e)
        else:
            raise AssertionError("未注册 schema 应报 ValueError")

    asyncio.run(run())
