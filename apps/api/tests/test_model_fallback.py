"""模型 fallback 链（model-resilience-cron）。

TDD RED：zimeiti_api.runtime.model_fallback 尚不存在。
只对基础设施类失败（连接/限流/5xx）切换；4xx 直抛不掩盖配置错误。
"""

import pytest

MOD = "zimeiti_api.runtime.model_fallback"


class _Err(Exception):
    def __init__(self, msg):
        super().__init__(msg)


def _make_stub(status_code=None, conn=False, msg="boom"):
    """构造一个 langchain 风格的异常（按类型名匹配）。"""
    from langchain_core.exceptions import LangChainException

    if conn:

        class APIConnectionError(LangChainException):
            pass

        return APIConnectionError(msg)

    class APIStatusError(LangChainException):
        pass

    e = APIStatusError(msg)
    e.status_code = status_code
    return e


@pytest.fixture()
def fb():
    from zimeiti_api.runtime import model_fallback as m

    return m


def test_switches_on_connection_error(fb):
    calls = []

    class Bad:
        def invoke(self, *a, **k):
            calls.append("bad")
            raise _make_stub(conn=True)

    class Good:
        def invoke(self, *a, **k):
            calls.append("good")
            return "OK"

    chain = fb.FallbackChatModel(models=[Bad(), Good()])
    assert chain.invoke("x") == "OK"
    assert calls == ["bad", "good"]


def test_switches_on_rate_limit(fb):
    class Bad:
        def invoke(self, *a, **k):
            raise _make_stub(status_code=429)

    class Good:
        def invoke(self, *a, **k):
            return "OK"

    assert fb.FallbackChatModel(models=[Bad(), Good()]).invoke("x") == "OK"


def test_switches_on_5xx(fb):
    class Bad:
        def invoke(self, *a, **k):
            raise _make_stub(status_code=500)

    class Good:
        def invoke(self, *a, **k):
            return "OK"

    assert fb.FallbackChatModel(models=[Bad(), Good()]).invoke("x") == "OK"


def test_no_switch_on_4xx(fb):
    class Bad:
        def invoke(self, *a, **k):
            raise _make_stub(status_code=401)

    class Never:
        def invoke(self, *a, **k):
            raise AssertionError("不应切换")

    with pytest.raises(Exception):  # noqa: B017  测试刻意宽匹配
        fb.FallbackChatModel(models=[Bad(), Never()]).invoke("x")


def test_all_fail_raises_last(fb):
    class Bad:
        def invoke(self, *a, **k):
            raise _make_stub(status_code=500)

    with pytest.raises(Exception):  # noqa: B017  测试刻意宽匹配
        fb.FallbackChatModel(models=[Bad(), Bad()]).invoke("x")


def test_no_fallback_single_model(fb):
    class Only:
        def invoke(self, *a, **k):
            return "solo"

    assert fb.FallbackChatModel(models=[Only()]).invoke("x") == "solo"


def test_switch_callback_records(fb):
    seen = []

    class Bad:
        def invoke(self, *a, **k):
            raise _make_stub(conn=True)

    class Good:
        def invoke(self, *a, **k):
            return "OK"

    chain = fb.FallbackChatModel(models=[Bad(), Good()], on_switch=lambda i, e: seen.append(i))
    chain.invoke("x")
    assert seen == [0]
