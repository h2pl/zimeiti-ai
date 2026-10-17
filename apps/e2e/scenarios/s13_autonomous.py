"""S13 自主运营页：流程 CRUD + 步骤勾选 + 执行记录 + 运行状态卡（autonomous-observability）。

zimeiti 独有功能（Easel 无此页）——easel 侧断言「导航项不存在」，parity 按预期
差异 NOTE（见 parity.py S13 分支）。操作后列表异步刷新 → 统一轮询等待（沿用 S11 教训）。
立即执行按钮刻意不提供（会真实消耗额度，D3）——本场景不点它。
"""

TITLE = "自主运营页 运营流程"


def _wait_text(page, needle: str, timeout_s: int = 6) -> bool:
    """轮询等 app-layout 出现目标文案（列表异步刷新竞态，沿用 S11 教训）。"""
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
        absent = page.get_by_role("button", name="自主运营").count() == 0
        check(f"[{ctx.target}] 自主运营导航不存在（预期）", absent)
        return {"nav_present": False, "created": False, "steps_shown": False, "deleted": False}

    # 清场：保证空态起点
    import json as _json
    import urllib.request as _ur

    def api(method: str, path: str) -> dict:
        req = _ur.Request(f"{ctx.base}{path}", method=method, headers={"Origin": ctx.base})
        with _ur.urlopen(req, timeout=15) as r:
            return _json.loads(r.read())

    try:
        for f in api("GET", "/api/flows").get("flows", []):
            api("DELETE", f"/api/flows/{f['id']}")
    except Exception:
        pass

    click_nav(page, "自主运营")
    _wait_text(page, "还没有运营流程")
    check(f"[{ctx.target}] 自主运营页空态", _wait_text(page, "还没有运营流程"))

    # 新建：勾选步骤（默认已勾 discover/plan，加勾 produce）→ 保存
    page.get_by_role("button", name="+ 新建流程").first.click()
    page.wait_for_timeout(400)
    page.locator("#flow-name").fill("E2E 探针流程")
    page.get_by_label("创作（成稿/素材）", exact=False).check()
    page.wait_for_timeout(200)
    page.get_by_role("button", name="保存").first.click()
    created = _wait_text(page, "E2E 探针流程")
    check(f"[{ctx.target}] 流程出现在列表", created)

    txt = page.locator(".app-layout").inner_text()
    steps_shown = all(k in txt for k in ("发现", "选题", "创作")) and "每天 08:00" in txt
    check(f"[{ctx.target}] 步骤徽标与调度展示", steps_shown)

    # 运行状态卡（预算/待确认/熔断）可见
    status_card = "运行状态" in txt and "当日预算" in txt and "待确认" in txt
    check(f"[{ctx.target}] 运行状态卡可见", status_card)

    # 删除 → 回空态
    page.locator(".auto-card button[title='删除']").first.click()
    deleted = _wait_text(page, "还没有运营流程")
    check(f"[{ctx.target}] 删除后回空态", deleted)

    return {"nav_present": True, "created": created, "steps_shown": steps_shown,
            "status_card": status_card, "deleted": deleted}
