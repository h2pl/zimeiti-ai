"""每日运营定时任务（调度接线唯一入口，无人值守闭环）。

串接两个既有 CLI（不重复造轮子，只做编排与状态持久化）：
  1. ops_metrics pull —— 每日 T-1 取数（gzh datacube 过去 7 天 + xhs 创作者中心看板）
  2. ops_calibration auto —— 按量触发校准（自上次校准新快照 ≥5 才出报告，xiaobei 对齐）

状态持久化：data/state/ops_daily.json 记录各账号 last_calibrated_at（成功校准后
自动写入，调度器无需手工传参）。设计参考 ops_calibration.auto_calibrate 的
last_calibrated_at 参数——此处补上「谁记录」的缺口。

失败语义：
  - 单平台 pull 失败 → collection_errors 留痕（ops_metrics 既有行为）后继续另一平台
  - 校准失败 → 记入运行日志，不更新 last_calibrated_at（下次重试）
  - 运行日志：data/metrics/ops_daily.jsonl，每次运行一条（可观测）

用法（计划任务与手动一致，须在 apps/api 目录下运行）：
  uv run python -m zimeiti_api.ops_daily [--force] [--skip-pull]

Windows 计划任务注册（Git Bash，或直接 `make schedule-install`）：
  cmd //c "schtasks /Create /TN \"zimeiti-ai-ops-daily\" /SC DAILY /ST 08:30 \
  /TR \"E:\\Projects\\zimeiti-ai\\scripts\\run_ops_daily.bat\""
（默认仅当用户登录时运行——xhs 取数需打开真实浏览器窗口，headless 有风控风险）
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

PLATFORM_SITES = ("gzh", "xhs")  # 取数站点（ops_metrics.pull_platform 的 site 参数）
SITE_ACCOUNTS = {"gzh": "gzh-main", "xhs": "xhs-main"}  # 站点 → 校准账号


def _state_path() -> Path:
    from zimeiti_api.config import DATA_DIR

    return Path(DATA_DIR) / "state" / "ops_daily.json"


def _log_path() -> Path:
    from zimeiti_api.config import DATA_DIR

    return Path(DATA_DIR) / "metrics" / "ops_daily.jsonl"


def _now() -> str:
    """与 MetricsDB.record_snapshot 的 captured_at 同格式（TEXT 字符串比较依赖一致）。"""
    return datetime.now().isoformat(timespec="seconds")


def load_state(path: Path | None = None) -> dict:
    p = path or _state_path()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return {}
    return {}


def save_state(state: dict, path: Path | None = None) -> None:
    p = path or _state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def run_daily(
    db: Any,
    sites: tuple[str, ...] = PLATFORM_SITES,
    force: bool = False,
    skip_pull: bool = False,
    state_path: Path | None = None,
) -> dict:
    """执行一轮每日任务：pull → auto 校准 → 状态与日志落盘。返回运行记录。"""
    from zimeiti_api.ops_calibration import auto_calibrate
    from zimeiti_api.ops_metrics import pull_platform

    state = load_state(state_path)
    run: dict[str, Any] = {"ts": _now(), "pull": {}, "calibration": {}}

    if not skip_pull:
        for site in sites:
            account = SITE_ACCOUNTS[site]
            try:
                run["pull"][account] = pull_platform(db, site)
            except Exception as exc:  # noqa: BLE001 - 单平台失败不中断整体
                run["pull"][account] = {site: {"ok": False, "error": str(exc)[:300]}}

    for site in sites:
        account = SITE_ACCOUNTS[site]
        last = (state.get(account) or {}).get("last_calibrated_at")
        if last is None:
            # 首轮无游标：全部历史快照视为「新」（与 auto_calibrate 非跳过分支的
            # len(snaps) 语义一致），否则 new_count 恒 0 → 永远跳过 → 死锁
            last = "1970-01-01T00:00:00"
        try:
            res = auto_calibrate(db, platform=account, last_calibrated_at=last, force=force)
            if not res.get("skipped"):
                state[account] = {"last_calibrated_at": _now()}
        except Exception as exc:  # noqa: BLE001 - 校准失败留痕，不更新游标
            res = {"error": str(exc)[:300]}
        run["calibration"][account] = res

    save_state(state, state_path)
    log = _log_path()
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(run, ensure_ascii=False, default=str) + "\n")
    return run


def main(argv: list[str] | None = None) -> int:
    import argparse

    from dotenv import load_dotenv

    from zimeiti_api.ops_metrics import MetricsDB

    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]

    load_dotenv()  # 凭证在 apps/api/.env，与 seal CLI 同一加载约定
    parser = argparse.ArgumentParser(description="每日运营定时任务（取数+按量校准）")
    parser.add_argument("--force", action="store_true", help="绕过校准阈值（手动兜底）")
    parser.add_argument("--skip-pull", action="store_true", help="只跑校准（调试用）")
    args = parser.parse_args(argv)

    run = run_daily(MetricsDB(), force=args.force, skip_pull=args.skip_pull)
    # pull_platform 按站点嵌套（{"gzh": {"ok": ...}}），ok 在内层
    pull_ok = any(
        isinstance(v, dict) and v.get("ok") for p in run["pull"].values() for v in p.values()
    )
    print(json.dumps(run, ensure_ascii=False, default=str))
    # 全部站点取数失败视为运行失败（校准跳过不算失败）
    return 0 if (pull_ok or not run["pull"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
