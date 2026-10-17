# -*- coding: utf-8 -*-
"""录制典型用户路径 demo 套件（每路径一段视频，与 E2E 十场景对应）。

基于 apps/e2e 十场景里除品牌 case 外最典型的四条用户路径：
  01 profile-wizard   画像创建向导全链路（S7，真实 LLM 增强）
  02 chat-sessions    对话流式创作 + 会话新建/切换/删除（S5）
  03 ideas-crud       选题库新建/编辑/删除（S3）
  04 outputs-browse   内容库浏览与文件预览（S6）

每个 demo 独立浏览器上下文（干净 localStorage）；可见虚拟光标 + 步骤横幅
复用 record_brand_demo 的原语；录制后演示数据自动清理。

用法（apps/api venv）: uv run python ../scripts/record_demo_suite.py
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

APPS = Path(__file__).resolve().parent.parent
API_DIR = APPS / "api"
OUT_DIR = APPS.parent / "docs" / "demo"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from record_brand_demo import (  # noqa: E402
    API_DIR as _API_DIR,  # noqa: F401
    api,
    back_to_dash,
    banner,
    glide,
    human_click,
    install_cursor,
)


def done_dialog(page) -> None:
    """自动接受 confirm/prompt（删除会话等）。"""
    page.on("dialog", lambda d: d.accept())


def ffmpeg_to_mp4(webm: Path, mp4: Path) -> None:
    conv = subprocess.run(
        ["ffmpeg", "-y", "-i", str(webm), "-c:v", "libx264", "-crf", "23",
         "-preset", "medium", "-movflags", "+faststart", str(mp4)],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=600,
    )
    if conv.returncode != 0 or not mp4.exists():
        raise RuntimeError(f"ffmpeg 转码失败: {conv.stderr[-300:] if conv.stderr else ''}")
    webm.unlink(missing_ok=True)
    print(f"    -> {mp4.name}（{mp4.stat().st_size // 1024} KB）")


# ── Demo 1：画像创建向导（S7）────────────────────────────────────────────
def demo_profile_wizard(page) -> None:
    name = "科技数码小助手"
    human_click(page, page.get_by_role("button", name="画像").first, 0.5)
    page.wait_for_timeout(1000)
    banner(page, "① 画像中心：给 AI 一份「你是谁」的设定", 2.8)
    human_click(page, page.get_by_role("button", name="+ 新建画像").first, 0.6)
    page.wait_for_timeout(500)

    banner(page, "② 创建向导：命名 → 平台 → 方向 → 目标", 3.0)
    page.get_by_placeholder("如：科技数码达人").fill(name)
    page.wait_for_timeout(400)
    direction = page.get_by_placeholder("如：平价护肤测评")
    goal = page.get_by_placeholder("涨粉 / 变现 / 个人品牌 / 引流私域")
    for _ in range(12):
        if direction.count() and not direction.input_value():
            direction.fill("AI 工具评测与效率技巧")
            page.wait_for_timeout(300)
        if goal.count() and not goal.input_value():
            goal.fill("涨粉")
            page.wait_for_timeout(300)
        btns = page.locator(".modal button, .overlay button")
        labels = [btns.nth(i).inner_text().strip() for i in range(btns.count())]
        if any("先进去用" in t for t in labels):
            break
        commit = next(
            (i for i, t in enumerate(labels)
             if ("生成" in t or t in ("完成", "创建画像")) and btns.nth(i).is_enabled()),
            None,
        )
        if commit is not None:
            human_click(page, btns.nth(commit), 0.6)
            break
        nxt = next((i for i, t in enumerate(labels) if t == "下一步" and btns.nth(i).is_enabled()), None)
        if nxt is not None:
            human_click(page, btns.nth(nxt), 0.5)
        else:
            page.wait_for_timeout(400)

    banner(page, "③ 提交：基线画像立即可用，AI 后台增强中…", 3.0)
    done = next((i for i in range(btns_count(page)) if "先进去用" in btn_text(page, i)), None)
    if done is not None:
        human_click(page, page.locator(".modal button, .overlay button").nth(done), 0.5)
    else:
        try:
            page.locator(".modal button", has_text="×").first.click()
        except Exception:
            pass
    # 等 LLM 增强完成（真实调用，1-3 分钟）；画像未建成时状态接口 404 → 视为未建
    from urllib.parse import quote
    st = "not-created"
    for _ in range(90):
        try:
            st = (api("GET", f"/api/profile/build/status/{quote(name)}") or {}).get("state") or "unknown"
        except Exception:
            st = "not-created"
            break
        if st != "running":
            break
        page.wait_for_timeout(2000)
        if st != "running":
            break
        page.wait_for_timeout(2000)
    banner(page, f"④ 画像「{name}」已就绪（AI 增强{'完成' if st == 'done' else st}）", 3.0)
    page.wait_for_timeout(1200)


def btn_count(page) -> int:
    return page.locator(".modal button, .overlay button").count()


# 兼容上面用到的两个小 helper
def btns_count(page) -> int:
    return page.locator(".modal button, .overlay button").count()


def btn_text(page, i: int) -> str:
    loc = page.locator(".modal button, .overlay button")
    if i >= loc.count():
        return ""
    return loc.nth(i).inner_text().strip()


# ── Demo 2：对话流式 + 会话管理（S5）────────────────────────────────────
def demo_chat_sessions(page) -> None:
    human_click(page, page.get_by_role("button", name="对话").first, 0.5)
    page.wait_for_timeout(1000)
    banner(page, "① 对话创作：像同事一样交代任务", 2.8)
    box = page.locator("textarea").first
    box.fill("用一句话解释什么是「上下文窗口」，面向后端程序员。直接回答，不要提问。")
    box.press("Enter")
    hint = page.locator(".composer-hint")
    for _ in range(24):
        if "生成中" in (hint.inner_text() or ""):
            break
        page.wait_for_timeout(500)
    page.wait_for_timeout(8000)
    for _ in range(60):
        if "生成中" not in (hint.inner_text() or ""):
            break
        page.wait_for_timeout(2000)
    banner(page, "② 流式回复完成，会话自动保存", 2.6)

    banner(page, "③ 新对话：不同任务互不干扰", 2.6)
    human_click(page, page.get_by_role("button", name="新对话").first, 0.5)
    page.wait_for_timeout(700)
    box = page.locator("textarea").first
    box.fill("给「程序员江湖」公众号起三个关于 Redis 的选题标题，只列标题。")
    box.press("Enter")
    for _ in range(24):
        if "生成中" in (hint.inner_text() or ""):
            break
        page.wait_for_timeout(500)
    for _ in range(60):
        if "生成中" not in (hint.inner_text() or ""):
            break
        page.wait_for_timeout(2000)

    banner(page, "④ 会话切换：回到上一个话题，上下文还在", 2.8)
    item = page.locator(".session-item:visible").nth(1)
    if item.count():
        human_click(page, item, 0.6)
        page.wait_for_timeout(900)

    banner(page, "⑤ 会话删除：不要的对话一键清理（确认框自动接受）", 2.8)
    first_item = page.locator(".session-item:visible").first
    if first_item.count():
        first_item.hover()
        page.wait_for_timeout(300)
        del_btn = first_item.locator("button[title='删除']").first
        if del_btn.count():
            human_click(page, del_btn, 0.4)
            page.wait_for_timeout(800)
    page.wait_for_timeout(800)


# ── Demo 3：选题库 CRUD（S3）────────────────────────────────────────────
def demo_ideas_crud(page) -> None:
    back_to_dash(page)
    human_click(page, page.get_by_role("button", name="记选题").first, 0.5)
    page.wait_for_timeout(1100)
    banner(page, "① 选题库：手动记录一个灵感", 2.8)
    human_click(page, page.get_by_role("button", name="+ 新建选题").first, 0.6)
    page.wait_for_timeout(400)
    box = page.get_by_placeholder("想做的内容 / 角度")
    box.fill("E2E 演示选题：Agent 记忆机制")
    with page.expect_response(lambda r: "/api/ideas" in r.url and r.request.method == "POST", timeout=10000):
        page.get_by_role("button", name="保存").click()
    page.wait_for_timeout(700)
    banner(page, "② 选题已入看板 → 直接编辑改题", 2.8)
    card = page.locator(".idea-card:visible", has_text="E2E 演示选题").first
    glide(page, card, 0.5)
    edit_btn = card.get_by_title("编辑") if card.get_by_title("编辑").count() else card.get_by_role("button", name="编辑").first
    human_click(page, edit_btn, 0.4)
    page.wait_for_timeout(400)
    edit_box = page.get_by_placeholder("想做的内容 / 角度")
    if edit_box.count() and edit_box.input_value():
        edit_box.fill("Agent 记忆机制：从对话历史到长期记忆")
        with page.expect_response(lambda r: "/api/ideas" in r.url and r.request.method in ("POST", "PUT"), timeout=10000):
            page.get_by_role("button", name="保存").click()
    else:
        # 编辑入口形态不同则退化为「再建一条改名选题」
        human_click(page, page.get_by_role("button", name="+ 新建选题").first, 0.4)
        page.get_by_placeholder("想做的内容 / 角度").fill("Agent 记忆机制：从对话历史到长期记忆")
        with page.expect_response(lambda r: "/api/ideas" in r.url and r.request.method == "POST", timeout=10000):
            page.get_by_role("button", name="保存").click()
    page.wait_for_timeout(700)
    banner(page, "③ 改名完成 → 演示删除", 2.8)
    card = page.locator(".idea-card:visible", has_text="Agent 记忆机制").first
    if card.count():
        card.hover()
        page.wait_for_timeout(300)
        human_click(page, card.get_by_title("删除").first, 0.4)
        page.wait_for_timeout(700)
    banner(page, "④ 选题的生命周期：新建 → 编辑 → 排期 → 删除，随你处置", 2.8)


# ── Demo 4：内容库浏览与预览（S6）───────────────────────────────────────
def demo_outputs_browse(page) -> None:
    human_click(page, page.get_by_role("button", name="内容库").first, 0.5)
    page.wait_for_timeout(1200)
    banner(page, "① 内容库：AI 产出的所有稿件自动归档", 2.8)
    page.mouse.wheel(0, 200)
    page.wait_for_timeout(700)
    node = page.get_by_text("wechat-article", exact=False).first
    if node.count():
        banner(page, "② 点开文章 → 在线预览 Markdown 成稿", 2.8)
        human_click(page, node, 0.7)
        page.wait_for_timeout(2400)
        page.mouse.wheel(0, 300)
        page.wait_for_timeout(900)
        try:
            page.locator(".drawer-overlay").click()
        except Exception:
            page.keyboard.press("Escape")
        page.wait_for_timeout(600)
    cover = page.get_by_text("cover", exact=False).first
    if cover.count():
        banner(page, "③ 封面图等素材同样可预览", 2.6)
        human_click(page, cover, 0.7)
        page.wait_for_timeout(1800)
        try:
            page.locator(".drawer-overlay").click()
        except Exception:
            page.keyboard.press("Escape")
        page.wait_for_timeout(500)
    banner(page, "④ 内容库 = 你的稿库：预览、下载、上传草稿一站式", 2.8)


def _wait_text(page, needle: str, timeout_s: int = 8) -> bool:
    """轮询等 app-layout 出现目标文案（列表异步刷新）。"""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            if needle in page.locator(".app-layout").inner_text():
                return True
        except Exception:
            pass
        page.wait_for_timeout(300)
    return False


# ── Demo 5：定时自动化与用量（S11/S12）────────────────────────────────────
def demo_automations_usage(page) -> None:
    human_click(page, page.get_by_role("button", name="自动化").first, 0.5)
    page.wait_for_timeout(1200)
    banner(page, "① 自动化：每天定时跑的运营任务，重启不丢", 2.8)

    # 清场：删除历史演示任务，保证画面从空态开始
    try:
        for a in api("GET", "/api/automations").get("automations", []):
            api("DELETE", f"/api/automations/{a['id']}")
        page.reload(wait_until="load")
        page.wait_for_timeout(1200)
        # reload 回到工作台——重新进自动化页
        human_click(page, page.get_by_role("button", name="自动化").first, 0.5)
        page.wait_for_timeout(900)
    except Exception:
        pass

    banner(page, "② 新建任务：每天早上 8 点自动找热点出选题", 2.8)
    human_click(page, page.get_by_role("button", name="+ 新建任务").first, 0.6)
    page.wait_for_timeout(500)
    page.locator("input[placeholder='如：每日出稿']").fill("每日早报")
    # 注意：页面有多个 select（侧栏画像下拉/表单类型选择），必须按选项值定位表单那个
    page.locator("select:has(option[value='prompt'])").first.select_option("prompt")
    page.locator("input[placeholder='如：找今天的 AI 热点并给三个角度']").fill("找今天的 AI 热点并给三个角度")
    page.wait_for_timeout(400)
    human_click(page, page.get_by_role("button", name="保存").first, 0.6)
    _wait_text(page, "每日早报")
    page.wait_for_timeout(900)

    banner(page, "③ 立即执行：后台跑起来，记录可查", 2.8)
    human_click(page, page.get_by_role("button", name="立即执行").first, 0.6)
    _wait_text(page, "最近执行", 6)
    page.wait_for_timeout(1500)
    page.mouse.wheel(0, 240)
    page.wait_for_timeout(900)

    banner(page, "④ 停用 / 删除：任务完全由你掌控", 2.6)
    btn = page.get_by_role("button", name="停用")
    if btn.count():
        human_click(page, btn.first, 0.5)
        _wait_text(page, "已停用")
        page.wait_for_timeout(700)
    try:
        for a in api("GET", "/api/automations").get("automations", []):
            if a.get("name") == "每日早报":
                api("DELETE", f"/api/automations/{a['id']}")
        page.reload(wait_until="load")
        page.wait_for_timeout(1000)
    except Exception:
        pass

    back_to_dash(page)
    page.wait_for_timeout(1000)
    banner(page, "⑤ 用量透明：每轮对话的 token 与费用一目了然", 2.8)
    page.mouse.wheel(0, 260)
    page.wait_for_timeout(1000)


# ── Demo 6：自主运营（S13）────────────────────────────────────────────────
def demo_autonomous(page) -> None:
    human_click(page, page.get_by_role("button", name="自主运营").first, 0.5)
    page.wait_for_timeout(1200)
    banner(page, "① 自主运营：把整条链路托管给 agent", 2.8)

    # 清场
    try:
        for f in api("GET", "/api/flows").get("flows", []):
            api("DELETE", f"/api/flows/{f['id']}")
        page.reload(wait_until="load")
        page.wait_for_timeout(1200)
        human_click(page, page.get_by_role("button", name="自主运营").first, 0.5)
        page.wait_for_timeout(900)
    except Exception:
        pass

    banner(page, "② 新建流程：每天 8 点自动「发现→选题→创作」", 2.8)
    human_click(page, page.get_by_role("button", name="+ 新建流程").first, 0.6)
    page.wait_for_timeout(500)
    page.locator("#flow-name").fill("每日选题")
    page.get_by_text("创作（成稿/素材）", exact=False).click()
    page.wait_for_timeout(400)
    human_click(page, page.get_by_role("button", name="保存").first, 0.6)
    if _wait_text(page, "每日选题"):
        page.wait_for_timeout(1000)

    banner(page, "③ 运行状态一目了然：预算 / 待确认 / 熔断护栏", 2.8)
    page.mouse.wheel(0, -200)
    page.wait_for_timeout(900)

    back_to_dash(page)
    page.wait_for_timeout(800)
    banner(page, "④ agent 自己跑，你只看结果——这就是自主运营", 2.8)


DEMOS = [
    ("01-profile-wizard", "首次使用：创建你的第一个画像", demo_profile_wizard),
    ("02-chat-sessions", "对话创作与会话管理", demo_chat_sessions),
    ("03-ideas-crud", "选题库：新建 / 编辑 / 删除", demo_ideas_crud),
    ("04-outputs-browse", "内容库：浏览与预览", demo_outputs_browse),
    ("05-automations-usage", "定时自动化与用量统计", demo_automations_usage),
    ("06-autonomous", "自主运营：流程托管与护栏", demo_autonomous),
]


def main() -> int:
    from playwright.sync_api import sync_playwright

    proc = subprocess.Popen(
        [str(API_DIR / ".venv" / "Scripts" / "python.exe"), "-m", "zimeiti_api", "--port", "8110"],
        cwd=API_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    new_sessions: list[str] = []
    try:
        for _ in range(40):
            try:
                urllib_ready()
                break
            except Exception:
                time.sleep(1)
        time.sleep(16)
        print("[demo] 服务就绪")

        OUT_DIR.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            for idx, (slug, title, fn) in enumerate(DEMOS):
                print(f"[demo] 录制 {slug}: {title}")
                ctx = browser.new_context(
                    viewport={"width": 1440, "height": 900},
                    record_video_dir=str(OUT_DIR),
                    record_video_size={"width": 1280, "height": 720},
                )
                page = ctx.new_page()
                page.set_default_timeout(20000)
                done_dialog(page)
                page.goto("http://127.0.0.1:8110", wait_until="load")
                page.wait_for_selector(".app-layout", timeout=20000)
                install_cursor(page)
                page.wait_for_timeout(600)
                banner(page, f"「程序员江湖」· {title}", 3.0)
                try:
                    fn(page)
                    ok = True
                except Exception as e:
                    print(f"    [!] {slug} 步骤异常：{e}")
                    ok = False
                banner(page, "程序员江湖 · 快速上手系列", 2.2)
                # 收集该上下文产生的会话（localStorage）供清理
                try:
                    sids = page.evaluate(
                        """() => { try {
                            return JSON.parse(localStorage.getItem('easel_sessions') || '[]').map(s => s.id);
                        } catch { return [] } }"""
                    )
                    new_sessions.extend(sids or [])
                except Exception:
                    pass
                video = page.video
                ctx.close()
                webm = Path(video.path())
                ffmpeg_to_mp4(webm, OUT_DIR / f"{slug}.mp4")
                if not ok:
                    print(f"    [!] {slug} 有步骤异常，视频已生成但请人工核对")
            browser.close()

        # ── 清理演示数据（全部容错：demo 未走到某步时对应资源可能不存在）──
        for sid in dict.fromkeys(new_sessions):
            try:
                api("DELETE", f"/api/session/{sid}")
                print(f"[cleanup] 删除演示会话 {sid}")
            except Exception as e:
                print(f"[cleanup] 会话 {sid} 清理失败（无碍）：{e}")
        try:
            for it in api("GET", "/api/ideas") or []:
                t = str(it.get("title", ""))
                if "E2E 演示选题" in t or "Agent 记忆机制：从对话历史到长期记忆" in t:
                    try:
                        api("DELETE", f"/api/ideas/{it['id']}")
                        print(f"[cleanup] 删除演示选题 {it['id']}")
                    except Exception as e:
                        print(f"[cleanup] 选题 {it['id']} 清理失败（无碍）：{e}")
        except Exception as e:
            print(f"[cleanup] ideas 清理失败（无碍）：{e}")
        try:
            for p in api("GET", "/api/personas") or []:
                if p.get("name") == "科技数码小助手":
                    # 删除路由是单数 /api/persona/{name}（复数仅 GET 列表）
                    api("DELETE", "/api/persona/科技数码小助手")
                    print("[cleanup] 删除演示画像")
        except Exception as e:
            print(f"[cleanup] 画像清理失败（无碍）：{e}")
        return 0
    finally:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def urllib_ready() -> None:
    import urllib.request
    urllib.request.urlopen("http://127.0.0.1:8110/api/status", timeout=15)


if __name__ == "__main__":
    sys.exit(main())
