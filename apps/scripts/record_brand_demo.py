# -*- coding: utf-8 -*-
"""录制「程序员江湖」运营全流程上手指引视频（真实前端 + 真实 LLM）。

流程：工作台 → 热点雷达（收藏选题）→ 选题库（一键排期）→ 内容日历 →
做内容（选题自动带入对话，流式生成文案初稿）→ 内容库 → 账号（公众号草稿）。

可视化：无头录屏不渲染系统光标，注入**可见虚拟光标**（箭头平滑移动 + 点击
涟漪），观众能看清每一次点击落点。
产物：docs/demo/brand-demo.mp4（webm 由 Playwright 录制，ffmpeg 转 h264）。
录制中产生的演示数据（收藏的选题/排期/对话会话）录制后自动清理。

用法（apps/api venv）: uv run python ../scripts/record_brand_demo.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

APPS = Path(__file__).resolve().parent.parent
API_DIR = APPS / "api"
BASE = "http://127.0.0.1:8110"
OUT_DIR = APPS.parent / "docs" / "demo"

sys.path.insert(0, str(APPS / "skills" / "shared" / "scripts"))


def api(method: str, path: str, payload: dict | None = None, timeout: int = 60):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        f"{BASE}{path}", data=data, method=method,
        headers={"Content-Type": "application/json", "Origin": BASE},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read().decode("utf-8", "replace")
        return json.loads(body) if body and body.lstrip()[:1] in "[{" else None


CURSOR_JS = """() => {
  if (document.getElementById('__demo_cursor')) return;
  const s = document.createElement('style');
  s.textContent = '@keyframes __dripple { 0%{transform:translate(-50%,-50%) scale(.25);'
    + 'opacity:.9} 100%{transform:translate(-50%,-50%) scale(2.6);opacity:0} }';
  document.head.appendChild(s);
  const c = document.createElement('div');
  c.id = '__demo_cursor';
  c.innerHTML = '<svg width="26" height="26" viewBox="0 0 24 24" '
    + 'style="filter:drop-shadow(0 2px 5px rgba(0,0,0,.55))">'
    + '<path d="M4 1.5 L18.5 13.5 L11.6 14.3 L15.2 22 L12.1 23.3 L8.7 15.4 L4 20 Z" '
    + 'fill="#ffffff" stroke="#1e293b" stroke-width="1.1"/></svg>';
  c.style.cssText = 'position:fixed;left:0;top:0;z-index:100001;pointer-events:none;'
    + 'transition:transform .5s cubic-bezier(.25,.7,.3,1)';
  document.body.appendChild(c);
}"""

MOVE_JS = """(p) => {
  const c = document.getElementById('__demo_cursor');
  if (c) c.style.transform = `translate(${p.x}px, ${p.y}px)`;
}"""

RIPPLE_JS = """(p) => {
  const d = document.createElement('div');
  d.style.cssText = 'position:fixed;left:' + p.x + 'px;top:' + p.y + 'px;width:40px;height:40px;'
    + 'border:3px solid #38bdf8;border-radius:50%;pointer-events:none;z-index:100000;'
    + 'animation:__dripple .55s ease-out forwards';
  document.body.appendChild(d);
  setTimeout(() => d.remove(), 600);
}"""


def banner(page, text: str, hold: float = 2.8) -> None:
    page.evaluate(
        """(t) => {
        document.getElementById('__demo_banner')?.remove();
        const d = document.createElement('div');
        d.id = '__demo_banner';
        d.style.cssText = 'position:fixed;top:20px;left:50%;transform:translateX(-50%);'
            + 'z-index:99999;background:rgba(15,23,42,.94);color:#fff;padding:12px 26px;'
            + 'border-radius:12px;font-size:17px;font-weight:600;letter-spacing:.5px;'
            + 'box-shadow:0 6px 22px rgba(0,0,0,.4);border:1px solid rgba(255,255,255,.18)';
        d.textContent = t;
        document.body.appendChild(d);
    }""",
        text,
    )
    page.wait_for_timeout(int(hold * 1000))


def install_cursor(page) -> None:
    page.evaluate(CURSOR_JS)


def glide(page, loc, hold: float = 0.8) -> None:
    """可见光标平滑移动到元素中心并悬停（真实 hover 事件同步触发）。"""
    box = loc.bounding_box()
    if not box:
        return
    x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    page.evaluate(MOVE_JS, {"x": x - 6, "y": y - 4})  # 光标尖端对准元素中心
    page.mouse.move(x, y, steps=14)
    page.wait_for_timeout(560)  # 等光标过渡动画走完
    page.wait_for_timeout(int(hold * 1000))


def human_click(page, loc, hold: float = 0.6) -> None:
    """可见光标移过去 → 涟漪标注点击落点 → 真实点击。"""
    glide(page, loc, hold)
    box = loc.bounding_box()
    if box:
        page.evaluate(RIPPLE_JS, {"x": box["x"] + box["width"] / 2, "y": box["y"] + box["height"] / 2})
        page.wait_for_timeout(280)
    loc.click()


def back_to_dash(page) -> None:
    """工具页经 SubNav「← 工作台」返回（quick 按钮只在工作台有）。"""
    back = page.locator(".subnav-back")
    if back.count():
        human_click(page, back.first, 0.5)
        page.wait_for_timeout(800)


def main() -> int:
    from playwright.sync_api import sync_playwright

    proc = subprocess.Popen(
        [str(API_DIR / ".venv" / "Scripts" / "python.exe"), "-m", "zimeiti_api", "--port", "8110"],
        cwd=API_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(40):
            try:
                urllib.request.urlopen(f"{BASE}/api/status", timeout=5)
                break
            except Exception:
                time.sleep(1)
        time.sleep(16)  # 等热点预热完成，保证工作台/热点即开即有数据
        print("[demo] 服务就绪，开始录制")

        OUT_DIR.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            ctx = browser.new_context(
                viewport={"width": 1440, "height": 900},
                record_video_dir=str(OUT_DIR),
                record_video_size={"width": 1280, "height": 720},
            )
            page = ctx.new_page()
            page.set_default_timeout(20000)

            # 开场
            page.goto(BASE, wait_until="load")
            page.wait_for_selector(".app-layout", timeout=20000)
            install_cursor(page)
            page.wait_for_timeout(800)
            banner(page, "「程序员江湖」自媒体运营工作台 · 快速上手", 3.2)

            # ① 工作台
            banner(page, "① 工作台：选题、排期、内容、账号，一屏总览", 3.0)
            for card in page.locator(".dash-stat").all()[:4]:
                glide(page, card, 0.5)

            # ② 热点雷达
            human_click(page, page.get_by_role("button", name="看热点").first, 0.5)
            page.wait_for_timeout(1100)
            banner(page, "② 热点雷达：微博 / 抖音 / 知乎 热点实时抓取", 3.0)
            first_trend = page.locator("button:has-text('做内容')").first
            for _ in range(30):
                if first_trend.count():
                    break
                page.wait_for_timeout(500)
            glide(page, first_trend, 1.0)
            page.mouse.wheel(0, 260)
            page.wait_for_timeout(900)
            ideas_before = {i.get("id") for i in (api("GET", "/api/ideas") or [])}

            # ③ 收藏到选题库
            save_btn = page.locator("button.trend-save").first
            human_click(page, save_btn, 0.6)
            page.wait_for_timeout(700)
            banner(page, "③ 一键收藏 → 自动进入选题库", 2.6)
            # 用服务端差集拿收藏产生的选题标题（=热点标题）
            trend_title, new_idea_id = "", ""
            for it in api("GET", "/api/ideas") or []:
                if it.get("id") not in ideas_before:
                    trend_title = str(it.get("title", ""))
                    new_idea_id = it.get("id")
                    break

            # ④ 选题库：对刚收藏的这条选题一键排期
            back_to_dash(page)
            human_click(page, page.get_by_role("button", name="记选题").first, 0.5)
            page.wait_for_timeout(1000)
            banner(page, "④ 选题库：看板式管理，一键排期", 2.8)
            card = page.locator(".idea-card:visible", has_text=trend_title[:12]).first
            if not card.count():
                card = page.locator(".idea-card:visible").first
            glide(page, card, 0.7)
            human_click(page, card.get_by_role("button", name="排期"), 0.6)
            page.wait_for_timeout(800)

            # ⑤ 内容日历
            back_to_dash(page)
            human_click(page, page.get_by_role("button", name="排日历").first, 0.5)
            page.wait_for_timeout(1100)
            banner(page, "⑤ 内容日历：发布节奏与断更缺口一目了然", 3.0)
            page.wait_for_timeout(800)

            # ⑥ 回热点 → 做内容：选题自动带入对话，agent 判断赛道并产出文案初稿
            back_to_dash(page)
            human_click(page, page.get_by_role("button", name="看热点").first, 0.5)
            page.wait_for_timeout(900)
            banner(page, "⑥ 做内容：选题自动带入对话，AI 判断赛道 → 二创角度 → 文案初稿", 3.2)
            same_trend = page.locator("div", has_text=trend_title[:12]).locator("button:has-text('做内容')").first
            human_click(page, same_trend if same_trend.count() else first_trend, 0.6)
            page.wait_for_timeout(1400)
            # 做内容已自动新开会话并发出选题指令——等流式开始，展示生成过程
            hint = page.locator(".composer-hint")
            started = False
            for _ in range(24):
                if "生成中" in (hint.inner_text() or ""):
                    started = True
                    break
                page.wait_for_timeout(500)
            page.wait_for_timeout(12000)  # 让观众看清流式输出
            done = False
            for _ in range(150):  # 真实 LLM 全文初稿，最多 5 分钟
                if "生成中" not in (hint.inner_text() or ""):
                    done = True
                    break
                page.wait_for_timeout(2000)
            print(f"[demo] 流式开始={started} 完成={done}")
            # 会话列表在前端 localStorage——读取新会话 ID 供录制后清理
            new_sid = page.evaluate(
                """() => { try {
                    const cur = JSON.parse(localStorage.getItem('easel_sessions') || '[]');
                    return cur.length ? cur[0].id : null;
                } catch { return null } }"""
            )

            # ⑦ 内容库（侧栏主导航，随处可达）
            human_click(page, page.get_by_role("button", name="内容库").first, 0.5)
            page.wait_for_timeout(1100)
            banner(page, "⑦ 内容库：成稿归档、在线预览", 2.8)
            node = page.get_by_text("wechat-article", exact=False).first
            if node.count():
                human_click(page, node, 0.7)
                page.wait_for_timeout(2400)
                try:
                    page.locator(".drawer-overlay").click()
                except Exception:
                    page.keyboard.press("Escape")
                page.wait_for_timeout(500)

            # ⑧ 账号：公众号凭证 / 草稿
            human_click(page, page.get_by_role("button", name="账号").first, 0.5)
            page.wait_for_timeout(1100)
            banner(page, "⑧ 账号中心：公众号已配置——文章一键上传草稿箱（只建草稿，绝不自动发布）", 3.4)

            banner(page, "程序员江湖 · 从热点到草稿，一站式搞定", 3.2)
            video = page.video
            ctx.close()
            video_path = Path(video.path())
            browser.close()

        # 转码 webm → mp4
        mp4 = OUT_DIR / "brand-demo.mp4"
        conv = subprocess.run(
            ["ffmpeg", "-y", "-i", str(video_path), "-c:v", "libx264", "-crf", "23",
             "-preset", "medium", "-movflags", "+faststart", str(mp4)],
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=600,
        )
        if conv.returncode != 0 or not mp4.exists():
            raise RuntimeError(f"ffmpeg 转码失败: {conv.stderr[-300:] if conv.stderr else ''}")
        video_path.unlink(missing_ok=True)
        print(f"[demo] 视频已生成：{mp4}（{mp4.stat().st_size // 1024} KB）")

        # ── 清理录制产生的演示数据 ────────────────────────────────
        if new_sid:
            try:
                api("DELETE", f"/api/session/{new_sid}")
                print(f"[cleanup] 删除演示会话 {new_sid}")
            except Exception as e:
                print(f"[cleanup] 会话清理失败（无碍）：{e}")
        for it in api("GET", "/api/schedule") or []:
            if it.get("id") != "ce65aaa6b211":
                api("DELETE", f"/api/schedule/{it['id']}")
                print(f"[cleanup] 删除演示排期 {it['id']}")
        for it in api("GET", "/api/ideas") or []:
            if it.get("id") == new_idea_id or (trend_title and trend_title[:18] in str(it.get("title", ""))):
                api("DELETE", f"/api/ideas/{it['id']}")
                print(f"[cleanup] 删除演示选题 {it['id']}")
        return 0
    finally:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == "__main__":
    sys.exit(main())
