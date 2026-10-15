"""S7 画像：列表 → 创建向导（mock LLM 增强）→ 出现在列表 → 清理。

向导四步：0 命名(必填) → 1 平台(可跳过) → 2 方向(必填) → 3 目标 → 提交异步创建。
按钮在必填项就绪前 disabled——推进器必须先补表单再点，且跳过禁用项。
"""

TITLE = "画像创建向导"

NAME = "E2E画像bot"


def run(page, ctx, check) -> dict:
    from helpers import ensure_ready, goto_page
    ensure_ready(page, ctx)

    _cleanup_created(ctx, set())  # 清历史残留（幂等）

    goto_page(page, "画像")
    page.wait_for_timeout(500)
    page.get_by_role("button", name="+ 新建画像").click()
    page.wait_for_timeout(400)
    wizard_open = page.get_by_placeholder("如：科技数码达人").count() > 0
    check(f"[{ctx.target}] 创建向导打开", wizard_open)

    before = _persona_names(ctx)
    created = False
    if wizard_open:
        page.get_by_placeholder("如：科技数码达人").fill(NAME)
        try:
            _advance_wizard(page)
        except Exception as e:
            check(f"[{ctx.target}] 向导推进异常", False, str(e)[:120])
        # 提交后异步创建（mock LLM 增强）→ 轮询「新增了画像」（名字可能被归一，用集合差集判断）
        for _ in range(40):  # ~20s
            if _persona_names(ctx) - before:
                created = True
                break
            page.wait_for_timeout(500)
    check(f"[{ctx.target}] 向导创建画像成功", created, f"before={sorted(before)}")

    # 关闭向导遮罩（先进去用 或 ×），否则遮住后续场景
    _close_wizard(page)

    deleted = _cleanup_created(ctx, before)
    check(f"[{ctx.target}] 画像已清理", deleted)
    return {"wizard_opened": wizard_open, "created": created, "deleted": deleted}


def _advance_wizard(page) -> None:
    direction = page.get_by_placeholder("如：平价护肤测评")
    goal = page.get_by_placeholder("涨粉 / 变现 / 个人品牌 / 引流私域")
    for _ in range(12):
        if direction.count() and not direction.input_value():
            direction.fill("E2E 自动化内容方向")
            page.wait_for_timeout(200)
        if goal.count() and not goal.input_value():
            goal.fill("涨粉")
            page.wait_for_timeout(200)
        btns = page.locator(".modal button, .overlay button")
        labels = [btns.nth(i).inner_text().strip() for i in range(btns.count())]
        if any("先进去用" in t for t in labels):
            return  # 创建完成页，交给 _close_wizard
        commit = next(
            (i for i, t in enumerate(labels) if ("生成" in t or t in ("完成", "创建画像")) and btns.nth(i).is_enabled()),
            None,
        )
        if commit is not None:
            btns.nth(commit).click()
            # 异步创建：等完成页出现（先进去用）或向导消失
            for _ in range(40):
                page.wait_for_timeout(500)
                cur = [page.locator(".modal button, .overlay button").nth(i).inner_text().strip()
                       for i in range(page.locator(".modal button, .overlay button").count())]
                if any("先进去用" in t for t in cur) or page.locator(".modal").count() == 0:
                    return
            return
        nxt = next((i for i, t in enumerate(labels) if t == "下一步" and btns.nth(i).is_enabled()), None)
        if nxt is None:
            page.wait_for_timeout(400)
            continue
        btns.nth(nxt).click()
        page.wait_for_timeout(400)


def _close_wizard(page) -> None:
    try:
        btns = page.locator(".modal button, .overlay button")
        labels = [btns.nth(i).inner_text().strip() for i in range(btns.count())]
        done = next((i for i, t in enumerate(labels) if "先进去用" in t), None)
        if done is not None:
            btns.nth(done).click()
            page.wait_for_timeout(500)
        elif page.locator(".modal").count():
            page.locator(".modal button", has_text="×").first.click()
            page.wait_for_timeout(400)
    except Exception:
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)


def _persona_names(ctx) -> set:
    try:
        return {p.get("name") for p in (ctx.api("GET", "/api/personas") or []) if p.get("name")}
    except Exception:
        return set()


def _cleanup_created(ctx, before: set) -> bool:
    """删除本次新增的画像（差集判定），顺带清历史残留。

    路由是单数 /api/persona/{name}；中文名必须 quote（urllib 不自动编码非 ASCII 路径）。
    """
    import urllib.parse

    ok = True
    try:
        current = _persona_names(ctx)
        targets = (current - before) | {n for n in current if "E2E画像" in str(n)}
        for n in targets:
            ctx.api("DELETE", "/api/persona/" + urllib.parse.quote(str(n)))
        ok = not (_persona_names(ctx) & targets)
    except Exception:
        ok = False
    return ok
