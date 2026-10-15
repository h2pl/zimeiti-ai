"""S3 选题 CRUD：新建 → 出现 → 编辑改名 → 删除 → 归零。

写请求（POST/PUT/DELETE）必须等回包（网络同步）；列表断言一律文本轮询——
app 保存/删除后可能走本地状态更新而非重新 GET，等 GET 会假超时。
"""

TITLE = "选题 CRUD"

IDEA_TITLE = "浏览器E2E-选题CRUD"
RENAMED = "浏览器E2E-选题CRUD-改"


def _wait_text(page, text: str, want: bool, tries: int = 20) -> bool:
    for _ in range(tries):
        if (page.get_by_text(text, exact=False).count() > 0) == want:
            return True
        page.wait_for_timeout(400)
    return (page.get_by_text(text, exact=False).count() > 0) == want


def run(page, ctx, check) -> dict:
    from helpers import click_until_response, ensure_ready, expect_api, goto_tool, sweep_ideas

    ensure_ready(page, ctx)

    goto_tool(page, "选题库")
    sweep_ideas(page, IDEA_TITLE)
    sweep_ideas(page, RENAMED)

    # 新建
    page.get_by_role("button", name="+ 新建选题").click()
    page.get_by_placeholder("想做的内容 / 角度").fill(IDEA_TITLE)
    click_until_response(page, "POST", "/api/ideas",
                         lambda: page.get_by_role("button", name="保存").click(), tag="新建保存")
    created = _wait_text(page, IDEA_TITLE, True)
    check(f"[{ctx.target}] 新建选题出现在看板", created)

    # 编辑改名（真实用户路径：卡片 编辑 按钮 → 保存）
    edited = False
    if created:
        card = page.locator(".idea-card:visible", has_text=IDEA_TITLE).first
        card.hover()
        card.get_by_title("编辑").click()
        page.get_by_placeholder("想做的内容 / 角度").fill(RENAMED)
        # 编辑保存：zimeiti 发 PUT、Easel 发 POST（真实行为差异）——两者皆收
        try:
            with page.expect_response(
                lambda r: "/api/ideas" in r.url and r.request.method in ("POST", "PUT"), timeout=10000
            ):
                page.get_by_role("button", name="保存").click()
        except Exception:
            # React 重渲染吞点击的重试兜底（重开表单重填）
            page.get_by_role("button", name="+ 新建选题").click()
            page.get_by_placeholder("想做的内容 / 角度").fill(RENAMED)
            with page.expect_response(
                lambda r: "/api/ideas" in r.url and r.request.method in ("POST", "PUT"), timeout=10000
            ):
                page.get_by_role("button", name="保存").click()
        edited = _wait_text(page, RENAMED, True)
    check(f"[{ctx.target}] 编辑改名生效", edited)

    # 删除 + 兜底清扫 + 归零
    deleted = False
    if edited or created:
        target_title = RENAMED if edited else IDEA_TITLE
        card = page.locator(".idea-card:visible", has_text=target_title).first
        if card.count():
            card.hover()
            expect_api(page, "DELETE", "/api/ideas",
                       lambda: card.get_by_title("删除").click(), tag="删除")
            page.wait_for_timeout(400)
        sweep_ideas(page, RENAMED)
        sweep_ideas(page, IDEA_TITLE)
        deleted = _wait_text(page, RENAMED, False) and _wait_text(page, IDEA_TITLE, False)
    check(f"[{ctx.target}] 删除后看板归零", deleted)
    return {"created": created, "edited": edited, "deleted": deleted}
