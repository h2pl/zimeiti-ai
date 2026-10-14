"""platforms 域测试（第一批）：login / accounts（subprocess 与文件系统全 mock）。"""

from __future__ import annotations

import json
import subprocess
import time
import types
from pathlib import Path

import pytest

from zimeiti_api.platforms import accounts as accounts_mod
from zimeiti_api.platforms import login as login_mod
from zimeiti_api.platforms.common import _WHOAMI_CACHE, _WHOAMI_LOCK, LOGIN_PROCESSES


@pytest.fixture
def fake_login_env(tmp_path, monkeypatch):
    """临时 LOGIN_DIR/PROJECT_ROOT/BROWSER_PROFILES + 受控 LOGIN_RUNNERS。"""
    login_dir = tmp_path / "_login"
    proj = tmp_path / "proj"
    profiles = tmp_path / "profiles"
    login_dir.mkdir()
    proj.mkdir()
    runners = {
        "xhs": {"name": "小红书", "backend": "xhs", "profile": "XhsProfile"},
        "bili": {"name": "B站", "backend": "biliup"},
        "wx": {"name": "公众号", "backend": "wechat-oa"},
        "dead": {"name": "不可用", "backend": "unsupported", "note": "未接入"},
        "kwai": {"name": "快手", "backend": "wp", "wp": "kuaishou", "profile": "KsProfile"},
    }
    monkeypatch.setattr(login_mod, "LOGIN_DIR", login_dir)
    monkeypatch.setattr(login_mod, "PROJECT_ROOT", proj)
    monkeypatch.setattr(login_mod, "BROWSER_PROFILES", profiles)
    monkeypatch.setattr(login_mod, "LOGIN_RUNNERS", runners)
    monkeypatch.setattr(accounts_mod, "LOGIN_DIR", login_dir)
    monkeypatch.setattr(accounts_mod, "PROJECT_ROOT", proj)
    monkeypatch.setattr(accounts_mod, "LOGIN_RUNNERS", runners)
    with _WHOAMI_LOCK:
        _WHOAMI_CACHE.clear()
    LOGIN_PROCESSES.clear()
    yield types.SimpleNamespace(login_dir=login_dir, proj=proj, profiles=profiles, runners=runners)
    LOGIN_PROCESSES.clear()


def _marker(env, platform, state):
    (env.login_dir / f"{platform}.json").write_text(
        json.dumps({"state": state, "message": "", "qr": "", "ts": int(time.time())}),
        encoding="utf-8",
    )


# ---------- _account_logged_in ----------


def test_account_logged_in_branches(fake_login_env, monkeypatch):
    r = fake_login_env.runners
    assert login_mod._account_logged_in("dead", r["dead"]) is False
    # biliup: cookies.json 存在即登录
    assert login_mod._account_logged_in("bili", r["bili"]) is False
    (fake_login_env.proj / "cookies.json").write_text("{}", encoding="utf-8")
    assert login_mod._account_logged_in("bili", r["bili"]) is True
    # wechat-oa: mp 后台会话优先，AppID 兜底
    monkeypatch.setattr(login_mod, "_mp_login_status", lambda: {"state": "success"})
    assert login_mod._account_logged_in("wx", r["wx"]) is True
    monkeypatch.setattr(login_mod, "_mp_login_status", lambda: {"state": "expired"})
    monkeypatch.setattr(login_mod, "_wechat_has_credentials", lambda: True)
    assert login_mod._account_logged_in("wx", r["wx"]) is True
    monkeypatch.setattr(login_mod, "_wechat_has_credentials", lambda: False)
    assert login_mod._account_logged_in("wx", r["wx"]) is False
    monkeypatch.setattr(
        login_mod, "_mp_login_status", lambda: (_ for _ in ()).throw(RuntimeError("x"))
    )
    assert login_mod._account_logged_in("wx", r["wx"]) is False  # 异常吞掉走兜底
    # 标记文件：success / 其它 / 损坏 / 缺失
    _marker(fake_login_env, "xhs", "success")
    assert login_mod._account_logged_in("xhs", r["xhs"]) is True
    _marker(fake_login_env, "xhs", "expired")
    assert login_mod._account_logged_in("xhs", r["xhs"]) is False
    (fake_login_env.login_dir / "xhs.json").write_text("{broken", encoding="utf-8")
    assert login_mod._account_logged_in("xhs", r["xhs"]) is False
    (fake_login_env.login_dir / "xhs.json").unlink()
    assert login_mod._account_logged_in("xhs", r["xhs"]) is False


# ---------- 账号列表与登录状态 ----------


def test_api_accounts_listing(fake_login_env, monkeypatch, client):
    _marker(fake_login_env, "xhs", "success")
    r = client.get("/api/accounts").json()
    by = {a["platform"]: a for a in r}
    assert by["xhs"]["loggedIn"] is True and by["xhs"]["supported"] is True
    assert by["dead"]["supported"] is False and by["dead"]["note"] == "未接入"
    assert by["wx"]["backend"] == "wechat-oa"


def test_login_status_shape(fake_login_env):
    _marker(fake_login_env, "xhs", "qr_ready")
    (fake_login_env.login_dir / "xhs.png").write_bytes(b"png")
    s = login_mod._login_status("xhs")
    assert s["state"] == "qr_ready" and s["qr"] == "_login/xhs.png" and s["qrTs"] > 0
    # 无 qr 文件
    (fake_login_env.login_dir / "xhs.png").unlink()
    s2 = login_mod._login_status("xhs")
    assert s2["qr"] == "" and s2["qrTs"] == 0
    # 状态文件损坏
    (fake_login_env.login_dir / "xhs.json").write_text("{bad", encoding="utf-8")
    assert login_mod._login_status("xhs")["state"] == "unknown"


def test_login_status_dead_process(fake_login_env):
    dead = subprocess.Popen(["cmd", "/c", "exit", "3"])
    dead.wait()
    LOGIN_PROCESSES["xhs"] = dead
    s = login_mod._login_status("xhs")
    assert s["state"] == "error" and "退出码 3" in s["message"]


def test_api_login_status_route(fake_login_env, client):
    assert client.get("/api/login/ghost/status").status_code == 404
    _marker(fake_login_env, "xhs", "success")
    assert client.get("/api/login/xhs/status").json()["state"] == "success"


def test_api_login_sms(fake_login_env, client):
    assert client.post("/api/login/ghost/sms", json={"code": "1234"}).status_code == 404
    assert client.post("/api/login/xhs/sms", json={"code": "12"}).status_code == 400
    assert client.post("/api/login/xhs/sms", json={"code": "ab12cd34ef"}).status_code == 200
    assert (fake_login_env.login_dir / "xhs.code").read_text(encoding="utf-8") == "1234"


def test_api_login_start_branches(fake_login_env, monkeypatch, client):
    assert client.post("/api/login/ghost").status_code == 404
    r = client.post("/api/login/dead")
    assert r.status_code == 400 and "未接入" in r.json()["detail"]
    r2 = client.post("/api/login/wx")
    assert r2.json()["mode"] == "credentials" and "AppID" in r2.json()["message"]
    # 浏览器平台：Popen mock + 预置二维码 → 第一轮轮询即返回
    (fake_login_env.login_dir / "xhs.png").write_bytes(b"png")
    started = {}

    class FakeProc:
        def poll(self):
            return None

        def terminate(self):
            pass

        pid = 4242

    def fake_popen(cmd, **kw):
        started["qr_out"] = cmd[cmd.index("--qr-out") + 1]
        started["cmd"] = cmd
        assert "--qr-out" in cmd and "--status-file" in cmd
        # 路由启动前会先删旧 qr/status，mock 进程"启动后"补写二维码 → 轮询第一轮即就绪
        Path(started["qr_out"]).write_bytes(b"png")
        return FakeProc()

    monkeypatch.setattr(login_mod.subprocess, "Popen", fake_popen)
    r3 = client.post("/api/login/xhs")
    body = r3.json()
    assert body["mode"] == "qr" and body["qr"] == "_login/xhs.png"
    assert started["cmd"][1].endswith("xhs_publish.py")
    assert "xhs" in LOGIN_PROCESSES
    # 状态端点在 success 时清 whoami 缓存
    with _WHOAMI_LOCK:
        _WHOAMI_CACHE["xhs"] = (time.time(), {"loggedIn": False})
    _marker(fake_login_env, "xhs", "success")
    client.get("/api/login/xhs/status")
    with _WHOAMI_LOCK:
        assert "xhs" not in _WHOAMI_CACHE


# ---------- logout ----------


def test_api_logout_normal(fake_login_env, client):
    prof = fake_login_env.profiles / "XhsProfile"
    prof.mkdir(parents=True)
    _marker(fake_login_env, "xhs", "success")
    (fake_login_env.login_dir / "xhs.png").write_bytes(b"p")
    (fake_login_env.login_dir / "xhs-me.png").write_bytes(b"p")
    r = client.post("/api/logout/xhs").json()
    assert r["ok"] is True
    assert "XhsProfile" in r["deleted"] and "xhs.json" in r["deleted"]
    assert not prof.exists() and not (fake_login_env.login_dir / "xhs.json").exists()
    assert client.post("/api/logout/ghost").status_code == 404


def test_api_logout_bili(fake_login_env, client):
    (fake_login_env.proj / "cookies.json").write_text("{}", encoding="utf-8")
    r = client.post("/api/logout/bili").json()
    assert "cookies.json" in r["deleted"]
    assert not (fake_login_env.proj / "cookies.json").exists()


def test_api_logout_wechat(fake_login_env, monkeypatch, client):
    cleared = []
    monkeypatch.setattr(login_mod, "_wechat_clear_credentials", lambda: cleared.append(1))
    live = subprocess.Popen(["cmd", "/c", "ping -n 5 127.0.0.1 >nul"])
    LOGIN_PROCESSES["wechat-oa-mp"] = live
    (fake_login_env.login_dir / "wechat-oa-mp.json").write_text("{}", encoding="utf-8")
    (fake_login_env.login_dir / "wx.json").write_text("{}", encoding="utf-8")
    r = client.post("/api/logout/wx").json()
    assert r["ok"] is True and cleared
    assert "wechat-publisher.yaml:accounts.web" in r["deleted"]
    assert "wechat-oa-mp.json" in r["deleted"]
    assert not (fake_login_env.login_dir / "wx.json").exists()
    live.terminate()
    live.wait()


# ---------- whoami ----------


def _fake_run(stdout: str, returncode: int = 0):
    def run(cmd, **kw):
        return subprocess.CompletedProcess(cmd, returncode, stdout, "")

    return run


def test_whoami_unknown_and_unsupported(fake_login_env, client):
    assert client.get("/api/accounts/ghost/whoami").status_code == 404
    r = client.get("/api/accounts/dead/whoami").json()
    assert r == {"loggedIn": False, "name": "", "avatar": ""}


def test_whoami_wechat_oa(fake_login_env, monkeypatch, client):
    monkeypatch.setattr(accounts_mod, "_wechat_web_account", lambda: {"name": "测试号"})
    monkeypatch.setattr(accounts_mod, "_account_logged_in", lambda pf, cfg: True)
    r = client.get("/api/accounts/wx/whoami").json()
    assert r == {"loggedIn": True, "name": "测试号", "avatar": ""}


def test_whoami_subprocess_flow(fake_login_env, monkeypatch, client):
    js = json.dumps({"loggedIn": True, "name": "阿明", "avatar": "a.png"})
    monkeypatch.setattr(accounts_mod.subprocess, "run", _fake_run(js))
    marker = {}
    monkeypatch.setattr(
        accounts_mod, "_write_login_marker", lambda pf, st, name: marker.update({pf: st})
    )
    r = client.get("/api/accounts/xhs/whoami").json()
    assert r == {"loggedIn": True, "name": "阿明", "avatar": "a.png"}
    assert marker["xhs"] == "success"  # 登录确认回写标记
    with _WHOAMI_LOCK:
        assert "xhs" in _WHOAMI_CACHE  # 可信结论才缓存

    # 缓存命中（TTL 内）不再起子进程
    monkeypatch.setattr(accounts_mod.subprocess, "run", _fake_run("", 1))
    r2 = client.get("/api/accounts/xhs/whoami").json()
    assert r2["name"] == "阿明"

    # 不可信输出（error 字段）→ 读标记兜底，不缓存不删标记
    with _WHOAMI_LOCK:
        _WHOAMI_CACHE.clear()
    _marker(fake_login_env, "kwai", "success")
    monkeypatch.setattr(
        accounts_mod.subprocess,
        "run",
        _fake_run(json.dumps({"loggedIn": False, "error": "crash"})),
    )
    r3 = client.get("/api/accounts/kwai/whoami").json()
    assert r3["loggedIn"] is True  # 上次已知状态
    with _WHOAMI_LOCK:
        assert "douyin" not in _WHOAMI_CACHE

    # 可信未登录 → 删标记
    monkeypatch.setattr(accounts_mod.subprocess, "run", _fake_run(json.dumps({"loggedIn": False})))
    _marker(fake_login_env, "kwai", "success")
    r4 = client.get("/api/accounts/kwai/whoami").json()
    assert r4["loggedIn"] is False
    assert not (fake_login_env.login_dir / "kwai.json").exists()

    # 从倒数行找 JSON（stdout 混有日志行）
    with _WHOAMI_LOCK:
        _WHOAMI_CACHE.clear()
    monkeypatch.setattr(accounts_mod.subprocess, "run", _fake_run("log line\nlog2\n" + js))
    assert client.get("/api/accounts/xhs/whoami").json()["name"] == "阿明"


def test_whoami_timeout(fake_login_env, monkeypatch, client):
    def run(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd, 150)

    monkeypatch.setattr(accounts_mod.subprocess, "run", run)
    r = client.get("/api/accounts/xhs/whoami")
    assert r.status_code == 504
