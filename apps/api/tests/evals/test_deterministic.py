"""确定性行为断言（agent-behavior-evals，无 LLM，随 make check 跑）。

断言的是「行为前提」：契约段在位、技能可发现、工具在册、白名单与 fallback 判定正确。
这些一旦被改动，agent 行为就会变——所以它们属于行为回归，不是普通单测。
"""

import pytest

from zimeiti_api.content import skills as skills_mod
from zimeiti_api.runtime import agent_runtime as ar
from zimeiti_api.runtime import exec_tool
from zimeiti_api.runtime import model_fallback as mfb


@pytest.fixture(autouse=True)
def _clear_skills_cache():
    """build_system_prompt() 会预热技能清单 TTL 缓存（300s）。

    不清理会让后续用「tmp 假目录」测 /api/skills 的用例读到缓存里的真实技能而失败
    （test_get_skills_route 实测踩到）——缓存污染是跨用例的，责任在使用方。
    """
    yield
    skills_mod._SKILLS_CACHE = None


def _prompt() -> str:
    return ar.build_system_prompt()


CONTRACT_SECTIONS = [
    "【人格与沟通】",
    "【执行偏向】",
    "【Follow-through】",
    "【风险分级 ask-first】",
    "【编排纪律】",
    "【运营五层流程】",
    "【文件系统】",
    "【白名单脚本】",
    "【记忆】",
    "【语言硬约束】",
]


@pytest.mark.parametrize("section", CONTRACT_SECTIONS)
def test_contract_section_present(section):
    assert section in _prompt(), f"契约段缺失：{section}（改提示词必须同步本断言）"


def test_skills_catalog_contains_detailed_skills():
    """探针实证过的痛点：agent 只用 ops-* 薄版，看不到库里的详细技能。"""
    p = _prompt()
    for name in ("skill-topic-evaluator", "skill-quality-gate", "skill-wechat-publisher"):
        assert f"- {name}（" in p or f"- {name} " in p or name in p, f"技能目录不含 {name}"


def test_skills_catalog_has_routing_rule():
    assert "精确匹配" in _prompt() and "最接近" in _prompt(), "路由链纪律缺失"


def test_catalog_includes_layer_groups():
    p = _prompt()
    assert "[discover]" in p and "[plan]" in p and "[produce]" in p, "技能目录未按 layer 分组"


def test_tools_registered():
    """工具装配一旦变化，agent 能力边界就变了。

    _build_tools 是 _build_agent 的内嵌函数（ask_human 需绑定会话上下文），
    故此处断言两个工厂产出的工具名 + 源码含 ask_human，避免起真实 agent（需 PG）。
    """
    from zimeiti_api.memory.tools import make_memory_tools
    from zimeiti_api.runtime.exec_tool import make_exec_tool

    def _names(obj):
        items = obj if isinstance(obj, (list, tuple)) else [obj]
        return {getattr(t, "name", "") for t in items}

    names = _names(make_exec_tool()) | _names(make_memory_tools())
    assert "exec_script" in names
    assert {"memory_record", "memory_search"} <= names

    import inspect

    assert "ask_human" in inspect.getsource(ar._build_agent), "ask_human 未装配"


def test_exec_whitelist_rejects_unregistered():
    r = exec_tool.exec_script("rm_rf_everything", {})
    assert r["exit_code"] != 0
    assert "未注册" in r["stderr"] or "白名单" in r["stderr"]


def test_exec_rejects_path_injection():
    r = exec_tool.exec_script("ai_score", {"article": "../../.env"})
    assert r["exit_code"] == 2
    assert "拒绝" in r["stderr"]


def test_fallback_policy_matrix():
    """4xx 直抛（不掩盖配置错误）；5xx/429/连接错误可切换。"""
    from langchain_core.exceptions import LangChainException

    class APIConnectionError(LangChainException):
        pass

    class Status(LangChainException):
        def __init__(self, code):
            super().__init__("x")
            self.status_code = code

    assert mfb._is_infra_failure(APIConnectionError()) is True
    assert mfb._is_infra_failure(Status(500)) is True
    assert mfb._is_infra_failure(Status(429)) is True
    assert mfb._is_infra_failure(Status(401)) is False
    assert mfb._is_infra_failure(Status(400)) is False


def test_prompt_size_guard():
    """提示词不应无限膨胀（技能目录是主要变量）。"""
    assert len(_prompt()) < 40000, "提示词超过 40K——技能目录注入需重新设计"
