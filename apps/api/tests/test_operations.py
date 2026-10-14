"""operations 域测试：env（环境面板）+ models（模型通道）（subprocess/httpx 全 mock）。"""

from __future__ import annotations

import json
import subprocess
import time

import pytest
from fastapi import HTTPException

from zimeiti_api.core import settings
from zimeiti_api.operations import env as env_mod
from zimeiti_api.operations import models as models_mod


@pytest.fixture(autouse=True)
def isolated_env_files(tmp_path, monkeypatch):
    """settings 与 models 两个模块的 ENV_FILE 都指向同一临时文件（两处定义，行为与线上一致）。"""
    envf = tmp_path / ".env"
    monkeypatch.setattr(settings, "ENV_FILE", envf)
    monkeypatch.setattr(models_mod, "ENV_FILE", envf)
    env_mod._ENV_TOOLS_CACHE.update({"ts": 0.0, "data": None})
    env_mod._INSTALL_IDS_CACHE.update({"ts": 0.0, "ids": frozenset()})
    env_mod._ENV_JOBS.clear()
    yield envf
    env_mod._ENV_JOBS.clear()


# ---------- env ----------


def test_env_save_route(isolated_env_files, client):
    r = client.post("/api/env", json={"updates": {"NOT_IN_ALLOWLIST": "x"}})
    assert r.status_code == 400 and "不允许写入" in r.json()["detail"]
    r2 = client.post(
        "/api/env",
        json={"updates": {"IMG_API_KEY": "sk-test-12345678", "IMG_BASE_URL": "https://x/v1"}},
    )
    assert r2.json()["ok"] is True
    sk = r2.json()["skills"]
    assert "ai-image-gen" in sk and isinstance(sk["ai-image-gen"], bool)
    assert sk["ai-image-gen"] is True  # IMG_API_KEY 已写
    assert "IMG_API_KEY=sk-test-12345678" in isolated_env_files.read_text(encoding="utf-8")
    # 注入值被 _write_env 拒绝
    r3 = client.post("/api/env", json={"updates": {"IMG_API_KEY": "a\nEVIL=1"}})
    assert r3.status_code == 400


def _fake_check_run(stdout: str, returncode: int = 0):
    def run(*a, **kw):
        return subprocess.CompletedProcess(a[0] if a else [], returncode, stdout, "err-out")

    return run


def test_env_tools_cache_and_errors(monkeypatch, client):
    # 体检失败 → 500
    monkeypatch.setattr(env_mod.subprocess, "run", _fake_check_run("", 1))
    assert client.get("/api/env/tools").status_code == 500
    # 坏 JSON → 500
    monkeypatch.setattr(env_mod.subprocess, "run", _fake_check_run("not-json", 0))
    assert client.get("/api/env/tools").status_code == 500
    # 正常 → 缓存
    payload = json.dumps({"tools": [{"id": "t1", "ok": True}]})
    monkeypatch.setattr(env_mod.subprocess, "run", _fake_check_run(payload, 0))
    d = client.get("/api/env/tools").json()
    assert d["tools"][0]["id"] == "t1" and "cachedAt" in d
    # 缓存命中（不再调 subprocess）
    monkeypatch.setattr(
        env_mod.subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(AssertionError("no call"))
    )
    d2 = client.get("/api/env/tools").json()
    assert d2["tools"][0]["id"] == "t1"
    # refresh 强制重测
    monkeypatch.setattr(env_mod.subprocess, "run", _fake_check_run(payload.replace("t1", "t2"), 0))
    d3 = client.get("/api/env/tools", params={"refresh": True}).json()
    assert d3["tools"][0]["id"] == "t2"

    # 超时 → 504
    def trun(*a, **kw):
        raise subprocess.TimeoutExpired("cmd", 240)

    monkeypatch.setattr(env_mod.subprocess, "run", trun)
    assert client.get("/api/env/tools", params={"refresh": True}).status_code == 504


def test_install_tool_ids(monkeypatch):
    payload = json.dumps({"tools": [{"id": "a"}, {"id": "b"}, {"no": "id"}]})
    monkeypatch.setattr(env_mod.subprocess, "run", _fake_check_run(payload, 0))
    ids = env_mod._install_tool_ids()
    assert ids == frozenset({"a", "b"})
    # 缓存命中
    monkeypatch.setattr(
        env_mod.subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(AssertionError())
    )
    assert env_mod._install_tool_ids() == ids
    # 失败时返回缓存值
    monkeypatch.setattr(
        env_mod.subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(OSError())
    )
    env_mod._INSTALL_IDS_CACHE.update({"ts": 0.0, "ids": ids})
    assert env_mod._install_tool_ids() == ids


def test_env_install_job_flow(monkeypatch, client):
    monkeypatch.setattr(
        env_mod.subprocess,
        "run",
        _fake_check_run(json.dumps({"tools": [{"id": "ffmpeg"}]}), 0),
    )
    # 未知 id
    assert client.post("/api/env/install", json={"id": "nope"}).status_code == 400

    # 已知 id → 后台任务；Popen fake 输出进度 + JSON 结果
    class FakeProc:
        def __init__(self):
            self.stdout = None
            self.stderr = iter(["step 1", "", "step 2"])
            self._done = False

        def wait(self, timeout=None):
            return 0

    proc_holder = {}

    def fake_popen(cmd, **kw):
        p = FakeProc()
        # stdout 是 .read() 的流对象
        import io

        p.stdout = io.StringIO(json.dumps({"results": [{"id": "ffmpeg", "state": "ok"}]}))
        proc_holder["p"] = p
        return p

    monkeypatch.setattr(env_mod.subprocess, "Popen", fake_popen)
    r = client.post("/api/env/install", json={"id": "ffmpeg"})
    assert r.json()["state"] == "running"
    job_id = r.json()["jobId"]
    for _ in range(100):
        job = client.get(f"/api/env/job/{job_id}").json()
        if job["state"] != "running":
            break
        time.sleep(0.05)
    assert job["state"] == "ok"
    assert job["result"]["state"] == "ok"
    assert "step 1" in job["lines"] and "step 2" in job["lines"]
    assert client.get("/api/env/job/ghost").status_code == 404
    # 安装结束 → 体检缓存失效（ts 归零）
    assert env_mod._ENV_TOOLS_CACHE["ts"] == 0.0


def test_env_install_fail_flow(monkeypatch, client):
    monkeypatch.setattr(
        env_mod.subprocess, "run", _fake_check_run(json.dumps({"tools": [{"id": "x"}]}), 0)
    )

    def bad_popen(cmd, **kw):
        raise RuntimeError("spawn fail")

    monkeypatch.setattr(env_mod.subprocess, "Popen", bad_popen)
    r = client.post("/api/env/install", json={"id": "x"})
    job_id = r.json()["jobId"]
    for _ in range(100):
        job = client.get(f"/api/env/job/{job_id}").json()
        if job["state"] == "fail":
            break
        time.sleep(0.05)
    assert job["state"] == "fail" and "RuntimeError" in job["result"]["detail"]


# ---------- models ----------


def test_mask_key():
    assert models_mod._mask_key("") == ""
    assert models_mod._mask_key("short") == "«已配置»"
    assert models_mod._mask_key("a" * 20) == "«aaaaa…aaaa»"


def test_model_channels_rows(isolated_env_files):
    isolated_env_files.write_text(
        "OPENAI_BASE_URL=https://api.x.com/v1\n"
        "OPENAI_API_KEY=sk-abc\n"
        "OPENAI_MODEL=deepseek-chat\n"
        "ANTHROPIC_API_KEY=ak-1\n"
        "EASEL_LLM_BASE_URL=https://relay.x.com\n"
        "SILICONFLOW_API_KEY=sf-1\n",
        encoding="utf-8",
    )
    ch = models_mod._model_channels()
    rows = ch["channels"]["chat"]["rows"]
    assert [r["slot"] for r in rows] == ["openai", "anthropic", "relay"]
    assert rows[0]["role"] == "主" and rows[0]["result"] == "已配置"
    assert (
        rows[0]["keyMasked"] == "«sk-ab…k-abc»"
        if len("sk-abc") > 14
        else rows[0]["keyMasked"] == "«已配置»"
    )
    assert ch["channels"]["transcribe"]["rows"][0]["result"] == "优先"
    assert ch["channels"]["transcribe"]["rows"][1]["result"] == "已配置"
    assert ch["primary"] == "openai/deepseek-chat"
    # 注册表通道（image 等）也渲染了（model_registry 真实可用）
    assert "image" in ch["channels"] and ch["channels"]["image"]["rows"]
    # 空 env → primary 空、无 chat 行
    isolated_env_files.write_text("", encoding="utf-8")
    ch2 = models_mod._model_channels()
    assert ch2["channels"]["chat"]["rows"] == [] and ch2["primary"] == ""


def test_write_env_direct(isolated_env_files):
    isolated_env_files.write_text("# c\nFOO=1\n", encoding="utf-8")
    models_mod._write_env_direct({"FOO": "2", "BAR": "3"})
    t = isolated_env_files.read_text(encoding="utf-8")
    assert "FOO=2" in t and "BAR=3" in t
    models_mod._write_env_direct({})  # 空更新 no-op
    with pytest.raises(HTTPException):
        models_mod._write_env_direct({"BAD": "x\ny"})  # 注入


def test_models_save_chat(isolated_env_files, client):
    r = client.post(
        "/api/settings/models/save",
        json={
            "channel": "chat",
            "rows": [
                {
                    "slot": "openai",
                    "model": "m1",
                    "baseUrl": "https://b.x.com/v1/",
                    "key": "sk-new-1",
                }
            ],
        },
    )
    body = r.json()
    assert body["ok"] is True and body["channels"]["chat"]["rows"][0]["slot"] == "openai"
    t = isolated_env_files.read_text(encoding="utf-8")
    assert "OPENAI_MODEL=m1" in t and "OPENAI_BASE_URL=https://b.x.com/v1" in t

    # 校验分支
    assert (
        client.post(
            "/api/settings/models/save",
            json={"rows": [{"slot": "openai", "baseUrl": "ftp://x"}]},
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/settings/models/save",
            json={"rows": [{"slot": "openai", "key": "a b"}]},
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/settings/models/save",
            json={"rows": [{"slot": "openai", "key": "x" * 401}]},
        ).status_code
        == 400
    )
    assert (
        client.post("/api/settings/models/save", json={"rows": [{"slot": "openai"}]}).status_code
        == 400
    )  # 无改动
    # 换 base 不填 key（已存 key 存在）→ 400
    client.post(
        "/api/settings/models/save",
        json={"rows": [{"slot": "openai", "key": "sk-keep"}]},
    )
    r2 = client.post(
        "/api/settings/models/save",
        json={"rows": [{"slot": "openai", "baseUrl": "https://other.x.com"}]},
    )
    assert r2.status_code == 400 and "重新填写" in r2.json()["detail"]
    # relay slot 键位映射
    client.post(
        "/api/settings/models/save",
        json={"rows": [{"slot": "relay", "key": "rk", "model": "cm"}]},
    )
    t2 = isolated_env_files.read_text(encoding="utf-8")
    assert "EASEL_LLM_API_KEY=rk" in t2 and "CLAUDE_MODEL=cm" in t2
    # anthropic slot
    client.post(
        "/api/settings/models/save",
        json={"rows": [{"slot": "anthropic", "key": "ak", "baseUrl": "https://a.x.com"}]},
    )
    t3 = isolated_env_files.read_text(encoding="utf-8")
    assert "ANTHROPIC_API_KEY=ak" in t3


def test_models_save_media_channel(isolated_env_files, monkeypatch, client):
    # 未知供应商
    r = client.post(
        "/api/settings/models/save",
        json={"channel": "image", "rows": [{"slot": "ghost-provider", "key": "k"}]},
    )
    assert r.status_code == 400 and "不认识的服务商" in r.json()["detail"]
    # image 通道：IMG_API_KEY 必填 key + model + base
    r2 = client.post(
        "/api/settings/models/save",
        json={
            "channel": "image",
            "rows": [
                {
                    "slot": "openai",
                    "key": "sk-img",
                    "model": "gpt-image-1",
                    "baseUrl": "https://img.x.com/v1",
                    "primary": True,
                }
            ],
        },
    )
    assert r2.json()["ok"] is True
    t = isolated_env_files.read_text(encoding="utf-8")
    assert "IMG_API_KEY=sk-img" in t and "IMG_MODEL=gpt-image-1" in t
    # image 域无 provider 设置 env（仅 video/music/voice 有），primary 不落盘
    # 空 key/base/model → 无改动 400
    r3 = client.post(
        "/api/settings/models/save",
        json={"channel": "image", "rows": [{"slot": "openai", "name": "x"}]},
    )
    assert r3.status_code == 400 and "没有可保存的改动" in r3.json()["detail"]
    # key 空白字符
    r4 = client.post(
        "/api/settings/models/save",
        json={"channel": "image", "rows": [{"slot": "openai", "key": "a b"}]},
    )
    assert r4.status_code == 400


def _fake_httpx(payload, status=200):
    """httpx.get 替身：返回带 content/status_code 的响应对象。"""

    class Resp:
        status_code = status
        content = json.dumps(payload).encode()

    return lambda *a, **k: Resp()


def test_models_available(monkeypatch, client, isolated_env_files):
    # 无 base → 400
    assert client.post("/api/settings/models/available", json={"baseUrl": ""}).status_code == 400
    # base 非法 → 400
    assert (
        client.post("/api/settings/models/available", json={"baseUrl": "ftp://x"}).status_code
        == 400
    )
    # SSRF 拒绝
    monkeypatch.setattr(models_mod, "_ssrf_safe", lambda u: False)
    r = client.post(
        "/api/settings/models/available", json={"baseUrl": "https://pub.example", "key": "k"}
    )
    assert r.status_code == 400 and "内网" in r.json()["detail"]
    # 正常拉取（openai 形状）
    monkeypatch.setattr(models_mod, "_ssrf_safe", lambda u: True)
    monkeypatch.setattr(
        models_mod.httpx,
        "get",
        _fake_httpx({"data": [{"id": "m2"}, {"id": "m1"}, "junk", {"id": "m1"}]}),
    )
    r2 = client.post(
        "/api/settings/models/available", json={"baseUrl": "https://pub.example/v1", "key": "k"}
    ).json()
    assert r2["models"] == ["junk", "m1", "m2"] and r2["baseUrl"].endswith(
        "/v1"
    )  # 裸字符串项按 id 收录
    # anthropic 协议 + list 形状
    monkeypatch.setattr(models_mod.httpx, "get", _fake_httpx(["a1", "a2"]))
    r3 = client.post(
        "/api/settings/models/available",
        json={"baseUrl": "https://pub.example", "key": "k", "protocol": "anthropic"},
    ).json()
    assert r3["models"] == ["a1", "a2"]
    # slot 回落 key/base（草稿留空）
    isolated_env_files.write_text(
        "OPENAI_API_KEY=stored-key\nOPENAI_BASE_URL=https://stored.x.com\n", encoding="utf-8"
    )
    monkeypatch.setattr(models_mod.httpx, "get", _fake_httpx({"data": []}))
    r4 = client.post(
        "/api/settings/models/available", json={"slot": "openai", "baseUrl": ""}
    ).json()
    assert r4["baseUrl"] == "https://stored.x.com"

    # 拉取异常 → 502
    monkeypatch.setattr(
        models_mod.httpx, "get", lambda *a, **k: (_ for _ in ()).throw(OSError("net down"))
    )
    assert (
        client.post(
            "/api/settings/models/available", json={"baseUrl": "https://pub.example", "key": "k"}
        ).status_code
        == 502
    )


def test_models_selftest(monkeypatch, client, isolated_env_files):
    isolated_env_files.write_text(
        "OPENAI_BASE_URL=https://o.x.com/v1\nOPENAI_API_KEY=k1\nSILICONFLOW_API_KEY=sf\n",
        encoding="utf-8",
    )
    # SSRF 拒绝路径（不发请求）
    monkeypatch.setattr(models_mod, "_ssrf_safe", lambda u: False)
    r = client.post("/api/settings/models/selftest", json={"channel": "all"}).json()
    assert all(res["ok"] is False and "内网" in res["detail"] for res in r["results"])
    # 正常探测 200
    monkeypatch.setattr(models_mod, "_ssrf_safe", lambda u: True)
    monkeypatch.setattr(models_mod.httpx, "get", _fake_httpx({}, status=200))
    r2 = client.post("/api/settings/models/selftest", json={"channel": "all"}).json()
    assert r2["channel"] == "all"
    assert any(res["ok"] for res in r2["results"])  # openai + siliconflow 均 200
    assert any(res["baseUrl"].endswith("o.x.com/v1") for res in r2["results"])
    # 仅 transcribe 通道
    r3 = client.post("/api/settings/models/selftest", json={"channel": "transcribe"}).json()
    assert len(r3["results"]) == 1 and "siliconflow" in r3["results"][0]["baseUrl"]

    # 请求异常 → ok False + detail
    monkeypatch.setattr(
        models_mod.httpx, "get", lambda *a, **k: (_ for _ in ()).throw(OSError("net down"))
    )
    r4 = client.post("/api/settings/models/selftest", json={"channel": "transcribe"}).json()
    assert r4["results"][0]["ok"] is False and "OSError" in r4["results"][0]["detail"]
    # settings/models 展示路由
    assert client.get("/api/settings/models").json()["channels"]["transcribe"]["rows"]
