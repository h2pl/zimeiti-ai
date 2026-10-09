"""Task 2.4 真账号走查 A4：人为制造读回失败 → unverified 留痕。

场景：真实上传草稿后，用篡改标题（与草稿箱实际标题不匹配）做读回对账，
断言 outcome=unverified 且审计 JSONL 留痕（不冒报成功，宪法 IV）。
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

from zimeiti_api import audit
from zimeiti_api.credentials import load_account_credentials
from zimeiti_api.platforms.gzh import GzhClient, publish_gzh_draft, readback_gzh_draft

TS = datetime.now().strftime("%Y%m%d-%H%M%S")


def main() -> int:
    print("[A4] 读回失败演练开始（真实草稿箱）")
    audit.record("walkthrough_a4_started", drill="readback_failure", ts=TS)

    creds = load_account_credentials("gzh-main")
    client = GzhClient(creds["app_id"], creds["app_secret"])

    # 1. 真实上传一篇演练草稿（草稿箱安全可逆，不群发）
    title = f"【演练A4】读回失败场景-{TS}"
    outcome = publish_gzh_draft(
        client,
        {"title": title, "body": "演练正文：验证读回对账失败时的 unverified 留痕。", "summary": "A4 演练"},
    )
    print(f"[A4] 上传结果：{json.dumps(outcome, ensure_ascii=False)}")

    # 2. 基线：用正确标题读回 → verified
    ok = readback_gzh_draft(client, title)
    print(f"[A4] 正确标题读回：{ok}")

    # 3. 人为制造读回失败：篡改标题 → unverified
    tampered = f"{title}-篡改"
    bad = readback_gzh_draft(client, tampered)
    print(f"[A4] 篡改标题读回：{bad}")

    # 4. 按生产路径的事件形态留痕（tools.publish 同款 record）
    audit.record(
        "published",
        account="gzh-main",
        outcome=bad,
        platform_result=outcome["platform_result"],
        drill="a4_readback_failure",
        ts=TS,
    )

    if ok == "verified" and bad == "unverified":
        print("[A4] 验证通过：verified/unverified 边界正确，审计已留痕")
        return 0
    print("[A4] 验证失败：读回三档判定不符合预期")
    return 1


if __name__ == "__main__":
    sys.exit(main())
