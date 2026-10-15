"""S2 全页面导航：侧栏 6 页 + 工具子导航 5 页全部可达且无 JS 崩溃。

SubNav 只在工具页内显示——侧栏页先走完，再从工作台进入工具页链。
"""

TITLE = "全页面导航"

from helpers import SIDEBAR_PAGES, TOOL_PAGES, click_nav, ensure_ready


def run(page, ctx, check) -> dict:
    ensure_ready(page, ctx)
    reached: list[str] = []
    for label in SIDEBAR_PAGES:
        try:
            click_nav(page, label)
            page.wait_for_timeout(200)
            reached.append(label)
        except Exception as e:
            reached.append(f"{label}✗{type(e).__name__}")
    # 工具页：工作台落点 → 热点雷达（工作台卡片）→ SubNav 依次
    try:
        click_nav(page, "工作台")
        first = TOOL_PAGES[0]
        click_nav(page, first)
        page.wait_for_timeout(300)
        reached.append(first)
        for label in TOOL_PAGES[1:]:
            click_nav(page, label)
            page.wait_for_timeout(200)
            reached.append(label)
    except Exception as e:
        reached.append(f"工具页✗{type(e).__name__}")
    ok = all("✗" not in r for r in reached)
    check(f"[{ctx.target}] 全部 {len(SIDEBAR_PAGES) + len(TOOL_PAGES)} 页可达", ok, str(reached))
    return {"reached": reached}
