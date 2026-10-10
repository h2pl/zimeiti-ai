"""Task 2.5 真账号走查 A5：频控边界——日限 2 篇后第三篇被拒（宪法 III）。

场景：PublishExecutor daily_limit=2，经真实路由器（gzh 草稿箱）连续发布 2 篇；
第 3 篇必须在平台函数零调用下被拒绝（publish_failed 留痕）。
"""

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
import os

os.chdir(ROOT / "apps/api")

from dotenv import load_dotenv

load_dotenv()

from zimeiti_api.core import audit
from zimeiti_api.core.credentials import load_account_credentials
from zimeiti_api.platforms.gzh import GzhClient
from zimeiti_api.governance.publisher import PublishExecutor, RateLimitExceeded
from zimeiti_api.runtime.tools import real_platform_router

TS = datetime.now().strftime("%Y%m%d-%H%M%S")


def main() -> int:
    print("[A5] 频控边界演练开始（真实草稿箱，daily_limit=2）")
    audit.record("walkthrough_a5_started", drill="rate_limit", ts=TS)

    creds = load_account_credentials("gzh-main")
    client = GzhClient(creds["app_id"], creds["app_secret"])
    before = client.draft_count()
    print(f"[A5] 演练前草稿数：{before}")

    executor = PublishExecutor(daily_limit=2, allowed_accounts={"gzh-main"})
    # 凭证密封文本：与生产 tools._account_credentials 同源（读 {account}.sealed 文件）
    sealed = (Path("data/credentials") / "gzh-main.sealed").read_text(encoding="utf-8").strip()

    published = []
    for i in (1, 2):
        result = executor.publish(
            "gzh-main",
            {
                "title": f"【演练A5】频控边界-{i}-{TS}",
                "body": f"频控演练第 {i} 篇正文。",
                "summary": "A5 频控演练",
            },
            platform_call=real_platform_router,
            credentials_sealed=sealed,
        )
        published.append(result)
        audit.record("published", account="gzh-main", drill="a5_rate_limit", seq=i, **result)
        print(f"[A5] 第 {i} 篇：{json.dumps(result, ensure_ascii=False)}")

    # 第三篇：必须拒绝，且平台函数零调用（草稿数不变）
    mid = client.draft_count()
    blocked = False
    try:
        executor.publish(
            "gzh-main",
            {"title": f"【演练A5】超限篇-{TS}", "body": "不应被上传。", "summary": ""},
            platform_call=real_platform_router,
            credentials_sealed=sealed,
        )
    except RateLimitExceeded as exc:
        blocked = True
        audit.record("publish_failed", account="gzh-main", error=str(exc), drill="a5_rate_limit")
        print(f"[A5] 第三篇被拒：{exc}")
    after = client.draft_count()
    print(f"[A5] 拒绝后草稿数：{after}（拒绝时 {mid}，差值应为 0）")

    if blocked and len(published) == 2 and after - mid == 0:
        print("[A5] 验证通过：2 篇真实上传 + 第三篇零调用拒绝 + 审计留痕")
        return 0
    print("[A5] 验证失败：频控边界行为不符合预期")
    return 1


if __name__ == "__main__":
    sys.exit(main())
