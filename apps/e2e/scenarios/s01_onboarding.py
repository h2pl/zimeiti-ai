"""S1 首屏与首次引导：骨架渲染 → 欢迎弹层（异步挂载）→ 跳过 → 进入工作台。

注意：本场景自加载页面、自带弹层断言，**不能**先跑 ensure_ready——
否则弹层被它先消费掉，本场景第二次 goto 时 localStorage 已有标记。

弹层显示条件是「画像数为 0」（产品逻辑：已有画像不需要推荐配置）。zimeiti 侧
数据根可能带真实画像（如 江小湖）——此时引导**正当缺席**，场景按状态自适应：
断言「无弹层且工作台直达」，parity 对该状态记 NOTE（见 parity.py S01 分支）。
"""

TITLE = "首屏与首次引导"


def run(page, ctx, check) -> dict:
    import json as _json
    import urllib.request as _ur

    from helpers import dismiss_onboarding

    # 先探画像状态（决定弹层是否应出现）。/api/personas 返回裸列表。
    personas_present = False
    if ctx.target == "zimeiti":
        try:
            with _ur.urlopen(_ur.Request(f"{ctx.base}/api/personas", headers={"Origin": ctx.base}), timeout=10) as r:
                data = _json.loads(r.read())
                items = data.get("personas") if isinstance(data, dict) else data
                personas_present = len(items or []) > 0
        except Exception:
            pass

    page.goto(ctx.base, wait_until="load")
    page.wait_for_selector(".app-layout", timeout=20000)
    check(f"[{ctx.target}] 首屏应用骨架", page.locator(".app-layout").count() == 1)

    dismissed = dismiss_onboarding(page)
    if personas_present:
        # 已有画像：弹层正当缺席，直接进工作台即通过
        ok = not dismissed and page.locator(".overlay").count() == 0
        check(f"[{ctx.target}] 已有画像 → 无首启引导，直达工作台", ok)
    else:
        check(f"[{ctx.target}] 欢迎弹层出现并可跳过", dismissed)

    # 遮罩卸载、工作台可达
    for _ in range(10):
        if page.locator(".overlay").count() == 0:
            break
        page.wait_for_timeout(300)
    dashboard = page.locator(".overlay").count() == 0
    check(f"[{ctx.target}] 跳过后进入工作台", dashboard)
    return {"skeleton": True, "onboarding_modal": dismissed,
            "dashboard": dashboard, "personas_present": personas_present}
