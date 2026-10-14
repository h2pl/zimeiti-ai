"""pg-data-layer 运行时验收脚本（Comet Native Runtime checks 用）。

自包含：自己起/停服务实例（127.0.0.1:8055，不占用开发用的 :8000），
不依赖外部已运行进程。三个模式对应此前被 blocked/需运行时证据的验收项：

    restart   A1（重启后会话上下文恢复）+ A2 数据级（pending 跨重启存活）+ A6（fail-fast）
    e2e       A3/A8（与 Easel 上游双服务 E2E 对比；自起两边服务于 8055/8056）

用法（必须用 apps/api 的 venv——依赖 psycopg）：
    apps/api/.venv/Scripts/python.exe apps/scripts/verify_pg_data_layer.py restart
    apps/api/.venv/Scripts/python.exe apps/scripts/verify_pg_data_layer.py e2e

退出码 0=通过，1=有验收项失败。所有判定打印证据（状态码/响应片段/退出码）。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]   # 仓库根（zimeiti-ai）
APPS = REPO / "apps"
API_DIR = APPS / "api"
VENV_PY = API_DIR / ".venv" / "Scripts" / "python.exe"
EASEL_DIR = Path(os.environ.get("EASEL_DIR", str(REPO.parent / "Easel")))
PORT = 8055
EASEL_PORT = 8056
BASE = f"http://127.0.0.1:{PORT}"
EASEL_BASE = f"http://127.0.0.1:{EASEL_PORT}"

PASS, FAIL = "PASS", "FAIL"
results: list[tuple[str, str, str]] = []   # (项, 结论, 证据)


def _record(item: str, ok: bool, evidence: str) -> None:
    results.append((item, PASS if ok else FAIL, evidence))
    print(f"[{PASS if ok else FAIL}] {item}: {evidence}", flush=True)


def _spawn(args: list[str], cwd: Path, env_extra: dict | None = None) -> subprocess.Popen:
    env = os.environ.copy()
    env.update(env_extra or {})
    return subprocess.Popen(args, cwd=str(cwd), env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def _wait_ready(url: str, timeout: float = 40) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url + "/api/status", timeout=3) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(1)
    return False


def _kill(proc: subprocess.Popen) -> None:
    if proc.poll() is None:
        proc.kill()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                       capture_output=True)


def _chat(message: str, session_id: str, base: str = BASE, timeout: float = 180) -> str:
    req = urllib.request.Request(
        base + "/api/chat",
        data=json.dumps({"message": message, "sessionId": session_id}).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read()).get("response", "")


def _start_server(env_extra: dict | None = None) -> subprocess.Popen:
    proc = _spawn([str(VENV_PY), "serve.py", "--host", "127.0.0.1", "--port", str(PORT)],
                  API_DIR, env_extra)
    if not _wait_ready(BASE):
        _kill(proc)
        raise RuntimeError("服务 40s 内未就绪")
    return proc


def _pg_run(stmt: str) -> tuple[int, str]:
    """在独立子进程里执行一条 zimeiti_api.core.pg 语句（证明跨进程持久性）。"""
    code = f"import sys; sys.path.insert(0, {str(API_DIR)!r}); from zimeiti_api.core import pg; {stmt}"
    proc = subprocess.run([str(VENV_PY), "-c", code], capture_output=True, text=True, timeout=60)
    return proc.returncode, (proc.stdout or "").strip()


def check_restart() -> None:
    """A1 + A2（数据级）+ A6。"""
    sid = f"verify-{uuid.uuid4().hex[:8]}"
    secret = f"青龙{uuid.uuid4().hex[:6]}"

    # ---- A1：两轮对话跨重启 ----
    proc = _start_server()
    try:
        r1 = _chat(f"记住一个暗号：{secret}。请确认。", sid)
        _record("A1.1 首轮对话", bool(r1), f"session={sid} 回复长度={len(r1)}")
    finally:
        _kill(proc)
    proc = _start_server()
    try:
        r2 = _chat("刚才的暗号是什么？", sid)
        ok = secret in r2
        _record("A1.2 重启后回忆暗号", ok,
                f"暗号{'命中' if ok else '未命中'}（回复: {r2[:60]!r}）")
    finally:
        _kill(proc)

    # ---- A2（数据级）：pending 跨重启存活（写/读都在独立子进程） ----
    qid = uuid.uuid4().hex
    code, _ = _pg_run(f"pg.pending_set({qid!r}, {sid!r}, {{'id': {qid!r}, 'thread_id': {sid!r}, 'created_at': __import__('time').time()}})")
    alive_after_restart = False
    if code == 0:
        proc = _start_server()   # 重启即重新读 PG
        try:
            code2, out = _pg_run(f"print(pg.pending_get({qid!r}))")
            alive_after_restart = code2 == 0 and out.strip() not in ("", "None")
        finally:
            _kill(proc)
    _record("A2 pending 跨重启存活", alive_after_restart,
            f"写入 qid={qid[:8]}，重启后 pending_get={'有' if alive_after_restart else '无'}")
    _pg_run(f"pg.pending_del({qid!r})")

    # ---- A6：坏 DATABASE_URL → fail-fast ----
    bad = "postgresql://zimeiti:zimeiti_dev@localhost:5432/__no_such_db__"
    proc = _spawn([str(VENV_PY), "serve.py", "--host", "127.0.0.1", "--port", str(PORT + 20)],
                  API_DIR, {"DATABASE_URL": bad})
    try:
        out, _ = proc.communicate(timeout=90)
    except subprocess.TimeoutExpired:
        _kill(proc)
        out = ""
    ok = proc.returncode not in (0, None) and "fail-fast" in out and "排查" in out
    _record("A6 缺库 fail-fast", ok,
            f"退出码={proc.returncode}，输出含 fail-fast+排查指引={'fail-fast' in out and '排查' in out}")

    # ---- 清理测试会话数据 ----
    _pg_run(f"pg.session_delete({sid!r}); pg.pending_delete_by_session({sid!r})")


def check_e2e() -> None:
    """A3/A8：自起 zimeiti(8055)+Easel(8056)，跑 e2e_parity_check --writes。"""
    z = _spawn([str(VENV_PY), "serve.py", "--host", "127.0.0.1", "--port", str(PORT)], API_DIR)
    e = _spawn([str(EASEL_DIR / ".venv" / "Scripts" / "python.exe"), "web/app.py"],
               EASEL_DIR, {"EASEL_PORT": str(EASEL_PORT), "PYTHONUTF8": "1"})
    try:
        if not _wait_ready(BASE):
            _record("e2e.0 双服务就绪", False, "zimeiti 未就绪")
            return
        if not _wait_ready(EASEL_BASE):
            _record("e2e.0 双服务就绪", False, "easel 未就绪")
            return
        _record("e2e.0 双服务就绪", True, f"zimeiti={BASE} easel={EASEL_BASE}")
        proc = subprocess.run(
            [sys.executable, str(APPS / "scripts" / "e2e_parity_check.py"),
             "--zimeiti", BASE, "--easel", EASEL_BASE, "--writes"],
            capture_output=True, text=True, timeout=900)
        out = (proc.stdout or "") + (proc.stderr or "")
        ok = proc.returncode == 0 and "全部一致" in out
        tail = [ln for ln in out.splitlines() if "全部一致" in ln or "不一致" in ln]
        _record("A3/A8 e2e 对比", ok, f"exit={proc.returncode}；{'；'.join(tail)[:120]}")
    finally:
        _kill(z)
        _kill(e)


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "restart"
    print(f"== pg-data-layer 运行时验收（mode={mode}）==", flush=True)
    if mode == "restart":
        check_restart()
    elif mode == "e2e":
        check_e2e()
    else:
        print(f"未知模式: {mode}（restart|e2e）", file=sys.stderr)
        return 2
    failed = [r for r in results if r[1] == FAIL]
    print(f"\n小结: {len(results) - len(failed)}/{len(results)} 通过")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
