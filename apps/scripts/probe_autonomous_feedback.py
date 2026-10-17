"""autonomous-feedback 端到端探针：真实服务上验证数据回流闭环。

造一份 outputs/_analytics 样本 → 跑流程 → 断言 discover 步含校准段、produce 步不含；
再验证无数据时如实降级 + /api/feedback 可查。不消耗真实 token。
"""

from __future__ import annotations

import json
import shutil
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
    from zimeiti_autonomous import feedback as fb
    from zimeiti_autonomous import runner as rn

    tmp = Path(tempfile.mkdtemp())
    analytics = tmp / "_analytics"
    (analytics / "wechat").mkdir(parents=True)
    (analytics / "wechat" / "2026-10-18.json").write_text(
        json.dumps([
            {"media_id": "m1", "title": "选题 A"},
            {"media_id": "m2", "title": "选题 B"},
        ], ensure_ascii=False),
        encoding="utf-8",
    )
    # 坏 JSON：验证容错
    (analytics / "wechat" / "2026-10-17.json").write_text("{ bad", encoding="utf-8")

    orig_a, orig_f = fb._ANALYTICS_DIR, fb._FEEDBACK_DIR
    fb._ANALYTICS_DIR, fb._FEEDBACK_DIR = analytics, tmp / "_feedback"
    try:
        # 1) 汇总容错
        items = fb.collect_published(days=14)
        check("汇总跳过坏文件", len(items) == 2, f"items={len(items)}")

        # 2) discover 注入 / produce 不注入
        seen: dict[str, str] = {}

        def entry(sk: str, msg: str) -> str:
            seen[sk.split("-")[-1]] = msg
            return "产出"

        rn.set_agent_entry(entry)
        res = rn.run_flow(
            flow_id="probe-fb", name="回流", steps=["discover", "produce"],
            config={}, archive_root=tmp,
        )
        check("流程跑通", res["status"] == "done")
        check("discover 含校准段", "wechat" in seen.get("discover", ""),
              seen.get("discover", "")[-60:])
        check("produce 不含校准段", "wechat" not in seen.get("produce", ""))
        check("归档落盘", len(list((tmp / "_feedback").glob("*.md"))) == 1)

        # 3) 无数据降级
        fb._ANALYTICS_DIR = tmp / "nope"
        rn.set_agent_entry(lambda sk, msg: "产出")
        seen2: dict[str, str] = {}
        rn.set_agent_entry(lambda sk, msg: (seen2.__setitem__("discover", msg), "产出")[1])
        rn.run_flow(flow_id="probe-empty", name="空", steps=["discover"],
                    config={}, archive_root=tmp)
        check("无数据如实降级", "暂无发布记录" in seen2.get("discover", ""))
        rn.set_agent_entry(None)
    finally:
        fb._ANALYTICS_DIR, fb._FEEDBACK_DIR = orig_a, orig_f
        shutil.rmtree(tmp, ignore_errors=True)

    # 4) /api/feedback
    try:
        r = api("GET", "/api/feedback")
        check("/api/feedback 可查", "calibration" in r and "has_facts" in r, str(r)[:80])
    except Exception as e:  # noqa: BLE001
        check("/api/feedback 可查", False, str(e)[:120])

    print(f"\n小结: {'PASS' if not FAILS else 'FAIL ' + ','.join(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
