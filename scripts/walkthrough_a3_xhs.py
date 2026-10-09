"""Task 2.3 真账号走查 A3-xhs（xiaohongshu-mcp API 路线）。

前置（一次性）：
  1. data/tools/xiaohongshu-login-windows-amd64.exe   # 扫码登录一次
  2. data/tools/xiaohongshu-mcp-windows-amd64.exe -headless  # 常驻 :18060
发布由 xiaohongshu-mcp 执行（visibility=仅自己可见，宪法 I）；读回走
创作者中心笔记管理页（DOM，独立线程隔离事件循环）。
证据落盘：data/outputs/xhs-main/<slug>/drafts.json + 审计 JSONL。
"""

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
import os

os.chdir(ROOT / "apps/api")
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

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
    print("[A3-xhs] 开始真账号走查（xiaohongshu-mcp API 路线）")
    audit.record("walkthrough_a3_xhs_started", slug=SLUG, mode="mcp_api")

    profile = load_profile("xhs-main")
    topic = select_topic(
        {
            "title": TOPIC_TITLE,
            "reason": "A3 验收走查（用户确认执行）",
            "direction": "以 zimeiti-ai 真实使用体验为主线的小红书图文；"
            "只记录流程与事实，不承诺收益、不夸大效果（合规要求）",
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

    cover = str(make_cover_png(OUT_DIR / "cover.png"))
    debug_dir = str(OUT_DIR / "debug")
    pub = XhsPublisher()

    # 发布走 API（requests 不受事件循环影响）
    print("[发布] 调用 xiaohongshu-mcp API 私密发布……")
    result = pub.publish_draft(drafts.xhs, cover_path=cover)
    print(f"[发布] 结果：{json.dumps(result, ensure_ascii=False, default=str)[:200]}")
    audit.record("xhs_mcp_published", account="xhs-main", slug=SLUG, result=result)

    # 读回走 DOM 子进程（litellm 残留事件循环会污染 sync Playwright，A3 实测）
    import subprocess

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "zimeiti_api.xhs_readback",
            "--title",
            drafts.xhs.title[:20],
            "--debug-dir",
            debug_dir,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(ROOT / "apps/api"),
    )
    try:
        readback = json.loads(proc.stdout.strip().splitlines()[-1])["outcome"]
    except (ValueError, IndexError, KeyError):
        print("[读回] 子进程输出异常:", proc.stdout[-200:], proc.stderr[-200:])
        readback = "unverified"

    audit.record(
        "published",
        account="xhs-main",
        outcome=readback,
        platform_result=result.get("status", ""),
        drill="a3_xhs_mcp",
        slug=SLUG,
    )
    print(f"[读回] outcome={readback}")

    if readback == "verified":
        print("[A3-xhs] 验证通过（verified）——请到小红书 App 确认笔记（仅自己可见）")
        return 0
    print("[A3-xhs] 读回未核实：检查 debug/note_list.txt 与审计")
    return 1


if __name__ == "__main__":
    sys.exit(main())
