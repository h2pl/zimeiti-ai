"""seal CLI 验收：凭证加密落盘（宪法 II）+ 缺环境变量 fail-closed。"""


class TestSeal:
    def test_seal_writes_encrypted_credentials(self, monkeypatch, tmp_path):
        from zimeiti_api.core import seal

        monkeypatch.setenv("ZIMEITI_MASTER_KEY", "test-master-key")
        monkeypatch.setenv("WECHAT_MP_APPID", "wxtest")
        monkeypatch.setenv("WECHAT_MP_APPSECRET", "sectest")
        monkeypatch.setenv("ZIMEITI_CREDENTIALS_DIR", str(tmp_path))

        assert seal.main(["gzh-main"]) == 0
        sealed = (tmp_path / "gzh-main.sealed").read_text(encoding="utf-8").strip()
        # 落盘是密文，不含明文 secret
        assert "sectest" not in sealed
        # 解密后可还原
        from zimeiti_api.core.credentials import load_account_credentials

        creds = load_account_credentials("gzh-main", credentials_dir=str(tmp_path))
        assert creds == {"app_id": "wxtest", "app_secret": "sectest"}

    def test_seal_fails_closed_without_env(self, monkeypatch, tmp_path):
        from zimeiti_api.core import seal

        monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: None)  # 隔离本地 .env
        monkeypatch.delenv("WECHAT_MP_APPID", raising=False)
        monkeypatch.delenv("WECHAT_MP_APPSECRET", raising=False)
        monkeypatch.setenv("ZIMEITI_CREDENTIALS_DIR", str(tmp_path))

        assert seal.main(["gzh-main"]) == 1
        assert not (tmp_path / "gzh-main.sealed").exists()


def test_seal_xhs_uses_login_state(monkeypatch, tmp_path):
    """xhs 账号 seal 登录态（非 appid/secret）；登录态缺失 fail-closed。"""
    import json as _json

    import zimeiti_api.core.seal as seal_mod

    state_file = tmp_path / "xhs_state.json"
    state_file.write_text(_json.dumps({"cookies": []}), encoding="utf-8")
    monkeypatch.setattr("zimeiti_api.config.LOGIN_STATE_PATH", str(state_file))
    monkeypatch.delenv("WECHAT_MP_APPID", raising=False)
    monkeypatch.delenv("WECHAT_MP_APPSECRET", raising=False)
    monkeypatch.setenv("ZIMEITI_CREDENTIALS_DIR", str(tmp_path / "creds"))
    monkeypatch.setenv(
        "ZIMEITI_MASTER_KEY",
        __import__("cryptography.fernet", fromlist=["Fernet"]).Fernet.generate_key().decode(),
    )

    # 登录态存在 → 加密落盘
    rc = seal_mod.main(["xhs-main"])
    assert rc == 0
    sealed = (tmp_path / "creds" / "xhs-main.sealed").read_text(encoding="utf-8").strip()
    from zimeiti_api.core.credentials import decrypt_secret

    payload = _json.loads(decrypt_secret(sealed))
    assert "cookies" in payload["login_state"]
    assert payload["sealed_at"]

    # 登录态缺失 → fail-closed 拒绝
    monkeypatch.setattr("zimeiti_api.config.LOGIN_STATE_PATH", str(tmp_path / "nope.json"))
    assert seal_mod.main(["xhs-other"]) == 1
