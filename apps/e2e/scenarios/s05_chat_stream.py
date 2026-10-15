"""S5 对话全链路：发送→SSE 流式（mock LLM）→回复渲染→完成；新建/切换/删除会话。

zimeiti 端回复以 MOCK: 前缀确定性返回；Easel 端走其真实配置——
两端只比较结构级事实（流式开始/完成/有回复），reply_kind 差异仅 NOTE。
"""

TITLE = "对话全链路与会话管理"

MSG = "浏览器 E2E 探活消息"


def run(page, ctx, check) -> dict:
    from helpers import ensure_ready, goto_page
    ensure_ready(page, ctx)

    goto_page(page, "对话")
    box = page.locator("textarea").first
    box.fill(MSG)
    box.press("Enter")

    hint = page.locator(".composer-hint")
    started = False
    for _ in range(20):
        if "生成中" in (hint.inner_text() or ""):
            started = True
            break
        page.wait_for_timeout(500)
    check(f"[{ctx.target}] 流式开始", started)

    # 完成：hint 恢复 或 线程文本停止增长（双信号，防真实模型长回复）
    done = False
    last_len, stall = -1, 0
    for _ in range(90):
        if started and "生成中" not in (hint.inner_text() or ""):
            done = True
            break
        page.wait_for_timeout(2000)
        txt = _thread_text(page)
        if len(txt) == last_len:
            stall += 1
            if stall >= 2 and len(txt) > len(MSG) + 10:
                done = True
                break
        else:
            stall = 0
        last_len = len(txt)
    thread_txt = _thread_text(page)
    has_reply = done and len(thread_txt.strip()) > 0
    reply_kind = "mock" if "MOCK:" in thread_txt else ("real" if has_reply else "none")
    check(f"[{ctx.target}] 流式完成且有回复", has_reply, f"kind={reply_kind}")

    # 会话管理：新建 → 列表变化 → 删除（confirm 由 page.on(dialog) 自动接受）
    before = _session_count(page)
    page.get_by_role("button", name="新对话").first.click()
    page.wait_for_timeout(500)
    after_new = _session_count(page)
    new_ok = after_new > before
    check(f"[{ctx.target}] 新建会话", new_ok)

    deleted = False
    if new_ok:
        # 删掉刚建的（列表里最后一个会话项），操作按钮 hover 才渲染
        item = page.locator(".session-item:visible").last
        item.hover()
        item.locator("button[title='删除']").click()
        page.wait_for_timeout(800)
        deleted = _session_count(page) == after_new - 1
    check(f"[{ctx.target}] 删除会话", deleted)

    return {
        "started": started,
        "completed": done,
        "has_reply": has_reply,
        "reply_kind": reply_kind,
        "new_session": new_ok,
        "session_deleted": deleted,
    }


def _thread_text(page) -> str:
    loc = page.locator(".chat-messages")
    return loc.inner_text() if loc.count() else ""


def _session_count(page) -> int:
    for sel in (".session-item", ".conv-item", ".session-row"):
        n = page.locator(sel).count()
        if n:
            return n
    return 0
