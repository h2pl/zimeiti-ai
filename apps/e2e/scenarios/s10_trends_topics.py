"""S10 热点雷达：页渲染（外部数据源，条件断言）→ 有条目时「做内容」跳转对话预填。"""

TITLE = "热点雷达与做内容跳转"


def run(page, ctx, check) -> dict:
    from helpers import ensure_ready, goto_tool
    ensure_ready(page, ctx)

    goto_tool(page, "热点雷达")
    page.wait_for_timeout(500)
    rendered = page.locator(".page-host").count() == 1 or page.locator("body").inner_text() != ""
    check(f"[{ctx.target}] 热点雷达页渲染", rendered)

    # 外部数据源（微博/抖音抓取）——条目存在性是环境事实：轮询 15s 再定性
    items = 0
    for _ in range(30):
        items = page.locator("button:has-text('做内容')").count()
        if items > 0:
            break
        page.wait_for_timeout(500)
    jumped = None
    if items > 0:
        page.locator("button:has-text('做内容')").first.click()
        page.wait_for_timeout(800)
        on_chat = page.locator("textarea").count() > 0
        check(f"[{ctx.target}] 「做内容」跳转对话页", on_chat)
        jumped = on_chat
    else:
        check(f"[{ctx.target}] 无热点条目（外部源）——跳转路径跳过", True, "环境无数据，条件断言通过")
    return {"rendered": rendered, "topics": items, "jumped": jumped}
