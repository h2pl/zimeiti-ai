"""autonomous-guardrails 端到端探针：真实服务上验证四项护栏。

不消耗真实 token（用注入的假入口）：
1. 重试：可重试异常按次重试后仍失败，记录 retries
2. blocked：需人工确认的动作标 blocked 且流程继续（不阻塞）
3. 预算：超上限拦截 / 无单价放行
4. /api/autonomous/status 可查（熔断态 + 预算）
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
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "api"))
    from zimeiti_autonomous import guardrails as gr
    from zimeiti_autonomous import runner as rn

    tmp = Path(tempfile.mkdtemp())

    # 1) 重试
    calls = {"n": 0}

    def flaky(sk: str, msg: str) -> str:
        calls["n"] += 1
        raise ConnectionError("一直抖")

    rn.set_agent_entry(flaky)
    res = rn.run_flow(flow_id="p-retry", name="重试", steps=["discover"],
                      config={"guardrails": True, "retry": 2}, archive_root=tmp)
    check("重试至上限后失败", res["status"] == "failed" and res["steps"][0]["retries"] == 2
          and calls["n"] == 3, f"calls={calls['n']} retries={res['steps'][0].get('retries')}")

    # 2) blocked 不阻塞
    def need_confirm(sk: str, msg: str) -> str:
        return "需要人工确认后发布（pending）" if "produce" in sk else "产出"

    rn.set_agent_entry(need_confirm)
    res2 = rn.run_flow(flow_id="p-block", name="阻塞", steps=["produce", "review"],
                       config={"guardrails": True}, archive_root=tmp)
    blocked = [s for s in res2["steps"] if s["status"] == "blocked"]
    check("需确认动作标 blocked 且继续", res2["status"] == "done" and len(blocked) == 1
          and [s["step"] for s in res2["steps"]] == ["produce", "review"])

    # 3) 预算护栏
    guard = gr.BudgetGuard(daily_limit_usd=1.0)
    check("超预算拦截 / 无单价放行", guard.check(1.5) is False and guard.check(0.5) is True
          and guard.check(None) is True)
    rn.set_agent_entry(None)

    # 4) 状态端点
    try:
        st = api("GET", "/api/autonomous/status")
        ok = "circuit" in st and "budget" in st
        check("/api/autonomous/status 可查", ok, str(st)[:120])
    except Exception as e:  # noqa: BLE001
        check("/api/autonomous/status 可查", False, str(e)[:120])

    print(f"\n小结: {'PASS' if not FAILS else 'FAIL ' + ','.join(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
