# -*- coding: utf-8 -*-
"""探针：API 返回 HTML 时，用量卡片呈现可行动错误而非原始 JSON 解析异常（api-error-clarity D3）。

场景对应「dev 代理失效」：/api/* 落进 vite SPA 兜底返回 index.html。
用 Playwright route 拦截精确注入该场景，不依赖人为弄坏代理。

用法：起一个后端实例（:8118），然后
    cd apps/api && uv run python ../scripts/probe_api_error.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from record_brand_demo import install_cursor  # noqa: E402

from playwright.sync_api import sync_playwright  # noqa: E402

BASE = "http://127.0.0.1:8118"
FAKE_HTML = "<!doctype html><html lang=\"en\"><head></head><body>dev index</body></html>"


def main() -> int:
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        page = b.new_context(viewport={"width": 1440, "height": 900}).new_page()
        page.on("dialog", lambda d: d.accept())
        page.goto(BASE, wait_until="load")
        page.wait_for_selector(".app-layout", timeout=25000)
        d = page.get_by_role("button", name="先用通用模式")
        if d.count():
            d.first.click()
            page.wait_for_timeout(400)
        install_cursor(page)

        # 注入故障：/api/usage 返回 HTML（复刻 vite 代理失效的表象）。
        # 工作台是默认页，首次 fetch 早于注册——注册后 reload 让拦截真正生效。
        page.route("**/api/usage*", lambda r: r.fulfill(
            status=200, content_type="text/html", body=FAKE_HTML))
        page.reload(wait_until="load")
        page.wait_for_selector(".usage-card", timeout=15000)
        page.wait_for_timeout(1500)
        txt = page.locator(".usage-card").inner_text()

        ok = ("HTML 而非 JSON" in txt) and ("Unexpected token" not in txt) and ("重启" in txt)
        print("用量卡片错误文案：", txt[:120].replace("\n", " | "))
        print("① 友好错误呈现：", "HTML 而非 JSON" in txt)
        print("② 无原始解析异常：", "Unexpected token" not in txt)
        print("③ 含处置指引（重启）：", "重启" in txt)
        print("PASS" if ok else "FAIL")
        b.close()
        return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
