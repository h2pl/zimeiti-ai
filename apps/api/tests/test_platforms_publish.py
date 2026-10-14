"""platforms 域测试（第二批）：publish / wechat / analytics（subprocess 全 mock）。"""

from __future__ import annotations

import json
import subprocess
import time
import types
from pathlib import Path

import pytest

from zimeiti_api.core import paths as paths_mod
from zimeiti_api.platforms import analytics as analytics_mod
from zimeiti_api.platforms import publish as publish_mod
from zimeiti_api.platforms import wechat as wechat_mod
from zimeiti_api.platforms.common import _WHOAMI_CACHE, _WHOAMI_LOCK, LOGIN_PROCESSES


@pytest.fixture
def pub_env(tmp_path, monkeypatch):
    """发布域的临时文件系统 + 受控 runners + pg mock。"""
    publish_dir = tmp_path / "_publish"
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    publish_dir.mkdir()
    runners = {
        "xiaohongshu": {"name": "小红书", "backend": "xhs"},
        "bilibili": {"name": "B站", "backend": "biliup"},
        "douyin": {"name": "抖音", "backend": "douyin"},
        "kwai": {"name": "快手", "backend": "wp", "wp": "kuaishou"},
        "wechat-oa": {"name": "公众号", "backend": "wechat-oa"},
        "dead": {"name": "不可用", "backend": "unsupported"},
    }
    sched = {"items": []}
    monkeypatch.setattr(publish_mod, "LOGIN_RUNNERS", runners)
    monkeypatch.setattr(publish_mod, "PUBLISH_DIR", publish_dir)
    monkeypatch.setattr(publish_mod, "OUTPUTS_DIR", outputs)
    # _safe_output_path 读 paths.OUTPUTS_DIR —— 必须一并重定向
    monkeypatch.setattr(paths_mod, "OUTPUTS_DIR", outputs)
    monkeypatch.setattr(publish_mod, "PROJECT_ROOT", tmp_path / "proj")
    monkeypatch.setattr(publish_mod.pg, "schedule_list", lambda: list(sched["items"]))
    monkeypatch.setattr(
        publish_mod.pg, "schedule_replace_all", lambda items: sched.update(items=list(items))
    )
    monkeypatch.setattr(analytics_mod, "LOGIN_RUNNERS", runners)
    with _WHOAMI_LOCK:
        _WHOAMI_CACHE.clear()
    LOGIN_PROCESSES.clear()
    yield types.SimpleNamespace(
        publish_dir=publish_dir, outputs=outputs, runners=runners, sched=sched
    )
    LOGIN_PROCESSES.clear()


def _mk_media(base: Path, img=True, vid=True):
    out = []
    if img:
        f = base / "img1.png"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"png")
        out.append("img1.png")
    if vid:
        f = base / "vid1.mp4"
        f.write_bytes(b"mp4")
        out.append("vid1.mp4")
    return out


# ---------- publish 状态/短信 ----------


def test_publish_status_route(pub_env, client):
    assert client.get("/api/publish/ghost/status").status_code == 404
    assert client.get("/api/publish/xiaohongshu/status").json() == {
        "mode": "publish",
        "state": "unknown",
        "message": "",
    }
    (pub_env.publish_dir / "xiaohongshu.json").write_text(
        json.dumps({"state": "success", "message": "ok"}), encoding="utf-8"
    )
    assert client.get("/api/publish/xiaohongshu/status").json()["state"] == "success"


def test_publish_sms_route(pub_env, client):
    assert client.post("/api/publish/ghost/sms", json={"code": "1234"}).status_code == 404
    assert client.post("/api/publish/xiaohongshu/sms", json={"code": "x"}).status_code == 400
    r = client.post("/api/publish/douyin/sms", json={"code": "ab1234"})
    assert r.json() == {"ok": True}
    assert (pub_env.publish_dir / "douyin.code").read_text(encoding="utf-8") == "1234"


# ---------- publish 校验分支 ----------


def test_publish_validation(pub_env, client, tmp_path, monkeypatch):
    assert client.post("/api/publish/ghost", json={"title": "t"}).status_code == 404
    r = client.post("/api/publish/dead", json={"title": "t"})
    assert r.status_code == 400 and "暂不支持" in r.json()["detail"]
    assert (
        client.post("/api/publish/xiaohongshu", json={"title": "  ", "body": " "}).status_code
        == 400
    )
    # xhs 需要媒体
    r2 = client.post("/api/publish/xiaohongshu", json={"title": "t", "body": "b"})
    assert r2.status_code == 400 and "需附带" in r2.json()["detail"]
    # 图视频同发 400
    media = _mk_media(pub_env.outputs)
    r3 = client.post("/api/publish/xiaohongshu", json={"title": "t", "media": [media[0], media[1]]})
    assert r3.status_code == 400 and "二选一" in r3.json()["detail"]
    # douyin 只能视频
    r4 = client.post("/api/publish/douyin", json={"title": "t", "media": [media[0]]})
    assert r4.status_code == 400 and "只能发视频" in r4.json()["detail"]


def test_publish_sync_success_and_schedule_reflux(pub_env, monkeypatch, client):
    media = _mk_media(pub_env.outputs, vid=False)
    captured = {}

    def fake_run(cmd, **kw):
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, "ok output", "")

    monkeypatch.setattr(publish_mod.subprocess, "run", fake_run)
    r = client.post(
        "/api/publish/xiaohongshu",
        json={"title": "标题", "body": "正文", "tags": "#a", "media": media},
    )
    body = r.json()
    assert body["ok"] is True and body["message"] == "发布成功"
    cmd = captured["cmd"]
    assert "xhs_publish.py" in cmd[1] and "publish" in cmd and "--exec" in cmd
    assert any("img1.png" in c for c in cmd)
    # 成功回流排期
    assert len(pub_env.sched["items"]) == 1
    item = pub_env.sched["items"][0]
    assert item["status"] == "published" and item["source"] == "publish-page"
    assert (pub_env.outputs / "_publish.log").is_file()


def test_publish_sync_failure_detail(pub_env, monkeypatch, client):
    media = _mk_media(pub_env.outputs, img=False)
    monkeypatch.setattr(
        publish_mod.subprocess,
        "run",
        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 3, "", " boom\nerr-line"),
    )
    r = client.post("/api/publish/bilibili", json={"title": "t", "media": media})
    body = r.json()
    assert body["ok"] is False and "err-line" in body["detail"]
    assert pub_env.sched["items"] == []  # 失败不回流


def test_publish_bilibili_cmd(pub_env, monkeypatch, client):
    media = _mk_media(pub_env.outputs, img=False)
    captured = {}

    def fake_run(cmd, **kw):
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(publish_mod.subprocess, "run", fake_run)
    client.post(
        "/api/publish/bilibili", json={"title": "t" * 100, "tags": "#知识#，测试", "media": media}
    )
    cmd = captured["cmd"]
    assert cmd[0] == "biliup" and "--tid" in cmd and "36" in cmd
    assert "知识,测试" in cmd  # 标签清洗
    assert "--copyright" in cmd


def test_publish_douyin_async_flow(pub_env, monkeypatch, client):
    media = _mk_media(pub_env.outputs, img=False)

    def fake_run(cmd, **kw):
        # 后台线程：模拟脚本写终态
        sf = Path(cmd[cmd.index("--status-file") + 1])
        sf.write_text(json.dumps({"state": "success", "message": "已发布"}), encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(publish_mod.subprocess, "run", fake_run)
    r = client.post("/api/publish/douyin", json={"title": "t", "media": media})
    body = r.json()
    assert body["async"] is True and body["pending"] is True and "ok" not in body
    for _ in range(50):
        st = client.get("/api/publish/douyin/status").json()
        if st["state"] == "success":
            break
        time.sleep(0.05)
    assert st["state"] == "success"
    assert (pub_env.publish_dir / "douyin.code").exists() is False  # 码文件清理


def test_publish_douyin_async_crash_fallback(pub_env, monkeypatch, client):
    media = _mk_media(pub_env.outputs, img=False)
    monkeypatch.setattr(
        publish_mod.subprocess,
        "run",
        lambda cmd, **kw: (_ for _ in ()).throw(RuntimeError("spawn failed")),
    )
    client.post("/api/publish/douyin", json={"title": "t", "media": media})
    for _ in range(50):
        st = client.get("/api/publish/douyin/status").json()
        if st["state"] == "error":
            break
        time.sleep(0.05)
    assert st["state"] == "error" and "异常" in st["message"]


def test_publish_wechat_oa(pub_env, monkeypatch, client, tmp_path):
    media = _mk_media(pub_env.outputs, vid=False)
    # 未登录 mp 后台 → 400
    monkeypatch.setattr(publish_mod, "_mp_login_status", lambda: {"state": "expired"})
    r = client.post("/api/publish/wechat-oa", json={"title": "t", "media": media})
    assert r.status_code == 400 and "未登录" in r.json()["detail"]
    # 已登录但只有视频 → 400
    monkeypatch.setattr(publish_mod, "_mp_login_status", lambda: {"state": "success"})
    vid_media = _mk_media(pub_env.outputs, img=False)
    assert (
        client.post("/api/publish/wechat-oa", json={"title": "t", "media": vid_media}).status_code
        == 400
    )
    # 成功路径：converter mock 产出 html，发布脚本 mock 成功
    monkeypatch.setattr(publish_mod, "WECHAT_SKILL_SCRIPTS", tmp_path / "skillscripts")
    monkeypatch.setattr(publish_mod, "SHARED_SCRIPTS", tmp_path / "shared")

    def fake_run(cmd, **kw):
        if "html_converter.py" in " ".join(cmd):
            out = Path(cmd[cmd.index("-o") + 1])
            out.write_text("<html>ok</html>", encoding="utf-8")
            return subprocess.CompletedProcess(cmd, 0, "", "")
        return subprocess.CompletedProcess(cmd, 0, "published", "")

    captured2 = []
    real_fake_run = fake_run

    def capturing_run(cmd, **kw):
        captured2.append(cmd)
        return real_fake_run(cmd, **kw)

    monkeypatch.setattr(publish_mod.subprocess, "run", capturing_run)
    r2 = client.post("/api/publish/wechat-oa", json={"title": "文", "body": "b", "media": media})
    assert r2.json()["ok"] is True
    assert any("weixin_mp_stats.py" in " ".join(c) for c in captured2)
    assert any("html_converter.py" in " ".join(c) for c in captured2)


def test_publish_timeout(pub_env, monkeypatch, client):
    media = _mk_media(pub_env.outputs, img=False)

    def fake_run(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd, 600)

    monkeypatch.setattr(publish_mod.subprocess, "run", fake_run)
    r = client.post("/api/publish/xiaohongshu", json={"title": "t", "media": media})
    assert r.status_code == 504


def test_publish_env_flag():
    env = publish_mod._publish_env()
    assert env["EASEL_CALENDAR_AUTORECORD"] == "0"


# ---------- wechat ----------


@pytest.fixture
def wx_env(tmp_path, monkeypatch):
    scripts = tmp_path / "skill" / "scripts"
    scripts.mkdir(parents=True)
    monkeypatch.setattr(wechat_mod, "WECHAT_SKILL_DIR", tmp_path / "skill")
    monkeypatch.setattr(wechat_mod, "WECHAT_SKILL_SCRIPTS", scripts)
    monkeypatch.setattr(
        wechat_mod, "WECHAT_CONFIG_YAML", tmp_path / "skill" / "wechat-publisher.yaml"
    )
    monkeypatch.setattr(wechat_mod, "LOGIN_DIR", tmp_path / "_login")
    import zimeiti_api.platforms.login as login_mod2

    monkeypatch.setattr(login_mod2, "LOGIN_DIR", tmp_path / "_login")
    monkeypatch.setattr(wechat_mod, "PROJECT_ROOT", tmp_path / "proj")
    monkeypatch.setattr(
        wechat_mod, "LOGIN_RUNNERS", {"wx": {"name": "公众号", "backend": "wechat-oa"}}
    )
    (tmp_path / "_login").mkdir()
    with _WHOAMI_LOCK:
        _WHOAMI_CACHE.clear()
    LOGIN_PROCESSES.clear()
    yield tmp_path
    LOGIN_PROCESSES.clear()


def test_wechat_credentials_roundtrip(wx_env):
    assert wechat_mod._wechat_load_yaml() == {}
    assert wechat_mod._wechat_web_account() == {}
    assert wechat_mod._wechat_has_credentials() is False
    wechat_mod._wechat_save_credentials("wx1234567890", "sec", name="我的号", author="作者")
    acc = wechat_mod._wechat_web_account()
    assert acc["app_id"] == "wx1234567890" and acc["name"] == "我的号"
    assert wechat_mod._wechat_has_credentials() is True
    # 再存保留其它字段；损坏 yaml → 空 dict
    wechat_mod._wechat_save_credentials("wx2", "s2")
    assert wechat_mod._wechat_web_account()["app_id"] == "wx2"
    wechat_mod.WECHAT_CONFIG_YAML.write_text("{bad yaml", encoding="utf-8")
    assert wechat_mod._wechat_load_yaml() == {}
    # 清除
    wechat_mod._wechat_save_credentials("wx3", "s3")
    wechat_mod._wechat_clear_credentials()
    assert wechat_mod._wechat_has_credentials() is False
    assert not wechat_mod._wechat_load_yaml().get("accounts", {}).get("web")


def test_wechat_env_modes(monkeypatch):
    monkeypatch.delenv("WECHAT_EGRESS_PROXY", raising=False)
    env = wechat_mod._wechat_env()
    assert "api.weixin.qq.com" in env["no_proxy"]  # 直连模式
    monkeypatch.setenv("WECHAT_EGRESS_PROXY", "http://1.2.3.4:8080")
    env2 = wechat_mod._wechat_env()
    assert env2["https_proxy"] == "http://1.2.3.4:8080"
    assert "api.weixin.qq.com" not in env2["no_proxy"]  # 代理模式剔除微信域名


def test_wechat_verify_token_mock(wx_env, monkeypatch):
    monkeypatch.setattr(
        wechat_mod.subprocess,
        "run",
        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, "OK", ""),
    )
    assert wechat_mod._wechat_verify_token() == (True, "")
    monkeypatch.setattr(
        wechat_mod.subprocess,
        "run",
        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, "ERR:40164", ""),
    )
    ok, msg = wechat_mod._wechat_verify_token()
    assert ok is False and "40164" in msg
    monkeypatch.setattr(
        wechat_mod.subprocess,
        "run",
        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, "junk", "trace last"),
    )
    ok2, msg2 = wechat_mod._wechat_verify_token()
    assert ok2 is False and "trace last" in msg2

    def timeout_run(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd, 30)

    monkeypatch.setattr(wechat_mod.subprocess, "run", timeout_run)
    ok3, msg3 = wechat_mod._wechat_verify_token()
    assert ok3 is False and "超时" in msg3


def test_wechat_credentials_routes(wx_env, monkeypatch, client):
    assert client.get("/api/accounts/xhs/credentials").status_code == 404
    assert (
        client.post(
            "/api/accounts/xhs/credentials", json={"appId": "a", "appSecret": "b"}
        ).status_code
        == 404
    )
    assert client.get("/api/accounts/wx/credentials").json()["configured"] is False
    # 保存+验证通过
    monkeypatch.setattr(wechat_mod, "_wechat_verify_token", lambda: (True, ""))
    r = client.post(
        "/api/accounts/wx/credentials",
        json={"appId": "wx1234567890ab", "appSecret": "s", "name": "号"},
    )
    assert r.json() == {"ok": True, "message": "公众号凭证已保存并验证通过"}
    r2 = client.get("/api/accounts/wx/credentials").json()
    assert r2["configured"] is True
    assert r2["appIdMasked"].startswith("wx1234") and "***" in r2["appIdMasked"]
    assert r2["appIdMasked"] != "wx1234567890ab"  # 脱敏
    # 保存但验证失败
    monkeypatch.setattr(wechat_mod, "_wechat_verify_token", lambda: (False, "IP 白名单"))
    r3 = client.post("/api/accounts/wx/credentials", json={"appId": "w", "appSecret": "s"})
    assert r3.json()["ok"] is False and "IP 白名单" in r3.json()["message"]
    # 空字段
    assert (
        client.post("/api/accounts/wx/credentials", json={"appId": "", "appSecret": ""}).status_code
        == 400
    )


def test_wechat_mp_login_status(wx_env):
    assert wechat_mod._mp_login_status() == {"state": "unknown", "message": "", "qr": "", "qrTs": 0}
    st = wx_env / "_login" / "wechat-oa-mp.json"
    st.write_text(json.dumps({"state": "qr_ready", "message": "m"}), encoding="utf-8")
    (wx_env / "_login" / "wechat-oa-mp.png").write_bytes(b"p")
    s = wechat_mod._mp_login_status()
    assert s["state"] == "qr_ready" and s["qr"].endswith("wechat-oa-mp.png")


def test_wechat_mp_login_routes(wx_env, monkeypatch, client):
    assert client.get("/api/accounts/xhs/mp-login/status").status_code == 404
    assert client.post("/api/accounts/xhs/mp-login").status_code == 404
    # 正在跑的登录复用
    live = subprocess.Popen(["cmd", "/c", "ping -n 3 127.0.0.1 >nul"])
    LOGIN_PROCESSES["wechat-oa-mp"] = live
    r = client.post("/api/accounts/wx/mp-login")
    assert r.json()["mode"] == "qr"
    live.terminate()
    live.wait()
    # 新启动：fake Popen 写二维码
    started = {}

    class FakeProc:
        pid = 1

        def poll(self):
            return None

        def terminate(self):
            pass

        def wait(self, timeout=None):
            return 0

    def fake_popen(cmd, **kw):
        started["cmd"] = cmd
        Path(cmd[cmd.index("--qr-out") + 1]).write_bytes(b"png")
        return FakeProc()

    monkeypatch.setattr(wechat_mod.subprocess, "Popen", fake_popen)
    r2 = client.post("/api/accounts/wx/mp-login")
    assert r2.json()["qr"].endswith("wechat-oa-mp.png")
    assert "weixin_mp_stats.py" in started["cmd"][1]
    assert "wechat-oa-mp" in LOGIN_PROCESSES


def test_wechat_shutdown_recovers_proc(wx_env, monkeypatch):
    class FakeLive:
        def __init__(self):
            self.terminated = False

        def poll(self):
            return None

        def terminate(self):
            self.terminated = True

        def wait(self, timeout=None):
            return 0

    live = FakeLive()
    LOGIN_PROCESSES["wechat-oa-mp"] = live
    wechat_mod._stop_mp_login_on_shutdown()
    assert live.terminated
    assert "wechat-oa-mp" not in LOGIN_PROCESSES
    # 写了 expired 标记
    st = wx_env / "_login" / "wechat-oa-mp.json"
    assert json.loads(st.read_text(encoding="utf-8"))["state"] == "expired"
    wechat_mod._stop_mp_login_on_shutdown()  # 无进程时不抛


# ---------- analytics ----------


def test_analytics_platforms_list(monkeypatch, client):
    monkeypatch.setattr(
        analytics_mod,
        "LOGIN_RUNNERS",
        {"xiaohongshu": {"name": "小红书"}, "dead": {"name": "不可用"}},
    )
    monkeypatch.setattr(analytics_mod, "_account_logged_in", lambda pf, cfg: pf == "xiaohongshu")
    lst = client.get("/api/analytics/platforms").json()
    assert [p["platform"] for p in lst] == ["xiaohongshu"]
    assert lst[0]["loggedIn"] is True


def test_analytics_fetch(monkeypatch, client, tmp_path):
    captured = {}

    def fake_run(cmd, **kw):
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, 'log\n{"fans": 1, "works": 2}\n', "")

    monkeypatch.setattr(analytics_mod.subprocess, "run", fake_run)
    monkeypatch.setattr(analytics_mod, "PROJECT_ROOT", tmp_path)
    r = client.get("/api/analytics/douyin").json()
    assert r == {"fans": 1, "works": 2}
    assert "account_stats.py" in captured["cmd"][1]

    # bilibili 走 cookies 分支
    client.get("/api/analytics/bilibili")
    assert "bili_login.py" in captured["cmd"][1]
    # wechat-oa 走 mp stats 分支
    client.get("/api/analytics/wechat-oa")
    assert "weixin_mp_stats.py" in captured["cmd"][1]

    # 不支持的平台
    assert client.get("/api/analytics/ghost").status_code == 404
    # 无 JSON 输出 → 502
    monkeypatch.setattr(
        analytics_mod.subprocess,
        "run",
        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, "no json here", "err tail"),
    )
    r2 = client.get("/api/analytics/douyin")
    assert r2.status_code == 502 and "err tail" in r2.json()["detail"]

    # 超时
    def trun(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd, 180)

    monkeypatch.setattr(analytics_mod.subprocess, "run", trun)
    assert client.get("/api/analytics/douyin").status_code == 504
