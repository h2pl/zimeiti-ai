"""autonomous-flow 端到端探针：真实服务上跑一条完整运营流程。

用假 agent 入口（注入 runner）验证编排骨架：步骤串行、上一步摘要注入、产出归档、
失败即停、/api/flows 端点可用。不消耗真实 token。
"""

from __future__ import annotations

import json
import sys
import tempfile
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8121"
FAILS: list[str] = []


def check(name: str, ok: bool, extra: str = "") -> None:
    print(f"{'[PASS]' if ok else '[FAIL]'} {name}{(' — ' + extra) if extra else ''}")
    if not ok:
        FAILS.append(name)


def api(method: str, path: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{BASE}{path}", data=data, method=method,
        headers={"Content-Type": "application/json", "Origin": BASE},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def main() -> int:
    # 1) 步骤目录端点
    try:
        cat = api("GET", "/api/flows/steps/catalog")
        check("步骤目录端点", len(cat.get("steps", [])) == 5, str(cat.get("steps"))[:60])
    except Exception as e:  # noqa: BLE001
        check("步骤目录端点", False, str(e)[:120])
        return 1

    # 2) 建流程（三步链路）
    try:
        created = api("POST", "/api/flows", {
            "name": "探针流程", "steps": ["discover", "plan", "review"],
            "schedule": "08:00", "config": {"topic": "AI 热点", "draft_only": True},
        })
        fid = created.get("id", "")
        check("创建流程", bool(fid), fid)
    except Exception as e:  # noqa: BLE001
        check("创建流程", False, str(e)[:120])
        return 1

    # 3) 逐步执行（注入假入口，验证摘要链与归档）
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "api"))
    from zimeiti_autonomous import runner as rn

    with tempfile.TemporaryDirectory() as td:
        seen: list[str] = []

        def fake(sk: str, msg: str) -> str:
            seen.append(msg)
            return f"第{len(seen)}步产出"

        rn.set_agent_entry(fake)
        res = rn.run_flow(
            flow_id="probe-flow", name="探针", steps=["discover", "plan", "review"],
            config={"topic": "AI 热点"}, archive_root=Path(td),
        )
        check("三步全部完成", res["status"] == "done" and len(res["steps"]) == 3)
        check("上一步摘要注入下一步", "第1步产出" in seen[1] and "第2步产出" in seen[2])
        archived = sorted(p.name for p in (Path(td) / "probe-flow").iterdir())
        check("逐步产出归档", archived == ["01-discover.md", "02-plan.md", "03-review.md"], str(archived))

        # 4) 失败即停
        calls = {"n": 0}

        def boom(sk: str, msg: str) -> str:
            calls["n"] += 1
            if calls["n"] == 2:
                raise RuntimeError("第二步炸了")
            return "ok"

        rn.set_agent_entry(boom)
        res2 = rn.run_flow(
            flow_id="probe-fail", name="失败", steps=["discover", "plan", "review"],
            config={}, archive_root=Path(td),
        )
        check("失败即停", res2["status"] == "failed" and res2["failed_step"] == "plan"
              and calls["n"] == 2, f"calls={calls['n']}")
        rn.set_agent_entry(None)

    # 5) 清理
    try:
        api("DELETE", f"/api/flows/{fid}")
        check("清理流程", True)
    except Exception as e:  # noqa: BLE001
        check("清理流程", False, str(e)[:100])

    print(f"\n小结: {'PASS' if not FAILS else 'FAIL ' + ','.join(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
