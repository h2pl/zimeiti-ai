"""小红书发布（Task 6.2，宪法原则 III：风控护栏）。

生产路线：DOM 自动化创作者中心，复用开源 aki66938/xhs-toolkit v1.3.0
（MIT，https://github.com/aki66938/xhs-toolkit）实测验证的选择器与流程，
移植到本项目既有 Playwright 栈。支持存草稿/发布二态。

为何不用 API 逆向路线（A3 走查实测记录）：edith 域对外部签名一律风控拒绝
（-100 无登录信息 / -1 签名失败，x-s/x-t、x-s-common、页内 fetch 均试过），
creator 域 /web_api/sns/v2/note 返回 404；且 creator 假阳性 success（data 空，
平台实际未建笔记）。站点自己的签名/风控只信真实前端环境——DOM 自动化即复用
站点自身逻辑，不再逆向。

登录态：首跑扫码一次持久化 storage_state，后续复用；
频控/白名单在 publisher 执行器层强制，本模块只做单次动作。
读回对账：笔记管理页（草稿 tab）正文含标题 → verified。
"""

import struct
import zlib
from pathlib import Path
from typing import Any

from playwright.sync_api import TimeoutError, sync_playwright

# 选择器与 URL 集中管理（来源：xhs-toolkit src/xiaohongshu/constants.py 实测值），
# 平台改版只改这里
SELECTORS: dict[str, str] = {
    "publish_page": "https://creator.xiaohongshu.com/publish/publish?from=menu",
    "login_url": "https://creator.xiaohongshu.com/login",
    "creator_tab": ".creator-tab",  # 发布页默认落上传视频 tab，必须切「上传图文」（A3 实测）
    "file_input": "input[type='file']",
    "title_input": "[placeholder*='标题']",
    "title_input_alt": ".d-text",
    "content_editor": ".tiptap.ProseMirror",  # 正文富文本编辑器（Tiptap，A3 实测；
    # 旧版 Quill .ql-editor 已被站点替换，xhs-toolkit 的 .ql-editor 选择器过时）
    # 发布按钮（A3 实测新版按钮文本为「发布笔记」，.publishBtn 为旧版类名兜底）
    "publish_button": "text=发布笔记",
    "publish_button_alt": ".publishBtn",
    "visibility_entry": "text=公开可见",
    "visibility_private": "text=仅自己可见",
    "note_list_url": "https://creator.xiaohongshu.com/new/note-manager",  # 旧 /publish/note 已 404（A3 实测）
    "draft_tab": "text=草稿",
}

# 平台硬约束（xiaobei/AiToEarn 实测对齐）
XHS_TITLE_LIMIT = 20
XHS_DESC_LIMIT = 1000


def parse_readback(note_titles: list[str], title: str) -> str:
    """读回对账纯函数：页面列表含标题 → verified，否则 unverified。"""
    return "verified" if title in note_titles else "unverified"


def make_cover_png(path: str | Path, width: int = 1080, height: int = 1440) -> Path:
    """纯标准库生成 3:4 纯色封面 PNG（图文笔记至少需要 1 张图）。

    参考: scripts/walkthrough_a3_gzh.py make_png（本项目既有实现）
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    rgb = (255, 96, 108)  # 小红书主题红
    raw = b"".join(b"\x00" + bytes(rgb) * width for _ in range(height))
    p.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )
    return p


class XhsPublisher:
    """小红书发布器（DOM 自动化）。page 可注入（测试用 FakePage）。

    存草稿（publish_draft）与发布（publish）共用填表流程，仅末端按钮不同；
    默认内部启动 Playwright 并复用持久化登录态。
    """

    def __init__(self, storage_state: str | None = None, selectors: dict[str, str] | None = None):
        if storage_state is None:
            from zimeiti_api.config import LOGIN_STATE_PATH

            storage_state = str(LOGIN_STATE_PATH)
        self.storage_state = storage_state
        self.selectors = selectors or SELECTORS

    # ─── 发布/存草稿 ────────────────────────────────────────────────

    def publish_draft(
        self,
        draft: Any,
        page: Any = None,
        cover_path: str | None = None,
        debug_dir: str | None = None,
    ) -> str:
        """私密发布（仅自己可见）——宪法 I 的 xhs 落地形态，返回 submitted_private。

        A3 实测：创作者中心 web 端图文模式没有「存草稿」按钮（App 草稿箱不开放
        web API/DOM），「仅自己可见」发布是「先暂存、人工确认后再公开」的最接近
        形态；公开化由人工在 App/后台操作（MUST NOT 由 agent 私自公开）。

        page 只在此处开一次并传给 _fill_note——若各自开 Playwright 实例，
        第二个实例会在第一个的 greenlet 循环内启动而报 asyncio 冲突（A3 实测）。
        """
        page = page or self._open_page()
        self._fill_note(draft, page=page, cover_path=cover_path, debug_dir=debug_dir)
        sel = self.selectors
        if debug_dir:
            Path(debug_dir).mkdir(parents=True, exist_ok=True)
            (Path(debug_dir) / "publish_page.html").write_text(page.content(), encoding="utf-8")
        # 可见性：公开可见 → 仅自己可见
        for el in page.locator(sel["visibility_entry"]).all():
            try:
                if el.is_visible():
                    el.click()
                    break
            except Exception:  # noqa: BLE001  # nosec B112 - 隐藏重复项容错
                continue
        page.wait_for_timeout(1_000)
        page.locator(sel["visibility_private"]).first.click()
        # 发布
        clicked = False
        for selector in (sel["publish_button"], sel["publish_button_alt"]):
            try:
                page.locator(selector).first.click(timeout=10_000)
                clicked = True
                break
            except Exception:  # noqa: BLE001  # nosec B112 - 多选择器轮询容错
                continue
        if not clicked:
            raise RuntimeError("未找到发布按钮（站点可能改版，检查 SELECTORS）")
        page.wait_for_timeout(5_000)
        return "submitted_private"

    def publish(
        self,
        draft: Any,
        page: Any = None,
        cover_path: str | None = None,
        debug_dir: str | None = None,
    ) -> str:
        """正式发布图文笔记，返回 submitted（真实结果以 readback 为准）。"""
        page = page or self._open_page()
        self._fill_note(draft, page=page, cover_path=cover_path, debug_dir=debug_dir)
        sel = self.selectors
        clicked = False
        for selector in (sel["publish_button"], sel["publish_button_alt"]):
            try:
                page.locator(selector).first.click(timeout=10_000)
                clicked = True
                break
            except Exception:  # noqa: BLE001  # nosec B112 - 多选择器轮询（xhs-toolkit 同款容错）
                continue
        if not clicked:
            raise RuntimeError("未找到发布按钮（站点可能改版，检查 SELECTORS）")
        page.wait_for_timeout(5_000)
        return "submitted"

    def _fill_note(
        self,
        draft: Any,
        page: Any = None,
        cover_path: str | None = None,
        debug_dir: str | None = None,
    ) -> None:
        """填表流程（xhs-toolkit 实测顺序）：上传封面 → 等编辑器 → 标题 → 正文。

        draft：XhsDraft 或 dict（发布审批进程从 drafts.json 读回的是 dict）。
        """
        title = draft["title"] if isinstance(draft, dict) else draft.title
        body = draft["body"] if isinstance(draft, dict) else draft.body
        if page is None:
            # 由 publish/publish_draft 统一开启传入，避免重复开 Playwright 实例
            raise RuntimeError("page 未注入：请经由 publish/publish_draft 调用")
        sel = self.selectors

        page.goto(sel["publish_page"])
        page.wait_for_selector(sel["creator_tab"], timeout=20_000)

        # 0. 切到「上传图文」tab（发布页默认落上传视频 tab，A3 走查实测；
        #    tab 有多个隐藏重复项，必须点可见的那个；SPA 渲染需重试）
        switched = False
        for _ in range(5):
            for tab in page.locator(sel["creator_tab"]).all():
                try:
                    if tab.is_visible() and "上传图文" in tab.inner_text():
                        tab.click()
                        switched = True
                        break
                except Exception:  # noqa: BLE001  # nosec B112 - 隐藏重复项点击容错
                    continue
            if switched:
                break
            page.wait_for_timeout(1_000)
        if not switched:
            raise RuntimeError("未找到可见的「上传图文」tab（站点可能改版，检查 SELECTORS）")

        # 1. 封面上传（图文笔记至少 1 张图；默认生成 3:4 纯色 PNG）
        cover = (
            Path(cover_path)
            if cover_path
            else make_cover_png(Path("data/outputs/xhs-main") / "cover.png")
        )
        # 取图片 file input（accept 为扩展名列表 .jpg/.jpeg/.png/.webp；A3 实测
        # 上传控件本身隐藏 visible=False 但 set_input_files 可用；视频 input 的
        # accept 是 .mp4 等视频扩展名）
        _IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp")
        file_input = None
        deadline = 20_000
        waited = 0
        while file_input is None and waited < deadline:
            for inp in page.locator(sel["file_input"]).all():
                try:
                    accept = (inp.get_attribute("accept") or "").lower()
                    if any(ext in accept for ext in _IMAGE_EXTS):
                        file_input = inp
                        break
                except Exception:  # noqa: BLE001  # nosec B112
                    continue
            if file_input is None:
                page.wait_for_timeout(1_000)
                waited += 1_000
        if file_input is None:
            raise RuntimeError("未找到图文上传入口（站点可能改版，检查 SELECTORS）")
        file_input.set_input_files(str(cover))

        # 2. 等素材上传完成（上传完成后 Quill 编辑器才出现）
        page.wait_for_selector(sel["content_editor"], timeout=60_000)

        # 3. 标题（多选择器轮询，xhs-toolkit 同款容错）
        filled = False
        for selector in (sel["title_input"], sel["title_input_alt"]):
            try:
                loc = page.locator(selector).first
                loc.click(timeout=5_000)
                loc.fill(title[:XHS_TITLE_LIMIT])
                filled = True
                break
            except Exception:  # noqa: BLE001  # nosec B112
                continue
        if not filled:
            raise RuntimeError("标题输入框未找到（站点可能改版，检查 SELECTORS）")

        # 4. 正文：Quill 编辑器点击聚焦 → 全选删除 → 逐行键入（xhs-toolkit 同款）
        editor = page.locator(sel["content_editor"]).first
        editor.click()
        page.keyboard.press("Control+a")
        page.keyboard.press("Delete")
        for line in body[:XHS_DESC_LIMIT].split("\n"):
            page.keyboard.type(line)
            page.keyboard.press("Enter")

        if debug_dir:
            Path(debug_dir).mkdir(parents=True, exist_ok=True)
            (Path(debug_dir) / "filled_page.html").write_text(page.content(), encoding="utf-8")

    # ─── 读回对账 ────────────────────────────────────────────────────

    def readback(self, title: str, page: Any = None, debug_dir: str | None = None) -> str:
        """读回笔记管理列表对账（草稿/发布同页不同 tab）；异常 MUST unverified。"""
        page = page or self._open_page()
        sel = self.selectors
        try:
            page.goto(sel["note_list_url"])
            page.wait_for_timeout(5_000)
            for tab in page.locator(sel["draft_tab"]).all():
                try:
                    tab.click()
                    page.wait_for_timeout(2_000)
                    break
                except Exception:  # noqa: BLE001  # nosec B112 - tab 点击失败降级为全文搜索
                    continue
            body = page.inner_text("body")
            if debug_dir:
                Path(debug_dir).mkdir(parents=True, exist_ok=True)
                (Path(debug_dir) / "note_list.txt").write_text(body, encoding="utf-8")
            return parse_readback([title] if title in body else [], title)
        except Exception:  # noqa: BLE001 - 观测层异常降级为 unverified（不冒报成功）
            return "unverified"

    # ─── 登录态 ──────────────────────────────────────────────────────

    def _open_page(self) -> Any:
        """真实浏览器打开（复用持久化登录态）。仅生产路径使用，单测注入 FakePage。"""
        pw = sync_playwright().start()
        browser = pw.chromium.launch(headless=False)
        state = self.storage_state if Path(self.storage_state).exists() else None
        context = browser.new_context(storage_state=state)
        page = context.new_page()

        def _on_close(_: Any) -> None:
            context.close()
            browser.close()
            pw.stop()

        page.on("close", _on_close)
        return page

    def login_interactive(self) -> None:
        """首跑扫码登录（Task 1.4）：打开登录页等待扫码，成功后持久化登录态。

        失效引导重扫：登录态失效时由调用方触发本方法重新扫码——MUST NOT 伪造登录。
        """
        sel = self.selectors
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()
            page.goto(sel["login_url"])

            # 扫码成功判定：离开登录页回到创作者中心任意页（真实站点登录后落
            # /new/home，不跳 publish/publish——A3 走查实测），不能硬等固定跳转 URL
            def _logged_in(url: Any) -> bool:
                u = str(url)
                return "creator.xiaohongshu.com" in u and "/login" not in u

            try:
                page.wait_for_url(_logged_in, timeout=180_000)
            except TimeoutError:
                # 超时兜底：用户实际已登录（URL 已离开登录页）也要持久化登录态，
                # 否则扫了码却白扫（A3 走查踩坑：等待 URL 错误导致登录态丢失）
                if not _logged_in(page.url):
                    raise
            # storage_state 写文件前必须确保父目录存在（A3 走查踩坑：目录缺失丢失登录态）
            Path(self.storage_state).parent.mkdir(parents=True, exist_ok=True)
            context.storage_state(path=self.storage_state)
            browser.close()
