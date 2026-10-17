"""成本折算与多 key 轮换（model-cost-rotation）。"""

import os

import pytest

from zimeiti_api.runtime import agent_runtime as ar
from zimeiti_api.runtime import pricing


@pytest.fixture(autouse=True)
def _env():
    saved = {
        k: os.environ.get(k)
        for k in (
            "ZIMEITI_API_KEYS",
            "ZIMEITI_FALLBACK_MODELS",
            "ZIMEITI_EXPLICIT_MODEL",
            "OPENAI_API_KEY",
            "OPENAI_MODEL",
        )
    }
    os.environ["OPENAI_API_KEY"] = "key-a"
    os.environ["OPENAI_MODEL"] = "deepseek-chat"
    os.environ.pop("ZIMEITI_EXPLICIT_MODEL", None)
    os.environ.pop("ZIMEITI_API_KEYS", None)
    os.environ.pop("ZIMEITI_FALLBACK_MODELS", None)
    yield
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


# ---------- 定价 ----------


def test_known_model_priced():
    c = pricing.cost_usd("deepseek-chat", 1_000_000, 1_000_000)
    assert c == pytest.approx(
        pricing.MODEL_PRICING["deepseek-chat"][0] + pricing.MODEL_PRICING["deepseek-chat"][1]
    )


def test_unknown_model_none():
    assert pricing.cost_usd("no-such-model", 100, 100) is None
    assert pricing.cost_usd("", 100, 100) is None


def test_case_insensitive_with_fallback_entry():
    # 链上 fallback 节点形如 "模型名@base_url"，取 @ 前段匹配
    c = pricing.cost_usd("deepseek-chat@https://api.deepseek.com", 1_000_000, 0)
    assert c == pytest.approx(pricing.MODEL_PRICING["deepseek-chat"][0])


def test_zero_tokens_zero_cost():
    assert pricing.cost_usd("deepseek-chat", 0, 0) == 0.0


# ---------- usage 接线 ----------


def test_usage_summary_cost_fields():
    from zimeiti_api import usage

    usage.setup()
    usage._exec("DELETE FROM chat_usage")
    usage.record("s-cost", "t1", "deepseek-chat", 1_000_000, 1_000_000)
    usage.record("s-cost", "t2", "unknown-model", 1_000_000, 1_000_000)
    s = usage.summary(session_key="s-cost")
    assert len(s["rows"]) == 2
    by_model = {r["model"]: r for r in s["rows"]}
    assert by_model["deepseek-chat"]["cost_usd"] == pytest.approx(
        pricing.MODEL_PRICING["deepseek-chat"][0] + pricing.MODEL_PRICING["deepseek-chat"][1]
    )
    assert by_model["unknown-model"]["cost_usd"] is None
    assert s["cost_usd"] == pytest.approx(by_model["deepseek-chat"]["cost_usd"])
    assert s["cost_usd_partial"] is True
    usage._exec("DELETE FROM chat_usage")


def test_usage_all_unknown():
    from zimeiti_api import usage

    usage.setup()
    usage._exec("DELETE FROM chat_usage")
    usage.record("s-cost2", "t1", "", 10, 10)
    s = usage.summary(session_key="s-cost2")
    assert s["cost_usd"] is None
    assert s["cost_usd_partial"] is True
    usage._exec("DELETE FROM chat_usage")


# ---------- key 轮换 ----------


def test_key_rotation_chain_order():
    os.environ["ZIMEITI_API_KEYS"] = "key-a,key-b,key-c"
    os.environ["ZIMEITI_FALLBACK_MODELS"] = "gpt-4o-mini"
    m = ar._build_model()
    assert type(m).__name__ == "FallbackChatModel"
    models = m.models
    # 链：主模型×key-a, ×key-b, ×key-c, 备用模型×key-a
    assert len(models) == 4

    def _key(x):
        v = x.openai_api_key
        return str(v.get_secret_value() if hasattr(v, "get_secret_value") else v)

    keys = [_key(x) for x in models]
    assert keys == ["key-a", "key-b", "key-c", "key-a"]
    assert all(x.model_name == "deepseek-chat" for x in models[:3])
    assert models[3].model_name == "gpt-4o-mini"


def test_no_keys_env_unchanged():
    os.environ["ZIMEITI_FALLBACK_MODELS"] = "gpt-4o-mini"
    m = ar._build_model()
    assert len(m.models) == 2  # 主 + 1 备用（原行为）


def test_explicit_model_no_rotation():
    os.environ["ZIMEITI_API_KEYS"] = "key-a,key-b"
    os.environ["ZIMEITI_EXPLICIT_MODEL"] = "1"
    m = ar._build_model()
    assert type(m).__name__ == "ChatOpenAI"  # 显式选择严格不包装


def test_single_key_equals_primary():
    os.environ["ZIMEITI_API_KEYS"] = "key-a"
    os.environ["ZIMEITI_FALLBACK_MODELS"] = "gpt-4o-mini"
    m = ar._build_model()
    assert len(m.models) == 2  # key-a 主 + 备用（与单 key 行为一致，不重复节点）
