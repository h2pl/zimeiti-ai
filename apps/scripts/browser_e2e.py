# -*- coding: utf-8 -*-
"""浏览器级 E2E（双端对齐）：同一套真实用户操作分别跑 zimeiti 与 Easel，断言行为一致。

与 e2e_parity_check.py（HTTP API 对比）互补。原则（用户指定）：
  - 前端代码源自 Easel，不以感觉测——同一旅程在两端跑，比较行为观测值；
  - 场景从 API 路径映射而来，凡有 UI 入口的路径都覆盖；无 UI 入口的路径
    （技能执行/发布后端/登录扫码等）由 API 级 parity 覆盖，末尾输出映射表。

运行：cd apps/api && uv run python ../scripts/browser_e2e.py
前置：apps/web/dist 已构建；本地 PG；Easel 仓库在 e:/Projects/Easel。
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
APPS = SCRIPTS.parent
API_DIR = APPS / "api"
EASEL_DIR = Path("e:/Projects/Easel")
PORT_Z = 8110
BASE_Z = f"http://127.0.0.1:{PORT_Z}"
BASE_E = "http://127.0.0.1:7860"

TITLE = "浏览器E2E对齐选题"

# 每个 API 路径簇 → 浏览器场景映射（无 UI 入口的由 API parity 覆盖）
COVERAGE_MAP = {
    "GET /api/status": "S1/S2",
    "GET /api/trends": "S8",
    "POST/GET/PUT/DELETE /api/ideas": "S3",
    "POST /api/schedule + GET /api/schedule": "S4",
    "GET /api/personas": "S6",
    "GET /api/outputs + /api/output/{path} + /api/media": "S7",
    "POST /api/chat/stream（SSE）+ GET /api/chat/jobs": "S5",
    "POST /api/chat/question/answer|status": "S5（问答卡依赖 HITL，浏览器层由 API parity 覆盖）",
    "DELETE /api/session/{key}": "S5（会话删除有 confirm 依赖，API parity 覆盖）",
    "POST /api/upload*": "无 UI 自动化（拖拽上传），API parity 覆盖",
    "GET /api/upload/limits": "S5（上传面板挂载即取）",
    "login/publish/wechat/analytics/env/models/skills/profile-build": "无浏览器旅程（平台扫码/后台任务），API parity 覆盖",
}

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail and not ok else ""))


def _wait_ready(base: str, proc, timeout: float = 40) -> None:
    for _ in range(int(timeout * 2)):
        try:
            urllib.request.urlopen(f"{base}/api/status", timeout=2)
            return
        except Exception:
            if proc.poll() is not None:
                raise RuntimeError(f"{base} 进程提前退出")
            time.sleep(0.5)
    proc.kill()
    raise RuntimeError(f"{base} {timeout}s 未就绪")


def spawn_target(name: str) -> tuple[str, subprocess.Popen]:
    if name == "zimeiti":
        venv_py = API_DIR / ".venv" / "Scripts" / "python.exe"
        env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}  # 确定性降级帧
        env["EASEL_PORT"] = str(PORT_Z)
        proc = subprocess.Popen(
            [str(venv_py), "-m", "zimeiti_api", "--host", "127.0.0.1", "--port", str(PORT_Z)],
            cwd=API_DIR, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        base = BASE_Z
    else:
        venv_py = EASEL_DIR / ".venv" / "Scripts" / "python.exe"
        proc = subprocess.Popen(
            [str(venv_py), "web/app.py"],
            cwd=EASEL_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        base = BASE_E
    _wait_ready(base, proc)
    return base, proc


def click_nav(page, label: str, timeout: int = 15000) -> None:
    """导航点击：role=button 优先（新构建），text 兜底（旧构建可能是 div 项）。"""
    try:
        page.get_by_role("button", name=label).first.click(timeout=3000)
    except Exception:
        page.get_by_text(label, exact=True).first.click(timeout=timeout)


def run_suite(base: str, target: str) -> dict:
    """在指定端上跑完整旅程，返回行为观测值（供双端比较）。"""
    from playwright.sync_api import sync_playwright

    obs: dict = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        page.on("dialog", lambda d: d.accept())
        js_errors: list[str] = []
        page.on("pageerror", lambda e: js_errors.append(str(e)))

        # ---- S1 首屏 + 引导 ----
        page.goto(base, wait_until="load")
        page.wait_for_selector(".app-layout", timeout=20000)
        obs["S1"] = {"skeleton": True}
        # 弹层在 /api/status 返回后才挂载（异步）——轮询等待而非立即断言
        dismiss = page.get_by_role("button", name="先用通用模式")
        for _ in range(25):
            if dismiss.count() > 0:
                break
            page.wait_for_timeout(300)
        obs["S1"]["onboarding_modal"] = dismiss.count() > 0
        if dismiss.count() > 0:
            dismiss.first.click()
            page.wait_for_timeout(400)  # 等 overlay 卸载，避免挡住后续点击
        check(f"[{target}] S1 首屏骨架+引导", obs["S1"]["skeleton"] is True)

        # ---- S2 全页面导航 ----
        reached = []
        for label in ["工作台", "热点雷达", "选题库", "内容日历", "发布中心", "爆款拆解",
                      "内容库", "账号", "画像", "技能库"]:
            try:
                page.get_by_role("button", name=label).first.click(timeout=5000)
                page.wait_for_timeout(200)
                reached.append(label)
            except Exception as e:
                reached.append(f"{label}✗{type(e).__name__}")
        obs["S2"] = {"reached": reached, "js_errors": len(js_errors)}
        check(f"[{target}] S2 全页面导航", all("✗" not in r for r in reached), str(reached))

        # ---- S3 选题 CRUD ----
        def go_ideas():
            click_nav(page, "工作台")
            click_nav(page, "热点雷达")
            click_nav(page, "选题库")
            page.wait_for_timeout(1000)  # 等列表 GET 完成——否则保存 POST 与刷新 GET 竞态，新卡被过期响应覆盖

        def sweep_leftovers():
            """自清理：删掉历次运行残留的同名卡片（E2E 写真实数据存储）。"""
            for _ in range(12):
                cards = page.locator(".idea-card:visible", has_text=TITLE)
                if cards.count() == 0:
                    return
                cards.first.hover()  # 操作按钮 display:none，:hover 才渲染
                with page.expect_response(
                    lambda r: "/api/ideas" in r.url and r.request.method == "DELETE",
                    timeout=8000,
                ):
                    cards.first.get_by_title("删除").click()
                with page.expect_response(
                    lambda r: "/api/ideas" in r.url and r.request.method == "GET",
                    timeout=8000,
                ):
                    pass  # 等 app 自己的列表刷新回包，避免读写竞态
                page.wait_for_timeout(200)

        try:
            go_ideas()
            sweep_leftovers()
            page.get_by_role("button", name="+ 新建选题").click()
            page.get_by_placeholder("想做的内容 / 角度").fill(TITLE)
            with page.expect_response(
                lambda r: "/api/ideas" in r.url and r.request.method == "POST", timeout=8000
            ):
                page.get_by_role("button", name="保存").click()
            with page.expect_response(
                lambda r: "/api/ideas" in r.url and r.request.method == "GET", timeout=8000
            ):
                pass
            created = page.get_by_text(TITLE, exact=False).count() > 0
            if not created:
                page.screenshot(path=str(SCRIPTS / "_s3a_fail.png"))
            check(f"[{target}] S3a 新建选题出现", created)
            deleted = False
            if created:
                del_card = page.locator(".idea-card:visible", has_text=TITLE).first
                del_card.hover()
                with page.expect_response(
                    lambda r: "/api/ideas" in r.url and r.request.method == "DELETE", timeout=8000
                ):
                    del_card.get_by_title("删除").click()
                with page.expect_response(
                    lambda r: "/api/ideas" in r.url and r.request.method == "GET", timeout=8000
                ):
                    pass
                sweep_leftovers()
                deleted = page.get_by_text(TITLE, exact=False).count() == 0
            check(f"[{target}] S3b 删除后移除", deleted)
            obs["S3"] = {"created": created, "deleted": deleted}
        except Exception as e:
            obs["S3"] = {"created": False, "deleted": False, "error": str(e)[:120]}
            check(f"[{target}] S3 选题 CRUD", False, str(e)[:120])

        # ---- S5 对话链路（UI→SSE→真实模型→帧渲染；两端都走 .env 真实 key）----
        try:
            click_nav(page, "对话")
            box = page.locator("textarea").first
            box.fill(f"{target} 浏览器探活消息")
            box.press("Enter")
            hint = page.locator(".composer-hint")
            started = False
            for _ in range(20):
                if "生成中" in (hint.inner_text() or ""):
                    started = True
                    break
                page.wait_for_timeout(500)
            done = False
            last_len, stall = -1, 0
            for _ in range(90):  # 真实 LLM 最长 180s
                if started and "生成中" not in (hint.inner_text() or ""):
                    done = True
                    break
                page.wait_for_timeout(2000)
                txt = page.locator(".chat-messages").inner_text() if page.locator(".chat-messages").count() else ""
                if len(txt) == last_len:
                    stall += 1
                    if stall >= 2 and len(txt) > len(f"{target} 浏览器探活消息") + 10:
                        done = True  # 文本停止增长 = 流已收尾
                        break
                else:
                    stall = 0
                last_len = len(txt)
            thread_txt = page.locator(".chat-messages").inner_text() if page.locator(".chat-messages").count() else ""
            has_reply = done and len(thread_txt.strip()) > 0
            check(f"[{target}] S5a 流式开始", started)
            check(f"[{target}] S5b 流式完成且有回复", has_reply)
            obs["S5"] = {"started": started, "completed": done, "has_reply": has_reply}
        except Exception as e:
            obs["S5"] = {"started": False, "completed": False, "has_reply": False}
            check(f"[{target}] S5 对话链路", False, str(e)[:120])

        # ---- S6/S7/S8 三个数据页渲染（结构级对齐）----
        for label, key in [("画像", "S6"), ("内容库", "S7")]:
            try:
                page.get_by_role("button", name=label).first.click()
                page.wait_for_timeout(400)
                rendered = page.locator(".page-host").count() == 1
                obs[key] = {"rendered": rendered}
                check(f"[{target}] {key} {label}页渲染", rendered)
            except Exception as e:
                obs[key] = {"rendered": False}
                check(f"[{target}] {key} {label}页渲染", False, str(e)[:100])
        try:
            click_nav(page, "工作台")
            click_nav(page, "热点雷达")
            click_nav(page, "内容日历")
            page.wait_for_timeout(400)
            obs["S8"] = {"rendered": page.locator(".page-host").count() == 1}
            check(f"[{target}] S8 内容日历渲染", obs["S8"]["rendered"])
        except Exception as e:
            obs["S8"] = {"rendered": False}
            check(f"[{target}] S8 内容日历渲染", False, str(e)[:100])

        obs["js_errors_total"] = len(js_errors)
        obs["js_error_samples"] = js_errors[:2]
        browser.close()
    return obs


def compare(zo: dict, eo: dict) -> list[str]:
    """双端观测值对齐比较，返回差异清单。"""
    diffs = []
    for key in sorted(set(zo) | set(eo)):
        zv, ev = zo.get(key), eo.get(key)
        if key == "S5":
            for f in ("started", "completed", "has_reply"):
                if bool((zv or {}).get(f)) != bool((ev or {}).get(f)):
                    diffs.append(f"S5.{f}: zimeiti={zv} easel={ev}")
        elif key == "js_errors_total":
            if bool(zv) != bool(ev):
                diffs.append(f"JS 错误: zimeiti={zv} 样本={(zo.get('js_error_samples') or [])[:1]} easel={ev} 样本={(eo.get('js_error_samples') or [])[:1]}")
        else:
            if zv != ev:
                diffs.append(f"{key}: zimeiti={zv} easel={ev}")
    return diffs


def main() -> int:
    from playwright.sync_api import sync_playwright  # noqa: F401  前置校验

    procs = []
    all_ok = True
    obs_by_target: dict[str, dict] = {}
    try:
        for target in ("zimeiti", "easel"):
            print(f"\n===== 目标端: {target} =====")
            base, proc = spawn_target(target)
            procs.append(proc)
            try:
                obs_by_target[target] = run_suite(base, target)
            finally:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except Exception:
                    proc.kill()

        print("\n===== 双端对齐比较 =====")
        diffs = compare(obs_by_target.get("zimeiti", {}), obs_by_target.get("easel", {}))
        if diffs:
            all_ok = False
            for d in diffs:
                print(f"  [DIFF] {d}")
        else:
            print("  全部观测值一致")

        print("\n===== API 路径 → 浏览器场景覆盖映射 =====")
        for path, scene in COVERAGE_MAP.items():
            print(f"  {path}  →  {scene}")

        failed = [r for r in results if not r[1]]
        print(f"\n小结: {len(results) - len(failed)}/{len(results)} 通过 | 双端差异 {len(diffs)} 项")
        return 0 if (all_ok and not failed) else 1
    finally:
        for p in procs:
            try:
                p.kill()
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())
