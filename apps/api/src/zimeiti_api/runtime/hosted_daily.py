"""托管循环每日触发（PRD 托管形态最后一块：无人触发 + 人在环审批）。

每天定时为每个账号触发一轮托管循环：发现选题 → select_topic 中断 →
（人稍后在 Web 审批页确认）→ 创作 → publish 中断 →（确认）→ 真实发布+读回。
本模块只负责「触发到第一次中断」，恢复由审批 API 端点完成（跨进程断点恢复）。

与 ops_daily 的分工：ops_daily 是数据侧（取数+校准）；hosted_daily 是内容侧
（选题+创作，产出待审批项）。两者共用计划任务机（scripts/run_hosted_daily.bat）。

用法（计划任务与手动一致，须在 apps/api 目录下运行）：
  uv run python -m zimeiti_api.runtime.hosted_daily [account ...]   # 默认 xhs-main gzh-main
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

if sys.platform == "win32":
    # psycopg 异步模式要求 Selector 事件循环（与 tests/conftest.py 同一约定）
    from asyncio import WindowsSelectorEventLoopPolicy

    asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())

DEFAULT_ACCOUNTS = ("xhs-main", "gzh-main")

INSTRUCTION = (
    "请执行一轮完整运营循环："
    "1) 调用 discover_topics 发现选题（信息源不足时结合账号定位自拟方向），"
    "2) 调用 select_topic 挑选最适合本账号的一个（会触发人工确认），"
    "3) 调用 create_drafts 创作图文草稿，"
    "4) 调用 publish 发布（会再次进入人工审批，发布结果以读回为准）。"
    "两个人工闸门无需等待——中断后本轮即结束，人工稍后在审批页确认。"
)


def _log_path() -> Path:
    from zimeiti_api.config import DATA_DIR

    return Path(DATA_DIR) / "metrics" / "hosted_daily.jsonl"


def _pending_accounts() -> set[str]:
    """已有待审批项的账号不再触发（避免审批队列堆积）。"""
    from zimeiti_api.runtime import hosted

    return {p.get("account", "") for p in hosted.list_pending_approvals()}


async def trigger_for_account(account: str) -> dict[str, Any]:
    """为单账号触发一轮托管循环（到第一次人工中断为止）。"""
    from zimeiti_api.config import OUTPUTS_DIR
    from zimeiti_api.content.profiles import load_profile
    from zimeiti_api.core.models import get_model
    from zimeiti_api.governance.publisher import PublishExecutor
    from zimeiti_api.runtime.checkpoints import get_checkpointer
    from zimeiti_api.runtime.graph import build_minimal_agent
    from zimeiti_api.runtime.hosted import run_hosted_cycle

    profile = load_profile(account)
    executor = PublishExecutor(daily_limit=2, allowed_accounts={"xhs-main", "gzh-main"})
    async with get_checkpointer() as saver:
        agent = build_minimal_agent(
            get_model(),
            saver,
            profile,
            executor,
            cycle_dir=Path(OUTPUTS_DIR)
            / account
            / f"daily-{datetime.now().strftime('%Y%m%d')}-{account}",
        )
        result = await run_hosted_cycle(agent, None, INSTRUCTION, account=account)
    interrupted = "__interrupt__" in result
    return {"account": account, "interrupted": interrupted}


async def run_daily_async(accounts: list[str] | None = None) -> list[dict[str, Any]]:
    """异步版（常驻网关进程内直接 await，参考: openclaw gateway 内嵌 agent turn）。"""
    from zimeiti_api.governance import platform_state

    accounts = accounts or list(DEFAULT_ACCOUNTS)
    busy = _pending_accounts()
    runs = []
    for account in accounts:
        if account in busy:
            runs.append({"account": account, "skipped": "已有待审批项"})
            continue
        if not platform_state.is_enabled(account):
            runs.append({"account": account, "skipped": "平台已停用（登录失效待人工恢复）"})
            continue
        try:
            runs.append(await trigger_for_account(account))
        except Exception as exc:  # noqa: BLE001 - 单账号失败不中断其他账号
            runs.append({"account": account, "error": str(exc)[:300]})
    _append_log(runs)
    return runs


def _append_log(runs: list[dict[str, Any]]) -> None:
    log = _log_path()
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {"ts": datetime.now().isoformat(timespec="seconds"), "runs": runs},
                ensure_ascii=False,
            )
            + "\n"
        )


def run_daily(accounts: list[str] | None = None) -> list[dict[str, Any]]:
    """同步版（CLI/计划任务入口：asyncio.run 包装）。"""
    return asyncio.run(run_daily_async(accounts))


def main(argv: list[str] | None = None) -> int:
    from dotenv import load_dotenv

    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    load_dotenv()
    runs = run_daily(argv)
    print(json.dumps(runs, ensure_ascii=False))
    ok = all(("interrupted" in r or "skipped" in r) for r in runs)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
