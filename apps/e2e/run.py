"""browser-e2e 套件入口。

用法（在 apps/api venv 下）：
    uv run python ../e2e/run.py                    # 双端全量
    uv run python ../e2e/run.py --scenarios S3,S5  # 按场景
    uv run python ../e2e/run.py --target zimeiti   # 单端调试

退出码：0=全部 PASS 且双端差异 0；1=存在 FAIL 或 DIFF。
"""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from coverage_map import COVERAGE_MAP
from mock_llm import MockLLMServer
from parity import compare
from runner import Target

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail and not ok else ""))


SCENARIO_IDS = [f"S{i:02d}" for i in range(1, 14)]


def load_scenarios(ids: list[str]):
    """按目录文件名映射场景 ID：S3 → scenarios/s03_ideas_crud。"""
    available: dict[str, str] = {}
    for f in sorted((Path(__file__).resolve().parent / "scenarios").glob("s[0-9][0-9]_*.py")):
        available[f"S{f.name[1:3]}"] = f"scenarios.{f.stem}"
    mods = []
    for sid in ids:
        if sid not in available:
            raise SystemExit(f"未知场景 {sid}；可用: {sorted(available)}")
        mods.append((sid, importlib.import_module(available[sid])))
    return mods


def run_target(target_name: str, mods) -> dict:
    from playwright.sync_api import sync_playwright

    tgt = Target(target_name)
    if tgt.port_busy():
        print(f"[SKIP] {target_name} 端口已占用（{tgt.base}）——先释放再跑")
        return {"_skipped": True}
    mock = MockLLMServer()
    obs: dict = {}
    print(f"\n===== 目标端: {target_name} ({tgt.base}) =====")
    try:
        mock.start()
        base = tgt.start()
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            ctx_pg = browser.new_context(viewport={"width": 1440, "height": 900})
            page = ctx_pg.new_page()
            js_errors: list[str] = []
            page.on("pageerror", lambda e: js_errors.append(str(e)[:150]))
            page.on("dialog", lambda d: d.accept())  # 会话删除 confirm 等
            from scenarios.base import Ctx

            ctx = Ctx(base, target_name)
            for sid, mod in mods:
                print(f"--- {sid} {getattr(mod, 'TITLE', sid)} ---")
                try:
                    obs[sid] = mod.run(page, ctx, check)
                except Exception as e:  # 场景崩溃 = FAIL，继续其余场景
                    obs[sid] = {"_crashed": str(e)[:150]}
                    check(f"[{target_name}] {sid} 场景崩溃", False, str(e)[:150])
            obs["js_errors_total"] = len(js_errors)
            obs["js_error_samples"] = js_errors[:2]
            browser.close()
    finally:
        tgt.stop()
        mock.stop()
    return obs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenarios", default=",".join(SCENARIO_IDS))
    ap.add_argument("--target", choices=["zimeiti", "easel", "both"], default="both")
    args = ap.parse_args()
    ids = [s.strip().upper() for s in args.scenarios.split(",") if s.strip()]
    mods = load_scenarios(ids)

    targets = ["zimeiti", "easel"] if args.target == "both" else [args.target]
    obs_by: dict[str, dict] = {}
    for t in targets:
        obs_by[t] = run_target(t, mods)

    diffs: list[str] = []
    notes: list[str] = []
    if len(obs_by) == 2 and not any(o.get("_skipped") for o in obs_by.values()):
        print("\n===== 双端对齐比较 =====")
        diffs, notes = compare(obs_by["zimeiti"], obs_by["easel"])
        for d in diffs:
            print(f"  [DIFF] {d}")
        for n in notes:
            print(f"  [NOTE] {n}")
        if not diffs:
            print("  结构级观测值完全一致")

    print("\n===== API 路径 → 浏览器场景覆盖映射 =====")
    for path, scene in COVERAGE_MAP.items():
        print(f"  {path}  →  {scene}")

    failed = [r for r in RESULTS if not r[1]]
    print(f"\n小结: {len(RESULTS) - len(failed)}/{len(RESULTS)} 通过 | 双端差异 {len(diffs)} 项 | NOTE {len(notes)} 项")
    for name, _ok, detail in failed:
        print(f"  FAIL: {name} {detail}")
    return 0 if (not failed and not diffs) else 1


if __name__ == "__main__":
    sys.exit(main())
