"""浏览器交互原语：全部来自单文件版三轮调试沉淀的稳定形态。

- 弹层/骨架异步挂载 → 轮询等待
- 旧构建侧栏项可能是 div → role=button 优先、text 兜底
- 写操作后必须等「变更请求回包 + 列表 GET 回包」，不靠固定 sleep
"""

from __future__ import annotations

import time
from collections.abc import Callable
from contextlib import contextmanager

from playwright.sync_api import Page

SIDEBAR_PAGES = ["工作台", "对话", "技能库", "内容库", "账号", "画像"]
TOOL_PAGES = ["热点雷达", "选题库", "内容日历", "发布中心", "爆款拆解"]
ALL_NAV = SIDEBAR_PAGES + TOOL_PAGES


def click_nav(page: Page, label: str, timeout: int = 15000) -> None:
    """导航点击：role=button 优先（新构建），text 兜底（旧构建 div 项）。"""
    try:
        page.get_by_role("button", name=label).first.click(timeout=3000)
    except Exception:
        page.get_by_text(label, exact=True).first.click(timeout=timeout)


def dismiss_onboarding(page: Page, timeout_ms: int = 30000) -> bool:
    """欢迎弹层在 /api/status 返回后才挂载——轮询等待后点「先用通用模式」。"""
    dismiss = page.get_by_role("button", name="先用通用模式")
    deadline = time.time() + timeout_ms / 1000
    while time.time() < deadline:
        if dismiss.count() > 0:
            dismiss.first.click()
            page.wait_for_timeout(400)  # 等 overlay 卸载
            return True
        page.wait_for_timeout(300)
    return False


def ensure_ready(page: Page, ctx=None) -> None:
    """场景自足：没有骨架就加载；有遮罩（首访弹层/残留弹层）就先处理掉。

    单独跑某场景时没有 S1 打底——不做这一步，后续点击会被 overlay 挡死。
    """
    if page.locator(".app-layout").count() == 0:
        if ctx is None:
            return
        page.goto(ctx.base, wait_until="load")
        page.wait_for_selector(".app-layout", timeout=20000)
        dismiss_onboarding(page)
        return
    if page.locator(".overlay").count():
        d = page.get_by_role("button", name="先用通用模式")
        if d.count():
            d.first.click()
            page.wait_for_timeout(400)


def goto_page(page: Page, label: str) -> None:
    """侧栏直达页（工作台/对话/技能库/内容库/账号/画像）。"""
    click_nav(page, label)
    page.wait_for_timeout(200)


def goto_tool(page: Page, tool: str) -> None:
    """工具页（SubNav 仅在工具页内显示）：工作台 → 热点雷达卡片 → SubNav 项。"""
    click_nav(page, "工作台")
    click_nav(page, "热点雷达")
    if tool != "热点雷达":
        click_nav(page, tool)
    page.wait_for_timeout(800)  # 等列表 GET 完成，防保存 POST 与刷新 GET 竞态


@contextmanager
def api_response(page: Page, method: str, url_part: str, timeout: int = 10000):
    """等待一个匹配 method+url 片段的响应（网络同步原语）。"""
    with page.expect_response(
        lambda r: url_part in r.url and r.request.method == method, timeout=timeout
    ) as ri:
        yield ri


def expect_api(page: Page, method: str, url_part: str, action: Callable[[], None],
               timeout: int = 10000, tag: str = "") -> None:
    """带标签的网络同步：等 method+url 回包期间执行 action；失败时报出具体步骤。"""
    try:
        with page.expect_response(
            lambda r: url_part in r.url and r.request.method == method, timeout=timeout
        ):
            action()
    except Exception as e:
        raise RuntimeError(f"[{tag or url_part}] {method} {url_part} 等待回包失败: {e}") from e


def click_until_response(page: Page, method: str, url_part: str, click: Callable[[], None],
                         tries: int = 2, timeout: int = 8000, tag: str = "") -> None:
    """点击直到见到目标回包——React 重渲染可能吞掉单击事件（保存 disabled 态
    恰好放行的瞬间被换节点），重试一次兜底。代价：极端情况下可能重复提交，
    由各场景的标题清扫兜底。"""
    last: Exception | None = None
    for _ in range(tries):
        try:
            with page.expect_response(
                lambda r: url_part in r.url and r.request.method == method, timeout=timeout
            ):
                click()
            return
        except Exception as e:
            last = e
            page.wait_for_timeout(300)
    raise RuntimeError(f"[{tag}] {tries} 次点击均未见 {method} {url_part}: {last}")


def wait_api_then_continue(page: Page, action: Callable[[], None], *pairs: tuple[str, str], timeout: int = 10000) -> None:
    """action 触发后依次等待多段响应（如 POST 后紧跟的列表 GET）。"""
    if not pairs:
        action()
        return
    with api_response(page, *pairs[0], timeout=timeout):
        if len(pairs) == 1:
            action()
        else:
            wait_api_then_continue(page, action, *pairs[1:], timeout=timeout)


def poll(fn: Callable[[], bool], timeout_s: float = 8.0, interval: float = 0.3) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            if fn():
                return True
        except Exception:
            pass
        page_wait(interval)
    return False


def page_wait(seconds: float) -> None:
    time.sleep(seconds)


def sweep_ideas(page: Page, title: str, api_call=None) -> None:
    """清扫历次运行残留的同名选题（删除按钮 hover 才渲染）。

    等 DELETE 回包即可：app 删除后未必重新 GET（可能走本地状态更新），
    等 GET 会假超时；卡片消失由外层轮询兜底。
    """
    for _ in range(12):
        cards = page.locator(".idea-card:visible", has_text=title)
        if cards.count() == 0:
            return
        cards.first.hover()
        with api_response(page, "DELETE", "/api/ideas", timeout=8000):
            cards.first.get_by_title("删除").click()
        page.wait_for_timeout(400)
