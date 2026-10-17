"""S12 用量可视化：工作台用量卡片 + 设置面板用量明细（ops-console-ui）。

zimeiti 独有功能——easel 侧断言「工作台无用量卡片」（预期差异，parity NOTE）。
记忆系统与 exec_script 为 agent 行为层（无独立 UI）→ evals 行为层覆盖，
见 COVERAGE_MAP 登记。
"""

TITLE = "用量可视化"


def run(page, ctx, check) -> dict:
    from helpers import ensure_ready, click_nav

    ensure_ready(page, ctx)

    if ctx.target == "easel":
        page.wait_for_timeout(600)
        txt = page.locator(".app-layout").inner_text()
        absent = "用量" not in txt
        check(f"[{ctx.target}] 工作台无用量卡片（预期）", absent)
        return {"dash_card": False, "settings_usage": False}

    click_nav(page, "工作台")
    page.wait_for_timeout(1200)
    txt = page.locator(".app-layout").inner_text()
    # 卡片三种合法形态：空态 / token 视图 / 金额视图（已知模型折算后不再显示 token 字样）
    dash_card = "用量" in txt and (
        "暂无用量数据" in txt or "token" in txt or "$" in txt or "≈" in txt
    )
    check(f"[{ctx.target}] 工作台用量卡片", dash_card)

    # 设置面板：用量明细区（齿轮 → 模型通道分区含用量 + 环境变量只读说明）
    gear = page.locator("[class*='settings'], button[title*='设置'], .icon-gear").first
    if gear.count() == 0:
        gear = page.get_by_role("button").filter(has_text="").last
    opened = False
    try:
        page.keyboard.press("Escape")
        # 侧栏底部齿轮按钮（settingsIcons）
        btn = page.locator("button:has(svg)").last
        for cand in page.locator("button").all():
            cls = cand.get_attribute("class") or ""
            if "gear" in cls or "settings" in cls:
                cand.click(); opened = True; break
        if not opened:
            # 兜底：找「设置」文字
            s = page.get_by_text("设置", exact=True)
            if s.count():
                s.first.click(); opened = True
    except Exception:
        pass
    page.wait_for_timeout(1000)
    stxt = page.locator("body").inner_text()
    settings_usage = ("用量" in stxt) and (
        "部分模型未计价" in stxt or "token" in stxt or "$" in stxt or "暂无用量数据" in stxt
    )
    check(f"[{ctx.target}] 设置面板用量明细", settings_usage and opened, f"opened={opened}")

    return {"dash_card": dash_card, "settings_usage": bool(settings_usage and opened)}
