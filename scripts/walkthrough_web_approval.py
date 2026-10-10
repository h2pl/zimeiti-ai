"""Web 审批页真机走查（A7）：Playwright 驱动真实审批页完成双闸门审批。

前置：uvicorn :8000（含双闸门重登记修复）+ vite :5173 + 一轮已在选题闸门
中断的托管循环（scripts/hosted_e2e_trigger.py）。

流程：
  1. 打开 http://localhost:5173，断言待审批卡片出现（真实 pending 数据）
  2. 截图留证 → 点击「确认发布」→ 等待创作完成（LLM 耗时，轮询最长 5 分钟）
  3. 发布闸门重登记后页面出现新卡片 → 截图 → 再次确认 → 等待发布+读回
  4. 断言执行日志出现 cycle_completed

用法（仓库根）：
  cd apps/api && uv run python ../../scripts/walkthrough_web_approval.py
"""

import re
import sys
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from playwright.sync_api import sync_playwright

WEB = "http://localhost:5173"
SLUG = datetime.now().strftime("%Y%m%d-%H%M%S")
SHOT_DIR = Path("data/outputs/web-approval") / SLUG


def _shot(page, name: str) -> str:
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = SHOT_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"[shot] {path}")
    return str(path)


def _wait_log_action(page, action: str, timeout_s: int) -> bool:
    """轮询执行日志表直到出现指定动作（审批是长耗时 POST，期间页面 busy）。"""
    import time

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            body = page.inner_text("body")
            if action in body:
                return True
        except Exception:  # noqa: BLE001 - 页面刷新间隙元素可能短暂不可用
            pass
        time.sleep(5)
        if page.locator(".card").count() == 0 and action != "cycle_completed":
            # 卡片消失 = 本轮 approve 已被消费（可能正在创作）
            pass
    return False


def main() -> int:
    print(f"[web-approval] 走查开始，截图目录 {SHOT_DIR}")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(WEB)
        page.wait_for_selector(".card", timeout=30_000)

        # ── 闸门#1：选题审批 ────────────────────────────────────────
        card_text = page.locator(".card").first.inner_text()
        thread_id = re.search(r"thread:\s*(\S+)", card_text).group(1)
        print(f"[web-approval] 待审批卡片：{thread_id}")
        _shot(page, "1-topic-gate")

        page.locator(".card").first.get_by_text("确认发布").click()
        print("[web-approval] 已点击确认（选题）——等待创作与发布中断……")
        # 恢复后：create_drafts（LLM 真实创作）→ publish 中断 → 重登记
        ok = _wait_log_action(page, "awaiting_approval", timeout_s=360)
        page.wait_for_timeout(6_000)  # 等前端 5s 轮询刷新出新卡片
        page.reload()
        page.wait_for_timeout(3_000)

        cards = page.locator(".card")
        if cards.count() == 0:
            print("[web-approval] FAIL：发布闸门未在页面出现（双闸门重登记缺失？）")
            _shot(page, "fail-no-second-card")
            return 1
        print(f"[web-approval] 发布闸门卡片出现：{cards.first.inner_text()[:80]}")
        _shot(page, "2-publish-gate")

        # ── 闸门#2：发布审批（gzh = 真实草稿箱上传 + 读回） ──────────
        cards.first.get_by_text("确认发布").click()
        print("[web-approval] 已点击确认（发布）——等待草稿箱上传与读回……")
        ok = _wait_log_action(page, "cycle_completed", timeout_s=600)
        page.wait_for_timeout(6_000)
        page.reload()
        page.wait_for_timeout(3_000)
        _shot(page, "3-completed")

        body = page.inner_text("body")
        if "cycle_completed" not in body:
            print("[web-approval] FAIL：执行日志未见 cycle_completed")
            return 1
        print(f"[web-approval] PASS：双闸门经 Web 审批页真实走查完成（thread {thread_id}）")
        browser.close()
        return 0


if __name__ == "__main__":
    sys.exit(main())
