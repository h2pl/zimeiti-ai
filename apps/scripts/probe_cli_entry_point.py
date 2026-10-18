"""cli-entry-point 端到端探针：真实服务 + 真实 CLI 进程（子进程方式）。

覆盖：--help 可发现性 / 连接失败行动指引（退出码 1）/ flows 列表-新建-删除 /
runs 空态 / usage。**不跑 chat 与 flows run**（会真实消耗模型额度）。
"""

from __future__ import annotations

import os
import subprocess
import sys
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8121"
API_DIR = Path(__file__).resolve().parent.parent / "api"
FAILS: list[str] = []


def check(name: str, ok: bool, extra: str = "") -> None:
    print(f"{'[PASS]' if ok else '[FAIL]'} {name}{(' — ' + extra) if extra else ''}")
    if not ok:
        FAILS.append(name)


def run_cli(*args: str, env_extra: dict | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONUTF8="1")
    env.pop("UV_PYTHON", None)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, "-m", "zimeiti_cli.cli", *args],
        capture_output=True, text=True, timeout=120, cwd=str(API_DIR), env=env,
    )


def api(method: str, path: str, body: dict | None = None) -> dict:
    import json

    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{BASE}{path}", data=data, method=method,
        headers={"Content-Type": "application/json", "Origin": BASE},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def main() -> int:
    # 1) 可发现性：--help 列出全部子命令
    r = run_cli("--help")
    ok = r.returncode == 0 and all(k in r.stdout for k in ("chat", "flows", "runs", "usage"))
    check("--help 列出子命令", ok, r.stdout.replace("\n", " ")[:90])

    # 2) 连接失败 → 退出码 1 + 行动指引
    r2 = run_cli("usage", env_extra={"ZIMEITI_API": "http://127.0.0.1:9"})
    check("连接失败退出码 1 + 指引",
          r2.returncode == 1 and "无法连接" in (r2.stderr + r2.stdout) and "make api" in (r2.stderr + r2.stdout),
          (r2.stderr or r2.stdout)[:80])

    # 3) flows 新建 → 列表可见 → 删除
    try:
        for f in api("GET", "/api/flows").get("flows", []):
            api("DELETE", f"/api/flows/{f['id']}")
    except Exception:
        pass
    r3 = run_cli("flows", "new", "--name", "探针流程", "--steps", "discover,plan",
                 "--schedule", "09:00", env_extra={"ZIMEITI_API": BASE})
    fid = ""
    if r3.returncode == 0 and "已创建：" in r3.stdout:
        fid = r3.stdout.split("已创建：")[1].split("（")[0].strip()
    check("flows new 创建并回显 id", bool(fid), r3.stdout.strip()[:60])

    r4 = run_cli("flows", env_extra={"ZIMEITI_API": BASE})
    check("flows 列表含中文步骤徽标",
          r4.returncode == 0 and "探针流程" in r4.stdout and "发现" in r4.stdout and "选题" in r4.stdout,
          r4.stdout.strip()[:70])

    r5 = run_cli("runs", env_extra={"ZIMEITI_API": BASE})
    check("runs 空态不炸", r5.returncode == 0, r5.stdout.strip()[:50])

    r6 = run_cli("usage", env_extra={"ZIMEITI_API": BASE})
    check("usage 可读", r6.returncode == 0 and "tokens" in r6.stdout, r6.stdout.strip()[:60])

    if fid:
        api("DELETE", f"/api/flows/{fid}")
        check("清理探针流程", True)

    print(f"\n小结: {'PASS' if not FAILS else 'FAIL ' + ','.join(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
