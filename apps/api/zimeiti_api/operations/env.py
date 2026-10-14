"""环境面板（operations）：.env 保存/工具安装/任务进度。"""
from __future__ import annotations

import asyncio
import json
import re
import subprocess
import sys
import threading
import time
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..core.paths import ENV_FILE, PROJECT_ROOT, SHARED_SCRIPTS
from ..core.settings import (_ENV_ALLOWLIST, _guard_env_values, _is_set, _key_configured,
                             _mask, _read_env, _skill_api_configured, _write_env,
                             SKILL_API_REQUIREMENTS)

router = APIRouter()

class EnvUpdateRequest(BaseModel):
    updates: dict[str, str]


@router.post("/api/env")
async def api_env_save(req: EnvUpdateRequest):
    """写 API key 到项目根 .env（仅允许注册表内 env 名）。返回更新后各 skill 的配置状态。"""
    bad = [k for k in (req.updates or {}) if k not in _ENV_ALLOWLIST]
    if bad:
        raise HTTPException(400, f"不允许写入的变量：{', '.join(bad)}")
    _write_env(req.updates or {})
    env = _read_env()
    return {
        "ok": True,
        "skills": {s: _skill_api_configured(s, env) for s in SKILL_API_REQUIREMENTS},
    }


# ═══════════════════════════════════════════════════════════════════════
# 设置面板 · 环境安装（skills/shared/scripts/install_tool.py 引擎桥）
# 体检走引擎 check --json；安装后台跑、前端轮询 /api/env/job/{id}。
# ═══════════════════════════════════════════════════════════════════════

INSTALL_TOOL = SHARED_SCRIPTS / "install_tool.py"
_ENV_TOOLS_CACHE: dict = {"ts": 0.0, "data": None}
_ENV_JOBS: dict[str, dict] = {}


@router.get("/api/env/tools")
async def api_env_tools(refresh: bool = False):
    """环境体检：引擎 check --json（15 秒缓存；refresh=1 强制重测）。"""
    if not refresh and _ENV_TOOLS_CACHE["data"] and time.time() - _ENV_TOOLS_CACHE["ts"] < 15:
        return _ENV_TOOLS_CACHE["data"]
    try:
        proc = await asyncio.to_thread(lambda: subprocess.run(
            [sys.executable, str(INSTALL_TOOL), "--json", "check"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=240, cwd=str(PROJECT_ROOT)))
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "环境体检超时，请稍后再试")
    if proc.returncode != 0 or not (proc.stdout or "").strip():
        raise HTTPException(500, f"环境体检失败：{(proc.stderr or '').strip()[-300:] or '无输出'}")
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise HTTPException(500, f"体检输出解析失败：{e}")
    data["cachedAt"] = int(time.time())
    _ENV_TOOLS_CACHE.update({"ts": time.time(), "data": data})
    return data


class EnvInstallRequest(BaseModel):
    id: str


_INSTALL_IDS_CACHE: dict = {"ts": 0.0, "ids": frozenset()}


def _install_tool_ids() -> frozenset[str]:
    """引擎里真实存在的配方 id（缓存 5 分钟）。安装接口只认这张表里的 id——
    只按正则放行的话，`--help` 这类带横线的串会被 argparse 当选项吃掉。"""
    if _INSTALL_IDS_CACHE["ids"] and time.time() - _INSTALL_IDS_CACHE["ts"] < 300:
        return _INSTALL_IDS_CACHE["ids"]
    try:
        p = subprocess.run([sys.executable, str(INSTALL_TOOL), "--json", "list"],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=30, cwd=str(PROJECT_ROOT))
        ids = frozenset(t["id"] for t in (json.loads(p.stdout).get("tools") or []) if t.get("id"))
    except Exception:  # noqa: BLE001
        return _INSTALL_IDS_CACHE["ids"]
    if ids:
        _INSTALL_IDS_CACHE.update({"ts": time.time(), "ids": ids})
    return ids


@router.post("/api/env/install")
async def api_env_install(req: EnvInstallRequest):
    """后台安装（引擎 install）：立即返回 jobId，前端轮询进度。"""
    tid = (req.id or "").strip()
    known = await asyncio.to_thread(_install_tool_ids)
    if tid not in known:
        raise HTTPException(400, f"无效的工具 id：{tid[:40]!r}")
    job_id = uuid.uuid4().hex[:16]
    if len(_ENV_JOBS) >= 200:                   # 任务表不能无限长：清掉最老的已结束任务
        for k, _ in sorted((kv for kv in _ENV_JOBS.items() if kv[1].get("ended")),
                           key=lambda kv: kv[1]["ended"])[:100]:
            _ENV_JOBS.pop(k, None)
    job = {"jobId": job_id, "id": tid, "state": "running", "lines": [],
           "result": None, "started": int(time.time()), "ended": None}
    _ENV_JOBS[job_id] = job

    def _run() -> None:
        proc = None
        try:
            proc = subprocess.Popen(
                [sys.executable, str(INSTALL_TOOL), "--json", "install", tid],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", errors="replace", cwd=str(PROJECT_ROOT))
            # stdout 必须**并发**抽干：串行地先读完 stderr 再读 stdout，子进程一旦往 stdout
            # 写满管道缓冲（64K）就会阻塞，而我们还堵在 stderr 上——双向死锁。
            _out: list[str] = []
            t_out = threading.Thread(target=lambda: _out.append(proc.stdout.read() or ""), daemon=True)
            t_out.start()
            for line in proc.stderr:            # 引擎进度日志走 stderr
                line = line.rstrip()
                if line:
                    job["lines"] = (job["lines"] + [line])[-40:]   # 只留最近 40 行（换列表，避免读端正在序列化时被就地改）
            try:
                proc.wait(timeout=3600)
            except subprocess.TimeoutExpired:   # 卡死的安装进程必须真的杀掉，否则线程与子进程永久泄漏
                proc.kill()
                proc.wait(timeout=30)
                raise
            t_out.join(timeout=30)
            out = ("".join(_out)).strip()
            if out:
                job["result"] = (json.loads(out).get("results") or [None])[0]
            job["state"] = "ok" if (job["result"] or {}).get("state") == "ok" else "fail"
        except Exception as e:  # noqa: BLE001
            job["state"] = "fail"
            job["result"] = {"id": tid, "state": "fail", "detail": f"{type(e).__name__}: {e}"}
        finally:
            job["ended"] = int(time.time())
            _ENV_TOOLS_CACHE["ts"] = 0.0        # 装完让下一次体检不吃旧缓存

    threading.Thread(target=_run, daemon=True).start()
    return {"jobId": job_id, "id": tid, "state": "running"}


@router.get("/api/env/job/{job_id}")
async def api_env_job(job_id: str):
    """查安装进度：running / ok / fail + 最近日志行 + 最终结果。"""
    job = _ENV_JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "任务不存在（服务可能重启过）")
    return job
