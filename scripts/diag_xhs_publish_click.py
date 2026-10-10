"""诊断发布点击后的真实结果：抓 note 创建 XHR 响应 + 弹层 + 截图。"""

import json
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
os_cwd = ROOT / "apps/api"
import os

os.chdir(os_cwd)

from dotenv import load_dotenv

load_dotenv()

from zimeiti_api.content.creation import XhsDraft
from zimeiti_api.platforms.xhs import XhsPublisher, make_cover_png

SLUG = "diag-publish-click"


def main() -> int:
    pub = XhsPublisher()
    box: dict = {}

    def flow() -> None:
        page = pub._open_page()
        responses = []

        def on_response(r):
            if "sns/v2/note" in r.url or "redcaptcha" in r.url:
                try:
                    body = r.text()[:300]
                except Exception:  # noqa: BLE001
                    body = "<no body>"
                responses.append({"url": r.url[:120], "status": r.status, "body": body})

        page.on("response", on_response)
        try:
            draft = XhsDraft(
                title="diag 发布链路验证笔记",
                body="这是一条发布链路诊断笔记，验证点击发布后的真实服务端响应。",
            )
            cover = str(make_cover_png(f"data/outputs/xhs-main/{SLUG}/cover.png"))
            debug = f"data/outputs/xhs-main/{SLUG}/debug"
            pub._fill_note(
                draft, page=page, cover_path=cover, debug_dir=debug
            )
            # 可见性 → 仅自己可见
            for el in page.locator("text=公开可见").all():
                try:
                    if el.is_visible():
                        el.click()
                        break
                except Exception:  # noqa: BLE001  # nosec B112
                    continue
            page.wait_for_timeout(1_000)
            page.locator("text=仅自己可见").first.click()
            page.wait_for_timeout(1_000)
            # 点击发布
            page.locator("text=发布笔记").first.click()
            page.wait_for_timeout(6_000)
            # 点击后的页面状态
            box["after_click_text"] = page.inner_text("body")[:600]
            page.screenshot(path=f"data/outputs/xhs-main/{SLUG}/debug/after_click.png")
            box["url_after"] = page.url
            page.wait_for_timeout(4_000)
        finally:
            box["responses"] = responses
            page.close()

    t = threading.Thread(target=flow)
    t.start()
    t.join()
    print("[url_after]", box.get("url_after", ""))
    print("[responses]")
    for r in box.get("responses", []):
        print("  ", r["status"], r["url"], "|", r["body"][:150])
    text = box.get("after_click_text", "")
    print("[after_click 片段]", text.replace("\n", " | ")[:400])
    return 0


if __name__ == "__main__":
    sys.exit(main())
