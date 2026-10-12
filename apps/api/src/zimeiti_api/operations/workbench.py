"""工作台数据面（web-workbench T1-T3，只读 + 受控画像写）。

参考: Easel web/frontend 的 Dashboard/Profile/Outputs/Trends 页面数据契约。
纯函数便于单测；端点层（app.py）只做 HTTP 适配。
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

# account 参数白名单（D3：路径遍历防护）
_ACCOUNT_RE = re.compile(r"^[A-Za-z0-9_-]+$")

THEME_NOTE = "画像写入即 git 追踪文件变更（可 diff 可回滚）"


def valid_account(account: str) -> bool:
    return bool(_ACCOUNT_RE.match(account))


def dashboard_summary(
    pending_count: int,
    accounts: dict[str, bool],
    publish_events: list[dict],
    recent_log: list[dict],
) -> dict[str, Any]:
    today = datetime.now().strftime("%Y-%m-%d")
    return {
        "pending_approvals": pending_count,
        "accounts": accounts,
        "today_publishes": sum(1 for e in publish_events if e["publish_date"] == today),
        "recent_log": recent_log[-10:],
    }


def list_accounts(profiles_dir: Path) -> list[dict[str, Any]]:
    """画像目录扫描：[{account, enabled}]（enabled 由 governance 状态文件判定）。"""
    from zimeiti_api.governance import platform_state

    out = []
    if profiles_dir.exists():
        for d in sorted(profiles_dir.iterdir()):
            if d.is_dir() and (d / "profile.yaml").exists():
                out.append({"account": d.name, "enabled": platform_state.is_enabled(d.name)})
    return out


def load_profile_data(account: str) -> dict[str, Any] | None:
    """查看指定账号画像（含 enabled）；account 不存在返回 None。"""
    if not valid_account(account):
        raise ValueError("非法账号名")
    from zimeiti_api.content.profiles import load_profile

    try:
        data = load_profile(account)
    except FileNotFoundError:
        return None
    from zimeiti_api.governance import platform_state

    data["enabled"] = platform_state.is_enabled(account)
    return data


def save_profile(account: str, data: dict[str, Any]) -> None:
    """受控画像写（D3）：validate 通过才落盘；account 目录必须已存在（只编辑不创建）。"""
    if not valid_account(account):
        raise ValueError("非法账号名")
    from zimeiti_api.content.profiles import DEFAULT_BASE_DIR, validate_profile

    profile_file = Path(DEFAULT_BASE_DIR) / account / "profile.yaml"
    if not profile_file.exists():
        raise FileNotFoundError(f"画像文件不存在: {profile_file}")
    if data.get("account") != account:
        raise ValueError("account 字段与 URL 不一致")
    validate_profile(data)  # fail-closed：非法输入抛异常，端点层转 400
    import yaml

    # W3：未知键过滤（收敛到既有 schema 键集），enabled 是运行时叠加字段不落盘
    existing_keys = set(yaml.safe_load(profile_file.read_text(encoding="utf-8")).keys())
    data = {k: v for k, v in data.items() if k in existing_keys and k != "enabled"}
    profile_file.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


def trends(account: str, db: Any = None) -> dict[str, Any] | None:
    """趋势数据：复用校准证据引擎（D4，不重写统计）。无数据返回 None（前端降级提示）。"""
    if not valid_account(account):
        raise ValueError("非法账号名")
    from zimeiti_api.operations.calibration import build_evidence
    from zimeiti_api.operations.metrics import MetricsDB

    ev = build_evidence(db or MetricsDB(), platform=account, profile=account)
    if ev["events"] == 0 and ev["snapshots"] == 0:
        return None
    return {
        "platform": ev["platform"],
        "events": ev["events"],
        "snapshots": ev["snapshots"],
        "baseline": ev["baseline"],
        "lifecycle_distribution": ev["lifecycle_distribution"],
        "rhythm": ev["rhythm"],
    }


def outputs(account: str, outputs_dir: Path) -> list[dict[str, Any]]:
    """内容库：已发布草稿产物元数据（D5 只读，不读正文）。"""
    if not valid_account(account):
        raise ValueError("非法账号名")
    root = Path(outputs_dir) / account
    if not root.exists():
        return []
    out = []
    for d in sorted(root.iterdir(), reverse=True):
        f = d / "drafts.json"
        if not f.exists():
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        out.append(
            {
                "slug": d.name,
                "title": (data.get("drafts", {}).get("xhs", {}) or {}).get("title")
                or data.get("topic", ""),
                "topic": data.get("topic", ""),
                "compliance_passed": bool((data.get("compliance") or {}).get("passed")),
                "created_at": data.get("created_at", ""),
            }
        )
    return out


def accounts_detail(
    profiles_dir: Path, credentials_dir: Path, login_state_path: Path
) -> list[dict[str, Any]]:
    """账号管理数据面（web-pages-batch）：画像账号 × 启停 × 凭证 × 登录态。"""
    from zimeiti_api.governance import platform_state

    out = []
    if profiles_dir.exists():
        for d in sorted(profiles_dir.iterdir()):
            if not (d.is_dir() and (d / "profile.yaml").exists()):
                continue
            account = d.name
            out.append(
                {
                    "account": account,
                    "enabled": platform_state.is_enabled(account),
                    "credentials_sealed": (Path(credentials_dir) / f"{account}.sealed").exists(),
                    # 登录态仅 xhs 系账号适用（gzh 走 appid/secret 凭证）
                    "login_state": Path(login_state_path).exists()
                    if account.startswith("xhs")
                    else None,
                }
            )
    return out


def output_detail(account: str, slug: str, outputs_dir: Path) -> dict[str, Any] | None:
    """内容查看器数据面（feat-outputs-viewer T1）：slug 全量元数据 + 双平台正文。

    slug 白名单同 account（D3 只读，防路径遍历）。
    """
    if not (valid_account(account) and valid_account(slug)):
        raise ValueError("非法 account/slug")
    f = Path(outputs_dir) / account / slug / "drafts.json"
    if not f.exists():
        return None
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    return {
        "slug": slug,
        "account": account,
        "topic": data.get("topic", ""),
        "created_at": data.get("created_at", ""),
        "compliance": data.get("compliance") or {},
        "drafts": data.get("drafts") or {},
    }


def preflight_for_draft(account: str, slug: str, outputs_dir: Path) -> dict[str, Any]:
    """发布编排预检（T2）：对双平台 draft 跑 governance.preflight，逐项返回。

    fail-closed：passed = 两平台均无违规。account/slug 白名单同 output_detail。
    """
    detail = output_detail(account, slug, outputs_dir)
    if detail is None:
        raise FileNotFoundError("草稿不存在")
    from zimeiti_api.governance.preflight import preflight

    result: dict[str, list[str]] = {}
    for platform in ("xhs", "gzh"):
        draft = detail["drafts"].get(platform) or {}
        result[platform] = preflight(account, {**draft, "platform": platform})
    return {
        "account": account,
        "slug": slug,
        "preflight": result,
        "passed": all(not v for v in result.values()),
    }


def create_account(data: dict[str, Any], profiles_dir: Path) -> dict[str, Any]:
    """创建账号（feat-accounts-crud）：白名单 + 不存在 + validate → 落盘并启用。"""
    account = str(data.get("account", ""))
    if not valid_account(account):
        raise ValueError("非法账号名")
    acc_dir = Path(profiles_dir) / account
    if (acc_dir / "profile.yaml").exists():
        raise FileExistsError(f"账号已存在: {account}")
    from zimeiti_api.content.profiles import validate_profile

    validate_profile(data)  # fail-closed
    acc_dir.mkdir(parents=True, exist_ok=True)
    import yaml

    (acc_dir / "profile.yaml").write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    from zimeiti_api.core import audit
    from zimeiti_api.governance import platform_state

    platform_state.ensure_defaults()
    platform_state.set_enabled(account, True, reason="创建账号")
    audit.record("account_created", account=account)
    return {**data, "enabled": True}


def delete_account(
    account: str, profiles_dir: Path, credentials_dir: Path, state_path: Path
) -> dict[str, Any]:
    """删除账号（危险操作，全程审计）：画像目录 + 平台状态键 + 凭证文件。"""
    import shutil

    if not valid_account(account):
        raise ValueError("非法账号名")
    acc_dir = Path(profiles_dir) / account
    if not (acc_dir / "profile.yaml").exists():
        raise FileNotFoundError(f"账号不存在: {account}")
    from zimeiti_api.core import audit
    from zimeiti_api.governance import platform_state

    removed: dict[str, Any] = {"profile": True}
    shutil.rmtree(acc_dir)
    state_removed = platform_state.remove_account(account, state_path)
    removed["platform_state"] = state_removed
    sealed = Path(credentials_dir) / f"{account}.sealed"
    if sealed.exists():
        sealed.unlink()
        removed["credentials"] = True
    audit.record("account_deleted", account=account, removed=json.dumps(removed))
    return {"account": account, "removed": removed}
