"""Task 6.1/6.4 验收：发布执行器框架（频控/白名单 fail-closed）+ 凭证加密。"""

import base64
import os

import pytest
from cryptography.fernet import Fernet


@pytest.fixture(autouse=True)
def _master_key(monkeypatch):
    monkeypatch.setenv("ZIMEITI_MASTER_KEY", Fernet.generate_key().decode())

from zimeiti_api.publisher import PublishExecutor, RateLimitExceeded, AccountNotAllowed
from zimeiti_api.credentials import encrypt_secret, decrypt_secret


@pytest.fixture
def executor():
    return PublishExecutor(daily_limit=1, allowed_accounts={"xhs-main", "gzh-main"})


class TestExecutor:
    def test_publish_within_limit_succeeds(self, executor):
        result = executor.publish("xhs-main", {"title": "t", "body": "b"})
        assert result["platform_result"] == "submitted"  # mock 平台返回 submitted

    def test_rate_limit_blocks_second_publish_same_day(self, executor):
        executor.publish("xhs-main", {"title": "t1", "body": "b"})
        with pytest.raises(RateLimitExceeded):
            executor.publish("xhs-main", {"title": "t2", "body": "b"})

    def test_account_not_in_whitelist_denied(self, executor):
        with pytest.raises(AccountNotAllowed):
            executor.publish("unknown-account", {"title": "t", "body": "b"})

    def test_denied_request_never_calls_platform(self, executor):
        # 白名单拒绝时，平台调用函数绝不能被执行
        called = []
        with pytest.raises(AccountNotAllowed):
            executor.publish("unknown-account", {"title": "t", "body": "b"},
                             platform_call=lambda d: called.append(d) or "ok")
        assert called == []


class TestCredentials:
    def test_encrypt_decrypt_roundtrip(self):
        token = "a2f5c=XhS2C9ozz3cup8IZBpZ8; web_session=abc123"
        sealed = encrypt_secret(token)
        assert sealed != token                      # 密文不等于明文
        assert token not in sealed                 # 明文不出现在密文中
        assert decrypt_secret(sealed) == token

    def test_sealed_text_is_not_plain_base64_of_secret(self):
        token = "very-secret-cookie-value"
        sealed = encrypt_secret(token)
        # 密文不等于明文的朴素 base64（证明真的加密了）
        assert sealed != base64.b64encode(token.encode()).decode()
        # 换一把主密钥必须解不开
        os.environ["ZIMEITI_MASTER_KEY"] = Fernet.generate_key().decode()
        with pytest.raises(Exception):
            decrypt_secret(sealed)
