"""诊断 edith 域拒绝原因：在签名浏览器环境内逐级加签名头试 permit（不发布）。"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
import os

os.chdir(ROOT / "apps/api")

from dotenv import load_dotenv

load_dotenv()

from xhs.help import sign as xhs_full_sign

from zimeiti_api.platforms.xhs import XhsApiClient
from zimeiti_api.platforms.xhs_signer import XhsSigner

URI = "/api/media/v1/upload/web/permit"
PARAMS = "biz_name=spectrum&scene=image&file_count=1&version=1&source=web"

# 在页面环境内 fetch edith（credentials include 自动带 cookie），headers 由外部注入
JS_FETCH = """
async ([url, headers]) => {
    const res = await fetch(url, {method: 'GET', headers: headers, credentials: 'include'});
    const text = await res.text();
    return text.slice(0, 200);
}
"""


def main() -> int:
    with XhsSigner("data/login/xhs_state.json") as signer:
        api = XhsApiClient(storage_state="data/login/xhs_state.json")
        cookie_a1 = "x"
        for c in json.loads(Path("data/login/xhs_state.json").read_text(encoding="utf-8"))[
            "cookies"
        ]:
            if c["name"] == "a1":
                cookie_a1 = c["value"]
        b1 = signer.get_b1()
        full = xhs_full_sign(URI, None, a1=cookie_a1, b1=b1)
        page = signer._page

        url = f"https://edith.xiaohongshu.com{URI}?{PARAMS}"
        # 1. 裸 fetch（仅 cookie）
        r1 = page.evaluate(JS_FETCH, [url, {}])
        print("[edith|no-sign]  ", r1[:120])
        # 2. x-s/x-t（window._webmsxyw）
        st = page.evaluate(
            "([uri, data]) => window._webmsxyw(uri, data)", [URI, ""]
        )
        r2 = page.evaluate(
            JS_FETCH, [url, {"x-s": st["X-s"], "x-t": str(st["X-t"])}]
        )
        print("[edith|xs-xt]    ", r2[:120])
        # 3. 三件套（x-s/x-t 用 _webmsxyw，x-s-common 用 python help.sign）
        r3 = page.evaluate(
            JS_FETCH,
            [
                url,
                {
                    "x-s": st["X-s"],
                    "x-t": str(st["X-t"]),
                    "x-s-common": full["x-s-common"],
                },
            ],
        )
        print("[edith|+common]  ", r3[:120])
        # 4. 全 python 签名三件套（对照：requests 同款）
        r4 = page.evaluate(
            JS_FETCH,
            [url, {k: full[k] for k in ("x-s", "x-t", "x-s-common")}],
        )
        print("[edith|py-full]  ", r4[:120])
    return 0


if __name__ == "__main__":
    sys.exit(main())
