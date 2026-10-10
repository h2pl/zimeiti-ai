"""托管形态端到端实测触发器（A6：真模型 + PG checkpointer + 双人工闸门）。

与审批 API 的跨进程约定：
- thread_id 由本脚本预生成（唯一，不复用），cycle_dir 与 app._resume_thread
  同一约定（OUTPUTS_DIR/<account>/<thread_id>），保证恢复进程读到同一 state.json
- 中断后脚本退出；恢复走 API /api/approvals/{thread_id}/confirm（另一进程）

用法（在仓库根执行）：
  cd apps/api && uv run python ../../scripts/hosted_e2e_trigger.py [account]

流程：发现选题 → select_topic 中断（人工审批#1）→ 创作+发布 → publish 中断
（人工审批#2）→ xhs 私密发布 + 读回对账。
"""

import asyncio
import json
import sys
import uuid
from pathlib import Path

if sys.platform == "win32":
    # psycopg 异步模式要求 Selector 事件循环（与 tests/conftest.py 同一约定）
    from asyncio import WindowsSelectorEventLoopPolicy

    asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
import os

os.chdir(ROOT / "apps/api")
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv

load_dotenv()

from zimeiti_api.runtime import hosted
from zimeiti_api.runtime.checkpoints import get_checkpointer
from zimeiti_api.config import OUTPUTS_DIR
from zimeiti_api.runtime.graph import build_minimal_agent
from zimeiti_api.core.models import get_model
from zimeiti_api.content.profiles import load_profile
from zimeiti_api.governance.publisher import PublishExecutor

ACCOUNT = sys.argv[1] if len(sys.argv) > 1 else "xhs-main"
DIRECTION = sys.argv[2] if len(sys.argv) > 2 else ""
THREAD_ID = f"hosted-{uuid.uuid4().hex[:12]}"


def _dump_interrupt(result: dict) -> None:
    for it in result.get("__interrupt__") or []:
        val = getattr(it, "value", it)
        print(json.dumps({"interrupt": str(val)[:800]}, ensure_ascii=False, default=str))


async def main() -> int:
    profile = load_profile(ACCOUNT)
    cycle_dir = Path(OUTPUTS_DIR) / profile["account"] / THREAD_ID
    executor = PublishExecutor(daily_limit=2, allowed_accounts={"xhs-main", "gzh-main"})
    print(f"[hosted-e2e] account={ACCOUNT} thread_id={THREAD_ID}")

    async with get_checkpointer() as saver:
        agent = build_minimal_agent(
            get_model(),
            saver,
            profile,
            executor,
            cycle_dir=cycle_dir,
        )
        instruction = (
            "请执行一轮完整运营循环："
            "1) 调用 discover_topics 发现选题"
            + (f"，并传入 manual_direction=\"{DIRECTION}\"" if DIRECTION else "")
            + "，"
            "2) 从中调用 select_topic 挑选最适合本账号的一个（会触发人工确认），"
            "3) 调用 create_drafts 创作图文草稿，"
            "4) 调用 publish 发布（会再次进入人工审批，发布结果以读回为准）。"
        )
        result = await hosted.run_hosted_cycle(
            agent, THREAD_ID, instruction, account=ACCOUNT
        )
        if "__interrupt__" in result:
            print("[hosted-e2e] 已在人工闸门中断，等待审批（API /api/approvals）")
            _dump_interrupt(result)
            return 0
        print("[hosted-e2e] 未中断直接完成（异常：双闸门应至少中断一次）")
        print(json.dumps(result["messages"][-1].content, ensure_ascii=False)[:500])
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
