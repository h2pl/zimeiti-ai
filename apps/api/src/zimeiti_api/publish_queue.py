"""定时发布排期队列 + mark 幂等回填（P0⑤）。

参考: Easel skill-publish-scheduler/scripts/publish_queue.py——
「内容×平台×时间」持久化队列，到期派发，发布后 mark 回填状态
（Easel 明文纪律：「每条发布后务必 mark，避免重复发布」）。

前置纪律（宪法 I，不可绕过）：队列条目**只能来自已人工批准的发布**
（审批通过后由审批流程/用户排期），队列扫描执行时不再重复审批——
频控/白名单/凭证门禁仍然生效（PublishExecutor）。

终态语义：done / failed 为终态，重复 mark 忽略（幂等回填）；
soft_block 冷却中的到期条目保留 pending，下轮扫描再试。
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

TERMINAL_STATUS = ("done", "failed")


def _queue_path() -> Path:
    from zimeiti_api.config import DATA_DIR

    return Path(DATA_DIR) / "state" / "publish-queue.json"


def _load(path: Path | None = None) -> list[dict[str, Any]]:
    p = path or _queue_path()
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (ValueError, OSError):
        return []


def _save(entries: list[dict[str, Any]], path: Path | None = None) -> None:
    p = path or _queue_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def schedule(
    account: str, drafts_path: str, run_at: str, title: str = "", path: Path | None = None
) -> str:
    """入队（仅审批通过后调用）。run_at: ISO 格式本地时间。返回条目 id。"""
    entries = _load(path)
    entry_id = uuid.uuid4().hex[:12]
    entries.append(
        {
            "id": entry_id,
            "account": account,
            "drafts_path": drafts_path,
            "title": title,
            "run_at": run_at,
            "status": "pending",
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
    )
    _save(entries, path)
    from zimeiti_api import audit

    audit.record("publish_scheduled", account=account, entry_id=entry_id, run_at=run_at)
    return entry_id


def due(now: datetime | None = None, path: Path | None = None) -> list[dict[str, Any]]:
    """到期待发布条目（pending 且 run_at ≤ now，按时间升序）。"""
    now = now or datetime.now()
    return [
        e
        for e in _load(path)
        if e.get("status") == "pending" and e.get("run_at", "") <= now.isoformat(timespec="seconds")
    ]


def mark(entry_id: str, status: str, detail: str = "", path: Path | None = None) -> bool:
    """回填状态（幂等）：终态条目的重复 mark 忽略。"""
    if status not in TERMINAL_STATUS:
        raise ValueError(f"非法状态 {status}（允许 {TERMINAL_STATUS}）")
    entries = _load(path)
    for e in entries:
        if e.get("id") == entry_id:
            if e.get("status") in TERMINAL_STATUS:
                return False  # 幂等：终态不可覆盖
            e["status"] = status
            e["detail"] = detail[:300]
            e["marked_at"] = datetime.now().isoformat(timespec="seconds")
            _save(entries, path)
            from zimeiti_api import audit

            audit.record("publish_queue_marked", entry_id=entry_id, status=status)
            return True
    return False


def run_due(now: datetime | None = None, path: Path | None = None) -> list[dict[str, Any]]:
    """扫描执行到期条目（网关定时调用）。

    平台停用 → mark failed（等恢复也无意义，需重新审批排期）；
    软风控冷却 → 保留 pending 下轮再试；发布成功/失败 → mark done/failed。
    """
    from zimeiti_api import platform_state, risk

    results = []
    for entry in due(now, path):
        account = entry["account"]
        if not platform_state.is_enabled(account):
            mark(entry["id"], "failed", "平台已停用（登录失效）", path)
            results.append({"id": entry["id"], "status": "failed", "reason": "disabled"})
            continue
        if risk.in_cooldown(account, now):
            results.append({"id": entry["id"], "status": "pending", "reason": "cooldown"})
            continue
        try:
            result = execute_approved_publish(account, entry["drafts_path"])
            mark(entry["id"], "done", json.dumps(result, ensure_ascii=False, default=str), path)
            results.append({"id": entry["id"], "status": "done"})
        except Exception as exc:  # noqa: BLE001 - 单条失败不中断队列
            level = risk.handle_platform_error(account, "publish_queue", str(exc))
            if level == "soft_block":
                # 冷却中：保留 pending，下轮再试
                results.append({"id": entry["id"], "status": "pending", "reason": "cooldown"})
                continue
            mark(entry["id"], "failed", str(exc)[:300], path)
            results.append({"id": entry["id"], "status": "failed"})
    return results


def execute_approved_publish(account: str, drafts_path: str) -> dict:
    """执行一条已批准的发布（与 tools.publish 同一链路：执行器+真实路由+读回）。"""
    from zimeiti_api.config import CREDENTIALS_DIR
    from zimeiti_api.publisher import PublishExecutor
    from zimeiti_api.tools import real_platform_router

    drafts = json.loads((Path(drafts_path) / "drafts.json").read_text(encoding="utf-8"))["drafts"]
    platform_draft = drafts["gzh"] if account.startswith("gzh") else drafts["xhs"]
    cred_file = Path(CREDENTIALS_DIR) / f"{account}.sealed"
    if not cred_file.exists():
        raise ValueError(f"账号 {account} 无已存凭证（{cred_file}），拒绝发布")
    executor = PublishExecutor(daily_limit=2, allowed_accounts={"xhs-main", "gzh-main"})
    return executor.publish(
        account,
        platform_draft,
        platform_call=real_platform_router,
        credentials_sealed=cred_file.read_text(encoding="utf-8").strip(),
    )
