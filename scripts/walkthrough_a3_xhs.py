"""Task 2.3 真账号走查 A3-xhs（DOM 草稿路线）：扫码登录 → 真实创作 → 合规 → 存草稿 → 读回。

复用 xhs-toolkit 实测流程（创作者中心发布页，存草稿按钮），登录态复用。
证据落盘：data/outputs/xhs-main/<slug>/drafts.json + 审计 JSONL + debug 目录。
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
from zimeiti_api.compliance import ComplianceGate
from zimeiti_api.creation import create_drafts
from zimeiti_api.models import get_model
from zimeiti_api.platforms.xhs import XhsPublisher, make_cover_png
from zimeiti_api.profiles import load_profile
from zimeiti_api.topics import select_topic

SLUG = datetime.now().strftime("%Y%m%d-%H%M%S")
OUT_DIR = Path("data/outputs/xhs-main") / SLUG
TOPIC_TITLE = "记录：我用一个 AI Agent 跑通自媒体选题到发布的完整流程"


def main() -> int:
    print("[A3-xhs] 开始真账号走查（DOM 草稿路线）")
    audit.record("walkthrough_a3_xhs_started", slug=SLUG, mode="dom_draft")

    profile = load_profile("xhs-main")
    topic = select_topic(
        {
            "title": TOPIC_TITLE,
            "reason": "A3 验收走查（用户确认执行）",
            "direction": "以 zimeiti-ai 真实使用体验为主线的小红书图文。"
            "合规硬约束：只描述操作步骤与事实；禁止出现「跑通/轻松/高效/提效/"
            "收益/赚钱/秒/翻倍」等承诺性、夸大性词汇；标题平实陈述即可",
        }
    )

    print("[A2] 调用模型创作草稿……")
    drafts = create_drafts(get_model(), topic, profile)
    gate = ComplianceGate()
    review = gate.review(f"{drafts.xhs.title}\n{drafts.xhs.body}")
    if not review["passed"]:
        print("[BLOCKED] 合规未通过:", review["violations"])
        return 2
    print(f"[A2] 草稿生成并过合规：标题={drafts.xhs.title!r} 正文 {len(drafts.xhs.body)} 字")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "drafts.json").write_text(
        json.dumps(
            {
                "topic": topic.title,
                "account": "xhs-main",
                "created_at": SLUG,
                "compliance": review,
                "drafts": {"xhs": vars(drafts.xhs)},
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    pub = XhsPublisher()
    if not Path(pub.storage_state).exists():
        print("[登录] 无登录态，浏览器将弹出，请用小红书 App 扫码……")
        audit.record("xhs_login_started", slug=SLUG)
        pub.login_interactive()
        audit.record("xhs_login_saved", slug=SLUG)
        print("[登录] 扫码成功，登录态已持久化")
    else:
        print(f"[登录] 复用已有登录态：{pub.storage_state}")

    cover = str(make_cover_png(OUT_DIR / "cover.png"))
    debug_dir = str(OUT_DIR / "debug")

    # 模型 invoke（litellm）可能在当前线程残留事件循环，导致 sync Playwright 报
    # 「Sync API inside the asyncio loop」——浏览器操作放进独立线程隔离执行
    # （生产接线同理：async 上下文内用 asyncio.to_thread 调 sync Playwright）
    import threading

    box: dict = {}

    def _browser_flow() -> None:
        page = None
        try:
            page = pub._open_page()  # 整个流程复用同一 Playwright 实例（A3 踩坑）
            print("[草稿] 打开创作者中心发布页填表并私密发布……")
            box["publish"] = pub.publish_draft(
                drafts.xhs, page=page, cover_path=cover, debug_dir=debug_dir
            )
            print("[读回] 笔记管理页对账……")
            box["readback"] = pub.readback(
                drafts.xhs.title[:20], page=page, debug_dir=debug_dir
            )
        except Exception as exc:  # noqa: BLE001 - 异常带回主线程处理
            box["error"] = exc
        finally:
            if page is not None:
                page.close()

    worker = threading.Thread(target=_browser_flow)
    worker.start()
    worker.join()
    if "error" in box:
        raise box["error"]
    platform_result = box["publish"]
    print(f"[草稿] 提交结果：{platform_result}")
    readback = box["readback"]
    audit.record(
        "published",
        account="xhs-main",
        outcome=readback,
        platform_result=platform_result,
        drill="a3_xhs_dom_draft",
        slug=SLUG,
    )
    print(f"[读回] outcome={readback}")

    if readback == "verified":
        print("[A3-xhs] 验证通过（verified）——请到小红书 App 草稿箱人工确认内容")
        return 0
    print("[A3-xhs] 读回未核实：debug 目录已落盘页面快照，检查选择器/登录态")
    return 1


if __name__ == "__main__":
    sys.exit(main())
