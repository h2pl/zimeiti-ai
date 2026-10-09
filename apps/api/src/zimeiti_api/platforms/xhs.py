"""小红书发布（Task 6.2，宪法原则 III：风控护栏）。

框架与选择器集中管理（平台改版只改 SELECTORS）；
登录态：首跑扫码一次持久化 storage_state，后续复用；
频控/白名单在 publisher 执行器层强制，本模块只做单次动作。
读回对账：发布后到创作者中心读回笔记列表，含标题即 verified。
"""

from pathlib import Path
from typing import Any

SELECTORS: dict[str, str] = {
    "creator_url": "https://creator.xiaohongshu.com/publish/publish",
    "note_list_url": "https://creator.xiaohongshu.com/publish/note",
    "title_input": "#title-textarea",
    "content_editor": "#post-textarea",
    "publish_button": ".publishBtn",
    "note_titles": ".note-item .title",
}


def parse_readback(note_titles: list[str], title: str) -> str:
    """读回对账纯函数：创作者中心笔记列表含标题 → verified，否则 unverified。"""
    return "verified" if title in note_titles else "unverified"


class XhsPublisher:
    """小红书发布器。page 可注入（测试用 FakePage），默认内部启动 Playwright。"""

    def __init__(
        self,
        storage_state: str = "outputs/_login/xhs_state.json",
        selectors: dict[str, str] | None = None,
    ):
        self.storage_state = storage_state
        self.selectors = selectors or SELECTORS

    def publish(self, draft: Any, page: Any = None) -> str:
        """发布一篇图文草稿，返回 submitted（真实结果以 readback 为准）。"""
        page = page or self._open_page()
        sel = self.selectors
        page.goto(sel["creator_url"])
        page.fill(sel["title_input"], draft.title)
        page.fill(sel["content_editor"], draft.body)
        page.click(sel["publish_button"])
        return "submitted"

    def readback(self, title: str, page: Any = None) -> str:
        """读回创作者中心笔记列表做对账。"""
        page = page or self._open_page()
        sel = self.selectors
        page.goto(sel["note_list_url"])
        titles = [el.text_content() for el in page.query_selector_all(sel["note_titles"])]
        return parse_readback(titles, title)

    def _open_page(self) -> Any:
        """真实浏览器打开（登录态持久化）。仅生产路径使用，单测注入 FakePage。"""
        from playwright.sync_api import sync_playwright

        pw = sync_playwright().start()
        browser = pw.chromium.launch(headless=False)
        context = browser.new_context()
        if Path(self.storage_state).exists():
            context = browser.new_context(storage_state=self.storage_state)
        page = context.new_page()
        page.on("close", lambda _: (context.close(), browser.close(), pw.stop()))
        return page
