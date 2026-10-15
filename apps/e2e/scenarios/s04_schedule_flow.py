"""S4 选题→排期→内容日历：卡片「排期」一键入今日 → 日历出现该条目 → 清理。"""

TITLE = "选题排期到日历"

from pathlib import Path

IDEA_TITLE = "浏览器E2E-排期流"


def run(page, ctx, check) -> dict:
    from helpers import click_until_response, ensure_ready, goto_tool
    ensure_ready(page, ctx)

    # 准备：建一个专属选题（走 API，用户路径在排期动作上）
    ctx.api("POST", "/api/ideas", {"title": IDEA_TITLE})

    goto_tool(page, "选题库")
    # 看板出现轮询（慢端列表 GET 可达 3-8s）
    found = False
    for _ in range(25):
        if page.locator(".idea-card:visible", has_text=IDEA_TITLE).count() > 0:
            found = True
            break
        page.wait_for_timeout(500)
    card = page.locator(".idea-card:visible", has_text=IDEA_TITLE).first
    check(f"[{ctx.target}] 前置选题在看板", found)
    if not found:
        _cleanup(ctx)
        return {"scheduled": False, "calendar_shows": False}

    # 用户路径：点「排期」→ 立即 POST /api/schedule（今日）+ toast
    with page.expect_response(
        lambda r: "/api/schedule" in r.url and r.request.method == "POST", timeout=10000
    ) as ri_ctx:
        click_until_response(page, "POST", "/api/schedule",
                             lambda: card.get_by_role("button", name="排期").click(), tag="排期")
    status = ri_ctx.value.status if ri_ctx.value is not None else 0
    check(f"[{ctx.target}] 排期请求成功", status in (200, 201, 204), f"status={status}")

    # 日历出现条目（轮询：慢端日历 GET + 渲染可达 10s+）
    goto_tool(page, "内容日历")
    shows = False
    for _ in range(32):
        if page.get_by_text(IDEA_TITLE, exact=False).count() > 0:
            shows = True
            break
        page.wait_for_timeout(500)
    check(f"[{ctx.target}] 内容日历出现排期条目", shows, f"status={status}")
    if not shows:
        page.screenshot(path=str(Path(__file__).resolve().parents[1] / "_s04_fail.png"))

    _cleanup(ctx)
    return {"scheduled": found, "calendar_shows": shows}


def _cleanup(ctx) -> None:
    """清理排期条目与选题（API 直连，非用户路径断言）。"""
    try:
        items = ctx.api("GET", "/api/schedule") or []
        for it in items:
            if IDEA_TITLE in str(it.get("title", "")):
                ctx.api("DELETE", f"/api/schedule/{it['id']}")
    except Exception:
        pass
    try:
        ideas = ctx.api("GET", "/api/ideas") or []
        for it in ideas:
            if IDEA_TITLE in str(it.get("title", "")):
                ctx.api("DELETE", f"/api/ideas/{it['id']}")
    except Exception:
        pass
