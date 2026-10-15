"""S1 首屏与首次引导：骨架渲染 → 欢迎弹层（异步挂载）→ 跳过 → 进入工作台。

注意：本场景自加载页面、自带弹层断言，**不能**先跑 ensure_ready——
否则弹层被它先消费掉，本场景第二次 goto 时 localStorage 已有标记。
"""

TITLE = "首屏与首次引导"


def run(page, ctx, check) -> dict:
    from helpers import dismiss_onboarding

    page.goto(ctx.base, wait_until="load")
    page.wait_for_selector(".app-layout", timeout=20000)
    check(f"[{ctx.target}] 首屏应用骨架", page.locator(".app-layout").count() == 1)

    dismissed = dismiss_onboarding(page)
    check(f"[{ctx.target}] 欢迎弹层出现并可跳过", dismissed)

    # 跳过后遮罩卸载、工作台可达
    for _ in range(10):
        if page.locator(".overlay").count() == 0:
            break
        page.wait_for_timeout(300)
    dashboard = page.locator(".overlay").count() == 0
    check(f"[{ctx.target}] 跳过后进入工作台", dashboard)
    return {"skeleton": True, "onboarding_modal": dismissed, "dashboard": dashboard}
