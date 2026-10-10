"""小红书发布（Task 6.2，宪法原则 III：风控护栏）。

生产路线：调用本地 xiaohongshu-mcp 服务（xpzouying/xiaohongshu-mcp v2.5.5，
Go + rod，2026-10 活跃维护）的 HTTP API 完成发布。登录态管理、Tiptap 编辑器
适配、拟人化输入、反检测、发布成功判定（URL 跳离发布页）全部由该成熟项目
负责，本项目只做薄客户端。

A3 走查记录（为何弃自研方案）：
- edith API 逆向：风控拒外部签名；creator 域 success:true 为假阳性（笔记未落库）
- 自研 DOM：站点改版频繁（Quill→Tiptap、按钮重排），选择器维护成本高
- web 草稿箱：浏览器 localStorage 存储，App 不可见，无产品价值

服务部署（apps/api/data/tools/，gitignored）：
  1. xiaohongshu-login-windows-amd64.exe   # 首次扫码登录（一次持久化）
  2. xiaohongshu-mcp-windows-amd64.exe -headless  # 常驻 :18060
配置：XHS_MCP_BASE_URL（默认 http://localhost:18060）、XHS_MCP_TOKEN（可选）。

读回对账：创作者中心笔记管理页（DOM，复用持久化登录态 storage_state）。
"""

import os
import struct
import zlib
from pathlib import Path
from typing import Any

import requests
from playwright.sync_api import TimeoutError, sync_playwright

# 平台硬约束（xiaobei/AiToEarn 实测对齐；xiaohongshu-mcp 服务端亦校验）
XHS_TITLE_LIMIT = 20
XHS_DESC_LIMIT = 1000

# 读回选择器（笔记管理页，A3 实测；/publish/note 已 404）
SELECTORS: dict[str, str] = {
    "login_url": "https://creator.xiaohongshu.com/login",
    "note_list_url": "https://creator.xiaohongshu.com/new/note-manager",
    "draft_tab": "text=草稿",
}


def parse_readback(page_texts: list[str], title: str) -> str:
    """读回对账纯函数：页面文本含标题 → verified，否则 unverified。"""
    return "verified" if title in page_texts else "unverified"


def make_cover_png(path: str | Path, width: int = 1080, height: int = 1440) -> Path:
    """纯标准库生成 3:4 纯色封面 PNG（图文笔记至少需要 1 张图）。"""
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
    """小红书发布器：xiaohongshu-mcp 本地服务的 API 客户端（薄封装）。

    publish_draft：私密发布（仅自己可见）——宪法 I 的 xhs 落地形态，
    人工确认后公开化；publish：公开发布。真实结果以 readback 为准。
    """

    def __init__(
        self,
        base_url: str | None = None,
        token: str | None = None,
        storage_state: str | None = None,
        selectors: dict[str, str] | None = None,
    ):
        self.base_url = (
            base_url or os.environ.get("XHS_MCP_BASE_URL") or "http://localhost:18060"
        ).rstrip("/")
        self.token = token or os.environ.get("XHS_MCP_TOKEN", "")
        if storage_state is None:
            from zimeiti_api.config import LOGIN_STATE_PATH

            storage_state = str(LOGIN_STATE_PATH)
        self.storage_state = storage_state  # 读回 DOM 用
        self.selectors = selectors or SELECTORS

    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _publish(self, draft: Any, visibility: str, cover_path: str | None) -> dict[str, Any]:
        title = draft["title"] if isinstance(draft, dict) else draft.title
        body = draft["body"] if isinstance(draft, dict) else draft.body
        tags = (
            draft.get("tags") if isinstance(draft, dict) else getattr(draft, "tags", None)
        ) or []
        # 含空格的话题无法命中联想下拉（A3 实测：「AI Agent」等待超时），过滤
        clean_tags = [str(t).strip() for t in tags if str(t).strip() and " " not in str(t).strip()]
        cover = (
            Path(cover_path)
            if cover_path
            else make_cover_png(Path("data/outputs/xhs-main") / "cover.png")
        )
        payload = {
            # 约束由 preflight 前置校验保证（P0⑥）——不做静默截断（截断会改变内容
            # 语义并导致读回对账标题不一致）。超限内容应在 tools.publish 即被拒绝。
            "title": title,
            "content": body,
            "images": [str(cover.resolve())],
            "tags": clean_tags[:10],
            "visibility": visibility,
        }
        resp = requests.post(
            f"{self.base_url}/api/v1/publish",
            json=payload,
            headers=self._headers(),
            timeout=600,  # 服务端含图片上传+拟人化输入+话题联想，耗时较长
        )
        result = resp.json()
        if not result.get("success"):
            raise RuntimeError(
                f"发布失败: {result.get('message', '')} {str(result.get('error', ''))[:200]}"
            )
        data = result.get("data") or {}
        return {"status": data.get("status", ""), "title": data.get("title", ""), "raw": result}

    def publish_draft(self, draft: Any, cover_path: str | None = None, **_: Any) -> dict[str, Any]:
        """私密发布（仅自己可见）。真实结果以 readback 为准。"""
        return self._publish(draft, "仅自己可见", cover_path)

    def publish(self, draft: Any, cover_path: str | None = None, **_: Any) -> dict[str, Any]:
        """公开发布。真实结果以 readback 为准。"""
        return self._publish(draft, "公开可见", cover_path)

    # ─── 读回对账 ────────────────────────────────────────────────────

    def readback(self, title: str, page: Any = None, debug_dir: str | None = None) -> str:
        """读回笔记管理列表对账；接口异常 MUST 返回 unverified（不冒报成功）。"""
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
                except Exception:  # noqa: BLE001  # nosec B112
                    continue
            body = page.inner_text("body")
            if debug_dir:
                Path(debug_dir).mkdir(parents=True, exist_ok=True)
                (Path(debug_dir) / "note_list.txt").write_text(body, encoding="utf-8")
            return parse_readback([title] if title in body else [], title)
        except Exception:  # noqa: BLE001 - 观测层异常降级为 unverified（不冒报成功）
            return "unverified"

    # ─── 读回用浏览器（复用持久化登录态） ─────────────────────────────

    def _launch(self, pw: Any, headless: bool = False) -> Any:
        """启动带反检测的浏览器（参考 xhs-toolkit 的 Selenium 反检测思路）。"""
        try:
            browser = pw.chromium.launch(
                channel="chrome",
                headless=headless,
                ignore_default_args=["--enable-automation"],
                args=["--disable-blink-features=AutomationControlled"],
            )
        except Exception:  # noqa: BLE001 - 未装 Chrome 时回退 chromium
            browser = pw.chromium.launch(
                headless=headless,
                ignore_default_args=["--enable-automation"],
                args=["--disable-blink-features=AutomationControlled"],
            )
        return browser

    @staticmethod
    def _stealth(context: Any) -> None:
        """注入 navigator.webdriver 反检测补丁。"""
        context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

    def _open_page(self) -> Any:
        """真实浏览器打开（复用持久化登录态）。仅生产路径使用，单测注入 FakePage。"""
        pw = sync_playwright().start()
        browser = self._launch(pw, headless=False)
        state = self.storage_state if Path(self.storage_state).exists() else None
        context = browser.new_context(storage_state=state)
        self._stealth(context)
        page = context.new_page()

        def _on_close(_: Any) -> None:
            context.close()
            browser.close()
            pw.stop()

        page.on("close", _on_close)
        return page

    def login_interactive(self) -> None:
        """首跑扫码登录（读回 DOM 用登录态）。MUST NOT 伪造登录。"""
        sel = self.selectors
        with sync_playwright() as pw:
            browser = self._launch(pw, headless=False)
            context = browser.new_context()
            self._stealth(context)
            page = context.new_page()
            page.goto(sel["login_url"])

            # 扫码成功判定：离开登录页回到创作者中心任意页（A3 实测落 /new/home）
            def _logged_in(url: Any) -> bool:
                u = str(url)
                return "creator.xiaohongshu.com" in u and "/login" not in u

            try:
                page.wait_for_url(_logged_in, timeout=180_000)
            except TimeoutError:
                if not _logged_in(page.url):
                    raise
            # 目录必须存在（A3 走查踩坑：目录缺失丢失登录态）
            Path(self.storage_state).parent.mkdir(parents=True, exist_ok=True)
            context.storage_state(path=self.storage_state)
            browser.close()
