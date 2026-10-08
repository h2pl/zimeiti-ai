"""Task 5.3 验收：合规审查闸门 fail-closed。"""

import pytest

from zimeiti_api.compliance import ComplianceGate


@pytest.fixture
def gate():
    return ComplianceGate()


def test_clean_content_passes(gate):
    r = gate.review("三招提升周报效率，亲测有效")
    assert r["passed"] is True
    assert r["violations"] == []


def test_api_key_leak_blocked(gate):
    r = gate.review("我的key是 sk-abcdef1234567890 分享给大家")
    assert r["passed"] is False
    assert any("凭证" in v for v in r["violations"])


def test_ai_self_disclosure_blocked(gate):
    r = gate.review("作为一个AI语言模型，我建议你…")
    assert r["passed"] is False


def test_exaggerated_claims_blocked(gate):
    r = gate.review("这个方法稳赚不赔，百分百涨粉")
    assert r["passed"] is False
    assert any("夸大" in v for v in r["violations"])


def test_gate_itself_failing_is_fail_closed(gate, monkeypatch):
    # 审查器自身出错时必须阻断（fail-closed），不能放行
    def boom(text):
        raise RuntimeError("审查服务挂了")
    monkeypatch.setattr(gate, "_check_rules", boom)
    r = gate.review("普通内容")
    assert r["passed"] is False
    assert "审查器异常" in r["violations"][0]
