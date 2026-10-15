"""S9 设置面板：齿轮打开 → 模型通道/环境区块渲染 → 关闭。"""

TITLE = "设置面板模型通道"


def run(page, ctx, check) -> dict:
    from helpers import ensure_ready, goto_page
    ensure_ready(page, ctx)

    goto_page(page, "工作台")
    gear = page.locator("button[title*='设置']").first
    gear.click()
    page.wait_for_timeout(500)
    opened = page.get_by_text("设置", exact=True).count() > 0 or page.locator(".settings-title").count() > 0
    check(f"[{ctx.target}] 设置面板打开", opened)

    rows = page.locator(".settings-title, [class*='model'], [class*='channel']").count()
    body_txt = page.locator("body").inner_text()
    has_models = ("模型" in body_txt) or rows > 1
    check(f"[{ctx.target}] 模型通道区块可见", has_models)

    # 关闭（Esc / ×）
    try:
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
    except Exception:
        pass
    return {"opened": opened, "models_visible": has_models}
