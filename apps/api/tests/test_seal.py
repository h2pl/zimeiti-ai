"""seal CLI 验收：凭证加密落盘（宪法 II）+ 缺环境变量 fail-closed。"""


class TestSeal:
    def test_seal_writes_encrypted_credentials(self, monkeypatch, tmp_path):
        from zimeiti_api import seal

        monkeypatch.setenv("ZIMEITI_MASTER_KEY", "test-master-key")
        monkeypatch.setenv("WECHAT_MP_APPID", "wxtest")
        monkeypatch.setenv("WECHAT_MP_APPSECRET", "sectest")
        monkeypatch.setenv("ZIMEITI_CREDENTIALS_DIR", str(tmp_path))

        assert seal.main(["gzh-main"]) == 0
        sealed = (tmp_path / "gzh-main.sealed").read_text(encoding="utf-8").strip()
        # 落盘是密文，不含明文 secret
        assert "sectest" not in sealed
        # 解密后可还原
        from zimeiti_api.credentials import load_account_credentials

        creds = load_account_credentials("gzh-main", credentials_dir=str(tmp_path))
        assert creds == {"app_id": "wxtest", "app_secret": "sectest"}

    def test_seal_fails_closed_without_env(self, monkeypatch, tmp_path):
        from zimeiti_api import seal

        monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: None)  # 隔离本地 .env
        monkeypatch.delenv("WECHAT_MP_APPID", raising=False)
        monkeypatch.delenv("WECHAT_MP_APPSECRET", raising=False)
        monkeypatch.setenv("ZIMEITI_CREDENTIALS_DIR", str(tmp_path))

        assert seal.main(["gzh-main"]) == 1
        assert not (tmp_path / "gzh-main.sealed").exists()
