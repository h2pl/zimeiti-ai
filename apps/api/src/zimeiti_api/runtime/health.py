"""账号健康巡检与晨报（P0⑦）。

参考: xiaobei crews/main/HEARTBEAT.md 的凌晨巡检闭环——每平台探活，
失效平台停用并汇总上报（「跳过+记录+白天请人工重登」，绝不自动造会话）。

探活分级（两级，参考 login-manager 两层探活，按成本从低到高）：
- xhs-main：登录态文件存在且含 web_session cookie（Tier1 cookie 关键字段）
- gzh-main：凭证密文可解密且 app_id 非空（Tier1）
晨报：巡检结果 + 当日各任务运行摘要，经 notify 推送（未配置 webhook 仅落审计）。
"""

import json
from datetime import datetime
from typing import Any

from zimeiti_api.core import audit, notify
from zimeiti_api.governance import platform_state


def check_xhs() -> dict[str, Any]:
    """xhs 登录态 Tier1 探活：storage_state 存在且含 web_session cookie。"""
    from pathlib import Path

    from zimeiti_api.config import LOGIN_STATE_PATH

    f = Path(LOGIN_STATE_PATH)
    if not f.exists():
        return {"ok": False, "detail": f"登录态文件不存在：{f}"}
    try:
        state = json.loads(f.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        return {"ok": False, "detail": f"登录态文件损坏：{exc}"}
    cookies = state.get("cookies") or []
    if any(c.get("name") == "web_session" for c in cookies):
        return {"ok": True, "detail": "web_session cookie 存在"}
    return {"ok": False, "detail": "登录态中无 web_session cookie（需重新扫码）"}


def check_gzh() -> dict[str, Any]:
    """gzh 凭证 Tier1 探活：密文可解密且 app_id 非空（不调用外部 API）。"""
    from zimeiti_api.core.credentials import load_account_credentials

    try:
        creds = load_account_credentials("gzh-main")
    except Exception as exc:  # noqa: BLE001 - 解密失败/文件缺失都算不健康
        return {"ok": False, "detail": f"凭证不可用：{exc}"}
    if creds.get("app_id"):
        return {"ok": True, "detail": "凭证密文可解密"}
    return {"ok": False, "detail": "凭证缺 app_id"}


CHECKERS = {"xhs-main": check_xhs, "gzh-main": check_gzh}


def run_health_check() -> dict[str, Any]:
    """巡检全部账号：失效 → 停用平台 + 通知（对齐 xiaobei「跳过+上报」纪律）。"""
    report: dict[str, Any] = {"ts": datetime.now().isoformat(timespec="seconds"), "accounts": {}}
    for account, checker in CHECKERS.items():
        result = checker()
        report["accounts"][account] = result
        if not result["ok"]:
            platform_state.set_enabled(account, False, f"健康巡检：{result['detail']}")
            notify.send(
                "login_wall",
                f"[晨检] {account} 登录态不健康：{result['detail']}"
                "——已停用该平台，请人工重登后恢复",
            )
    audit.record(
        "health_checked",
        **{
            "ok": [a for a, r in report["accounts"].items() if r["ok"]],
            "bad": [a for a, r in report["accounts"].items() if not r["ok"]],
        },
    )
    return report


def build_morning_digest(health: dict, job_results: dict[str, Any]) -> str:
    """晨报文案：巡检结果 + 各任务摘要（成功/跳过/失败数 + 失效平台清单）。"""
    bad = [a for a, r in health.get("accounts", {}).items() if not r["ok"]]
    lines = ["[晨报]"]
    lines.append(
        "登录态：" + ("全部健康" if not bad else f"失效 {','.join(bad)}（已停用，请人工重登）")
    )
    for job, res in job_results.items():
        if "runs" in res:
            ok = sum(1 for r in res["runs"] if r.get("interrupted"))
            skipped = sum(1 for r in res["runs"] if "skipped" in r)
            failed = sum(1 for r in res["runs"] if "error" in r)
            lines.append(f"{job}: 成功{ok} 跳过{skipped} 失败{failed}")
        elif "error" in res:
            lines.append(f"{job}: 失败（{res['error'][:80]}）")
    return "\n".join(lines)
