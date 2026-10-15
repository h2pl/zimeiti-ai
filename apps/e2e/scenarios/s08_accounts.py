"""S8 账号页：平台卡片渲染 + whoami 状态（GET /api/accounts/*/whoami 由页面触发）。"""

TITLE = "账号页 whoami"


def run(page, ctx, check) -> dict:
    from helpers import ensure_ready, goto_page
    ensure_ready(page, ctx)

    requests_seen: list[str] = []
    page.on(
        "request",
        lambda r: requests_seen.append(r.url) if "/api/accounts/" in r.url and "whoami" in r.url else None,
    )
    goto_page(page, "账号")
    # whoami 并发校验：轮询等请求发出（Easel 慢端单请求 3-8s）
    whoami_fired = False
    for _ in range(30):
        if requests_seen:
            whoami_fired = True
            break
        page.wait_for_timeout(500)
    cards = page.locator(".account-avatar, .account-card, [class*='account']").count()
    ok = cards > 0
    check(f"[{ctx.target}] 账号页平台卡片渲染", ok, f"cards={cards}")
    check(f"[{ctx.target}] whoami 校验请求已发出", whoami_fired, f"n={len(requests_seen)}")
    return {"cards": ok, "whoami_fired": whoami_fired}
