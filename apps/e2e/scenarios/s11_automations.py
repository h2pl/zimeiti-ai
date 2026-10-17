"""S11 自动化页：定时任务 CRUD + 立即执行 + 执行记录（ops-console-ui）。

zimeiti 独有功能（Easel 无此页）——easel 侧断言「导航项不存在」，
parity 按预期差异 NOTE（见 parity.py S11 分支）。

操作后状态经异步 load() 刷新，固定 sleep 有竞态（实测偶发）→ 统一用轮询等待。
"""

TITLE = "自动化页 定时任务"


def _wait_text(page, needle: str, timeout_s: int = 6) -> bool:
    """轮询等 app-layout 出现目标文案（应对列表异步刷新竞态）。"""
    import time

    dl = time.time() + timeout_s
    while time.time() < dl:
        if needle in page.locator(".app-layout").inner_text():
            return True
        page.wait_for_timeout(300)
    return False


def run(page, ctx, check) -> dict:
    from helpers import ensure_ready, click_nav

    ensure_ready(page, ctx)

    if ctx.target == "easel":
        # Easel 无自动化功能：断言侧栏确实没有该项（结构事实，parity 记 NOTE）
        absent = page.get_by_role("button", name="自动化").count() == 0
        check(f"[{ctx.target}] 自动化导航不存在（预期）", absent)
        return {"nav_present": False, "created": False, "run_record": False, "deleted": False}

    # 清场：保证空态起点（确定性）
    try:
        items = ctx.api("GET", "/api/automations").get("automations", [])
        for a in items:
            ctx.api("DELETE", f"/api/automations/{a['id']}")
    except Exception:
        pass

    click_nav(page, "自动化")
    _wait_text(page, "还没有定时任务")
    empty_ok = _wait_text(page, "还没有定时任务")
    check(f"[{ctx.target}] 自动化页空态", empty_ok)

    # 新建
    page.get_by_role("button", name="+ 新建任务").click()
    page.wait_for_timeout(300)
    page.locator("input[placeholder='如：每日出稿']").fill("E2E 探针任务")
    page.get_by_role("button", name="保存").click()
    created = _wait_text(page, "E2E 探针任务") and _wait_text(page, "下次")
    check(f"[{ctx.target}] 新建任务出现在列表", created)

    # 立即执行 → 执行记录出现（prompt 类型走 mock LLM，快）
    page.get_by_role("button", name="立即执行").first.click()
    run_record = any(_wait_text(page, t, 4) for t in ("最近执行", "执行中", "成功", "失败"))
    check(f"[{ctx.target}] 立即执行产生执行记录", run_record)

    # 停用
    page.get_by_role("button", name="停用").first.click()
    disabled = _wait_text(page, "已停用")
    check(f"[{ctx.target}] 停用生效", disabled)

    # 删除 → 回空态
    page.locator(".auto-card button[title='删除']").first.click()
    deleted = _wait_text(page, "还没有定时任务")
    check(f"[{ctx.target}] 删除后回空态", deleted)

    return {"nav_present": True, "created": created, "run_record": run_record,
            "disabled": disabled, "deleted": deleted}
