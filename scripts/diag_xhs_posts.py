"""诊断发布点击后的全部 POST 请求（全量抓包）。"""

import os
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
os.chdir(ROOT / "apps/api")

from dotenv import load_dotenv

load_dotenv()

from zimeiti_api.creation import XhsDraft
from zimeiti_api.platforms.xhs import XhsPublisher, make_cover_png


def main() -> int:
    pub = XhsPublisher()
    box: dict = {}

    def flow() -> None:
        page = pub._open_page()
        posts: list = []

        def on_response(r):
            if r.request.method == "POST" and "xiaohongshu" in r.url:
                try:
                    body = r.text()[:120]
                except Exception:  # noqa: BLE001
                    body = "<no body>"
                posts.append((r.status, r.url[:110], body))

        page.on("response", on_response)
        try:
            draft = XhsDraft(title="diag 发布验证", body="发布链路诊断正文。")
            cover = str(make_cover_png("data/outputs/xhs-main/diag_publish_click/cover.png"))
            debug = "data/outputs/xhs-main/diag_publish_click/debug"
            pub._fill_note(draft, page=page, cover_path=cover, debug_dir=debug)
            for el in page.locator("text=公开可见").all():
                try:
                    if el.is_visible():
                        el.click()
                        break
                except Exception:  # noqa: BLE001  # nosec B112
                    continue
            page.wait_for_timeout(1_000)
            page.locator("text=仅自己可见").first.click()
            time.sleep(1)
            page.locator(".btn-wrapper").first.click()
            time.sleep(10)
            page.screenshot(path=f"{debug}/after_submit.png")
            box["url"] = page.url
        finally:
            box["posts"] = posts
            page.close()

    t = threading.Thread(target=flow)
    t.start()
    t.join()
    print("[url]", box.get("url"))
    print("[POSTs]")
    for p in box.get("posts", []):
        print("  ", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
