"""S6 内容库浏览与预览：目录卡片 → 进入 → 打开文件 → 预览区渲染内容。

fixture（outputs/e2e-fixture/note.md）由 runner 在 spawn 前预置、teardown 删除。
"""

TITLE = "内容库浏览与预览"

from runner import FIXTURE_DIRNAME


def run(page, ctx, check) -> dict:
    from helpers import ensure_ready, goto_page
    ensure_ready(page, ctx)

    goto_page(page, "内容库")
    page.wait_for_timeout(600)  # 目录树 GET

    # 目录卡片 → 进入
    d = page.locator(".gcard", has_text=FIXTURE_DIRNAME).first
    tree_ok = d.count() > 0
    check(f"[{ctx.target}] 内容库目录树渲染（含 fixture 目录）", tree_ok)
    if not tree_ok:
        return {"tree": False, "preview": False}

    d.click()
    page.wait_for_timeout(500)

    # 文件卡片 → 打开预览
    f = page.locator(".gcard", has_text="note.md").first
    file_ok = f.count() > 0
    check(f"[{ctx.target}] 文件卡片可见", file_ok)
    preview_ok = False
    if file_ok:
        f.click()
        # 预览渲染（iframe 或文本面板），断言 fixture 正文出现
        found = False
        for _ in range(20):
            body = page.locator("body").inner_text()
            if "E2E 固定装置" in body:
                found = True
                break
            # iframe 预览：进入 frame 找
            for fr in page.frames:
                try:
                    if "E2E 固定装置" in (fr.locator("body").inner_text() or ""):
                        found = True
                        break
                except Exception:
                    continue
            if found:
                break
            page.wait_for_timeout(400)
        preview_ok = found
    check(f"[{ctx.target}] 预览渲染文件内容", preview_ok)
    # 预览是 drawer-overlay（全屏遮罩）——必须关闭，否则遮住后续场景的导航
    try:
        page.locator(".drawer-overlay").click()
        page.wait_for_timeout(400)
    except Exception:
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
    closed = page.locator(".drawer-overlay").count() == 0
    check(f"[{ctx.target}] 预览抽屉已关闭", closed)
    return {"tree": tree_ok, "preview": preview_ok, "drawer_closed": closed}
