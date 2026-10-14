"""core 域单元测试：paths / settings / dotenv 集成语义 / timeouts / governance.guard。"""

from __future__ import annotations

import socket

import pytest
from fastapi import HTTPException

from zimeiti_api.core import paths, settings
from zimeiti_api.core.timeouts import TIMEOUT_CHAT, TIMEOUT_DIRECT, TIMEOUT_PRODUCE
from zimeiti_api.governance import guard

# ---------- paths ----------


def test_safe_output_path_ok(tmp_path, monkeypatch):
    f = tmp_path / "a.txt"
    f.write_text("x", encoding="utf-8")
    monkeypatch.setattr(paths, "OUTPUTS_DIR", tmp_path)
    assert paths._safe_output_path("a.txt") == f.resolve()


def test_safe_output_path_escape(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "OUTPUTS_DIR", tmp_path)
    with pytest.raises(HTTPException) as ei:
        paths._safe_output_path("../outside.txt")
    assert ei.value.status_code == 403


def test_safe_output_path_404(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "OUTPUTS_DIR", tmp_path)
    with pytest.raises(HTTPException) as ei:
        paths._safe_output_path("nope.txt")
    assert ei.value.status_code == 404


def test_safe_output_target_dir_and_root(tmp_path, monkeypatch):
    d = tmp_path / "sub"
    d.mkdir()
    monkeypatch.setattr(paths, "OUTPUTS_DIR", tmp_path)
    assert paths._safe_output_target("sub", must_exist=True) == d.resolve()
    with pytest.raises(HTTPException):
        paths._safe_output_target("")  # outputs 根本身 → 403
    with pytest.raises(HTTPException) as ei:
        paths._safe_output_target("new.txt", must_exist=True)  # 不存在 → 404
    assert ei.value.status_code == 404
    # must_exist=False 允许不存在
    assert (
        paths._safe_output_target("new.txt", must_exist=False) == (tmp_path / "new.txt").resolve()
    )


def test_paths_constants():
    assert paths.PROJECT_ROOT.name == "apps"
    assert paths.SKILLS_DIR == paths.PROJECT_ROOT / "skills"
    assert "analytics" in paths.SYSTEM_TOPLEVEL_DIRS
    assert ".png" in paths.IMAGE_EXTS and ".mp4" in paths.VIDEO_EXTS


# ---------- settings ----------


def test_is_set():
    assert settings._is_set("sk-abc")
    assert not settings._is_set("")
    assert not settings._is_set(None)
    assert not settings._is_set("your-api-key")
    assert not settings._is_set("replace_me")
    assert not settings._is_set("xxx")


def test_mask():
    assert settings._mask("abcd1234") == "••••1234"
    assert settings._mask("abc") == "••••"
    assert settings._mask(" ab ") == "••••"


def test_key_configured_with_aliases():
    key = {"env": "K1", "aliases": ["K2"]}
    assert settings._key_configured(key, {"K1": "v"})
    assert settings._key_configured(key, {"K2": "v"})
    assert not settings._key_configured(key, {"K1": "your-api-key"})


def test_guard_env_values_ok_and_bad():
    settings._guard_env_values({"GOOD_KEY_1": "abc-123"})  # 不抛
    with pytest.raises(HTTPException):
        settings._guard_env_values({"bad key": "v"})  # 键名非法
    with pytest.raises(HTTPException):
        settings._guard_env_values({"K": "a\nb"})  # 换行注入
    with pytest.raises(HTTPException):
        settings._guard_env_values({"K": "v;ls"})  # 命令分隔符
    with pytest.raises(HTTPException):
        settings._guard_env_values({"K": "v$(id)"})  # 命令替换


def test_valid_base_url():
    assert settings._valid_base_url("https://api.openai.com/v1")
    assert settings._valid_base_url("http://localhost:8080")
    assert not settings._valid_base_url("ftp://x")
    assert not settings._valid_base_url("https://u:p@host")  # 内嵌凭据
    assert not settings._valid_base_url("https://h\r\ne")  # 控制字符


def test_ssrf_safe(monkeypatch):
    def fake_getaddrinfo(host, port):
        return [(2, 1, 6, "", ("127.0.0.1", 0))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    assert not settings._ssrf_safe("https://internal.example")

    def fake_pub(host, port):
        return [(2, 1, 6, "", ("93.184.216.34", 0))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_pub)
    assert settings._ssrf_safe("https://api.example.com")

    def fake_broken(host, port):
        raise OSError("dns down")

    monkeypatch.setattr(socket, "getaddrinfo", fake_broken)
    assert not settings._ssrf_safe("https://broken.example")


def test_read_env_and_write_env(tmp_path, monkeypatch):
    envf = tmp_path / ".env"
    envf.write_text(
        "# comment\nOPENAI_API_KEY=1\nB=spaced\n\nMINERU_API_TOKEN=3\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(settings, "ENV_FILE", envf)
    assert settings._read_env() == {"OPENAI_API_KEY": "1", "B": "spaced", "MINERU_API_TOKEN": "3"}

    # 更新命中的 key；白名单外的键被过滤
    settings._write_env({"OPENAI_API_KEY": "2", "NOT_ALLOWED": "x"})
    content = envf.read_text(encoding="utf-8")
    assert "OPENAI_API_KEY=2" in content
    assert "NOT_ALLOWED" not in content
    # 注入防护
    with pytest.raises(HTTPException):
        settings._write_env({"OPENAI_API_KEY": "x\nEVIL=1"})
    # 空串 → 删除该行
    settings._write_env({"MINERU_API_TOKEN": ""})
    assert "MINERU_API_TOKEN" not in envf.read_text(encoding="utf-8")


def test_skill_api_configured_branches():
    # 未知 skill 默认已配置（无 spec 不挡）
    assert settings._skill_api_configured("no-such-skill", {})
    env = {k: "x" for k in settings._ENV_ALLOWLIST}
    assert isinstance(settings._skill_api_configured("ai-image-gen", env), bool)
    assert not settings._skill_api_configured("ai-image-gen", {})  # required key 缺失


def test_skill_api_requirements_sane():
    assert "ai-image-gen" in settings.SKILL_API_REQUIREMENTS
    assert "short-drama" in settings.SKILL_API_REQUIREMENTS
    drama = settings.SKILL_API_REQUIREMENTS["short-drama"]
    assert drama["providers"][0]["id"] == "drama"
    # allowlist 非空且键名合法
    assert settings._ENV_ALLOWLIST
    assert all(k.isidentifier() for k in settings._ENV_ALLOWLIST)


def test_proxy_env_defaults():
    env = settings._proxy_env()
    assert "EASEL_ROOT" in env
    assert "no_proxy" in env


# ---------- guard ----------


class FakeRequest:
    def __init__(self, method="POST", path="/api/ideas", headers=None, client_host="127.0.0.1"):
        from types import SimpleNamespace

        self.method = method
        self.url = SimpleNamespace(path=path)
        self.headers = headers or {}
        self.client = SimpleNamespace(host=client_host) if client_host else None


def _next_ok(request):
    async def call_next(req):
        return "OK"

    return call_next


def test_local_ports_and_proxy_origin():
    ports = guard._local_ports("8000")
    assert "7860" in ports and "8000" in ports
    assert guard._proxy_uri_origin("") is None
    assert guard._proxy_uri_origin("https://abc.def.dev.vscode-cdn.net/x") == (
        "abc.def.dev.vscode-cdn.net",
        "https://abc.def.dev.vscode-cdn.net",
    )


def test_write_guard_allows_local_origin():
    import asyncio

    req = FakeRequest(headers={"origin": guard._LOCAL_ORIGINS[0]})
    result = (
        asyncio.get_event_loop_policy()
        .new_event_loop()
        .run_until_complete(guard.local_write_guard(req, _next_ok(req)))
    )
    assert result == "OK"


def test_write_guard_blocks_foreign_origin():
    import asyncio

    req = FakeRequest(headers={"origin": "https://evil.example"})
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(guard.local_write_guard(req, _next_ok(req)))
        assert result.status_code == 403
    finally:
        loop.close()


def test_write_guard_same_origin_host():
    import asyncio

    req = FakeRequest(headers={"origin": "http://127.0.0.1:8000", "host": "127.0.0.1:8000"})
    loop = asyncio.new_event_loop()
    try:
        assert loop.run_until_complete(guard.local_write_guard(req, _next_ok(req))) == "OK"
    finally:
        loop.close()


def test_write_guard_loopback_no_origin():
    import asyncio

    req = FakeRequest(headers={}, client_host="127.0.0.1")
    loop = asyncio.new_event_loop()
    try:
        assert loop.run_until_complete(guard.local_write_guard(req, _next_ok(req))) == "OK"
    finally:
        loop.close()


def test_write_guard_remote_no_origin_blocked():
    import asyncio

    req = FakeRequest(headers={}, client_host="192.168.1.9")
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(guard.local_write_guard(req, _next_ok(req)))
        assert result.status_code == 403
    finally:
        loop.close()


def test_write_guard_get_passes_without_checks():
    import asyncio

    req = FakeRequest(method="GET", headers={"origin": "https://evil.example"})
    loop = asyncio.new_event_loop()
    try:
        assert loop.run_until_complete(guard.local_write_guard(req, _next_ok(req))) == "OK"
    finally:
        loop.close()


def test_loopback_peer_none_client():
    req = FakeRequest(client_host=None)
    assert guard._loopback_peer(req) is False


# ---------- dotenv / timeouts ----------


def test_load_dotenv_integration(tmp_path, monkeypatch):
    """集成语义验证：python-dotenv 以 override=False 挂接（已存在环境变量优先）。"""
    import os

    from dotenv import load_dotenv

    envf = tmp_path / ".env"
    envf.write_text('NEW_KEY="quoted val"\n', encoding="utf-8")
    monkeypatch.delenv("NEW_KEY", raising=False)
    load_dotenv(envf, override=False)
    assert os.environ["NEW_KEY"] == "quoted val"
    monkeypatch.delenv("NEW_KEY", raising=False)


def test_timeouts():
    assert TIMEOUT_PRODUCE == 7200
    assert TIMEOUT_DIRECT == 300
    assert TIMEOUT_CHAT == TIMEOUT_PRODUCE


# ---------- 本机任意端口来源（Vite 自动升端口场景，真实栈回归） ----------


def test_origin_is_local():
    assert guard._origin_is_local("http://localhost:5175") is True
    assert guard._origin_is_local("http://127.0.0.1:59999") is True
    assert guard._origin_is_local("https://foo.localhost") is True
    assert guard._origin_is_local("http://localhost") is True
    assert guard._origin_is_local("https://evil.com") is False
    assert guard._origin_is_local("http://192.168.1.9:5173") is False
    assert guard._origin_is_local("ftp://localhost:5173") is False
    assert guard._origin_is_local("not a url") is False


def test_write_guard_allows_local_origin_any_port():
    import asyncio

    loop = asyncio.new_event_loop()
    try:
        # Vite 自动升端口场景（真实栈回归）：Origin 5175 + Host 8000
        req = FakeRequest(headers={"origin": "http://localhost:5175", "host": "localhost:8000"})
        assert loop.run_until_complete(guard.local_write_guard(req, _next_ok(req))) == "OK"
        # 任意本地端口都放行（根治端口白名单这类 bug）
        req2 = FakeRequest(headers={"origin": "http://127.0.0.1:65123", "host": "localhost:8000"})
        assert loop.run_until_complete(guard.local_write_guard(req2, _next_ok(req2))) == "OK"
        # 跨站攻击页面仍然拒绝
        req3 = FakeRequest(headers={"origin": "https://evil.com", "host": "localhost:8000"})
        resp = loop.run_until_complete(guard.local_write_guard(req3, _next_ok(req3)))
        assert resp.status_code == 403
    finally:
        loop.close()
