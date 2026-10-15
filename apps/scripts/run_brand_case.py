# -*- coding: utf-8 -*-
"""「程序员江湖」公众号自动化运营 case——模拟用户完整使用系统的一轮运营。

流程（真实 LLM，非测试）：
  1. 建/复用画像「江小湖」（定位来自 multi-agent-manager 知识库）
  2. 系统热点雷达抓取热点 → LLM 筛选与后端/Java/AI/Agent 受众相关的选题
  3. 选题入库（/api/ideas）→ 排期到内容日历（/api/schedule）
  4. 按知识库写作规范生成完整文章（对话链路，agent 产出到内容库）
  5. 公众号草稿上传（apps/skills/shared/scripts/wechat_mp/draft.py，复制自
     my-tools/wechat-mp-manage 的逻辑；凭据 ~/.wechat-mp.json）——只建草稿，不发布
  6. 打印全部生成数据清单

用法（apps/api venv）:
  uv run python ../scripts/run_brand_case.py [--skip-draft] [--keep-server]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.request
import uuid
from datetime import date
from pathlib import Path

APPS = Path(__file__).resolve().parent.parent
API_DIR = APPS / "api"
KB = Path("e:/Projects/multi-agent-manager/knowledge/domains/my-brand/wechat-mp")
BASE = "http://127.0.0.1:8110"
PORT = 8110

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


def chat(message: str, persona: str = "江小湖", session_id: str | None = None,
         max_seconds: int = 420) -> tuple[str, str | None]:
    """对话链路（SSE 流式），返回 (回复全文, question_event 文本或 None)。"""
    if session_id is None:
        session_id = uuid.uuid4().hex[:12]
    req = urllib.request.Request(
        f"{BASE}/api/chat/stream",
        data=json.dumps({"message": message, "persona": persona, "sessionId": session_id}).encode(),
        method="POST", headers={"Content-Type": "application/json", "Origin": BASE},
    )
    text, question = [], None
    with urllib.request.urlopen(req, timeout=max_seconds) as r:
        start = time.time()
        event = "message"
        for raw in r:
            line = raw.decode("utf-8", "replace").rstrip("\n")
            if line.startswith("event:"):
                event = line[6:].strip()
                continue
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                break
            try:
                data = json.loads(payload)
            except Exception:
                continue
            if event == "token" and isinstance(data, str):
                text.append(data)
            elif event == "question":
                # HITL 问答：自动选「继续/直接/确认」类选项（否则第一个），同一 SSE 续流
                questions = (data or {}).get("questions") if isinstance(data, dict) else None
                if not questions:
                    question = str(data)[:200]
                    break
                for question in questions:
                    qid = question.get("questionId")
                    options = [str(o) for o in (question.get("options") or [])]
                    pick = next(
                        (o for o in options if re.search(r"继续|直接|确认|开始|是|好|保存|生成", o)),
                        options[0] if options else "按你的最佳判断直接完成，不要再确认",
                    )
                    try:
                        api("POST", "/api/chat/question/answer",
                            {"questionId": qid, "answers": {qid: [pick]}, "resolvedBy": "auto-case"},
                            timeout=30)
                        print(f"    [i] 自动应答：{pick[:40]}")
                    except Exception as e:
                        print(f"    [!] 应答失败：{e}")
                continue
            elif event == "done":
                break
            elif event == "error":
                text.append(f"\n[流错误] {data}")
                break
            if time.time() - start > max_seconds:
                break
    return "".join(text), question


def wait_server(timeout: float = 60) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"{BASE}/api/status", timeout=8)
            return
        except Exception:
            time.sleep(1)
    raise RuntimeError(f"{BASE} 未就绪")


def extract_json(reply: str) -> dict | None:
    m = re.search(r"\{.*\}", reply, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def newest_output_md(since: float) -> Path | None:
    out = APPS / "outputs"
    cands = [p for p in out.rglob("*.md") if p.stat().st_mtime >= since and not p.name.startswith("_")]
    return max(cands, key=lambda p: p.stat().st_mtime) if cands else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-draft", action="store_true", help="只生成材料，不上传草稿")
    ap.add_argument("--keep-server", action="store_true")
    args = ap.parse_args()
    generated: dict = {}

    # ── 0. 启动系统（真实 LLM：继承 .env，不注入 mock）──────────────
    proc = subprocess.Popen(
        [str(API_DIR / ".venv" / "Scripts" / "python.exe"), "-m", "zimeiti_api",
         "--port", str(PORT)],
        cwd=API_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        wait_server()
        print(f"[1/6] 系统就绪 {BASE}")
        generated["system"] = BASE

        # ── 1. 画像「江小湖」────────────────────────────────────────
        personas = api("GET", "/api/personas") or []
        names = [p.get("name") for p in personas]
        if "江小湖" not in names:
            api("POST", "/api/profile/build", {
                "name": "江小湖",
                "form": {
                    "direction": "公众号「程序员江湖」主理人：后端技术 + AI 干货分享，覆盖 Java 技术栈、后端全家桶、LLM 和 Agent 全栈",
                    "goal": "把公众号「程序员江湖」做成后端程序员群体的 AI 时代技术读物；引流锚点 github.com/h2pl/LearnAgent",
                    "platforms": ["wechat-oa"],
                    "tone": "亲切但不油腻，像有经验的同行朋友聊技术；开头用「你好，我是江小湖」或自然切入",
                },
            })
            print("[2/6] 画像「江小湖」已创建，等待后台 LLM 增强（防跨循环锁冲突）…")
            for _ in range(100):  # ~5min
                st = (api("GET", "/api/profile/build/status/江小湖", timeout=15) or {}).get("state")
                if st != "running":
                    print(f"    增强状态：{st}")
                    break
                time.sleep(3)
        else:
            print("[2/6] 画像「江小湖」已存在，复用")
        generated["persona"] = "江小湖"

        # ── 2. 热点雷达 → LLM 筛选题 ────────────────────────────────
        trends = api("GET", "/api/trends?platforms=weibo,douyin,zhihu&limit=20", timeout=120)
        items = []
        for block in (trends or {}).get("trends", []):
            for it in block.get("items", []):
                items.append({"platform": block.get("platform"), "title": it.get("title")})
        print(f"[3/6] 热点雷达抓到 {len(items)} 条")
        generated["trends_count"] = len(items)

        writing = (KB / "WRITING.md").read_text(encoding="utf-8")
        trend_lines = "\n".join(f"- [{t['platform']}] {t['title']}" for t in items[:30])
        reply, q = chat(
            "你是公众号「程序员江湖」的选题编辑。下面是今天的热点榜单：\n" + trend_lines +
            "\n\n请从中挑出 1 个最适合面向「后端程序员 + AI 学习者」受众的选题。约束："
            "①文章主体必须是技术原理/工程实践（热点只能作引子或类比），能稳定写满 1500 字而不依赖未经核实的新闻细节；"
            "②避开纯财经/时政/娱乐类需要事实核验的题；③与 Java/后端/LLM/Agent 相关或可迁移类比。"
            "再给出 2 个备选。只输出 JSON，不要提问，格式："
            '{"primary": {"title": "...", "angle": "切入角度一句话", "sub": "封面二级菜单，如 Agent 实战/LLM 基础"}, '
            '"backup": [{"title": "..."}, {"title": "..."}]}',
        )
        picked = extract_json(reply or "") or {}
        primary = picked.get("primary") or {}
        if not primary.get("title"):
            # 兜底：LLM 没给出结构化结果就用固定锚点选题
            primary = {"title": "Agent 记忆层设计：从对话历史到长期记忆的正确做法", "angle": "知识库系列下一篇", "sub": "Agent 实战"}
        print(f"    选题：{primary['title']}（{primary.get('angle','')}）")
        generated["topic"] = primary
        generated["backup_topics"] = picked.get("backup", [])

        # ── 3. 选题入库 + 排期 ──────────────────────────────────────
        idea = api("POST", "/api/ideas", {"title": primary["title"], "note": primary.get("angle", "")})
        generated["idea_id"] = (idea or {}).get("id")
        sched = api("POST", "/api/schedule", {"title": primary["title"], "date": date.today().isoformat(),
                                              "platform": "wechat-oa", "time": "", "status": "idea",
                                              "note": "brand-case 自动排期"})
        print(f"[4/6] 选题入库 idea={generated['idea_id']}，已排期今天")
        generated["schedule_id"] = (sched or {}).get("id")

        # ── 4. 生成文章（写作规范来自知识库）────────────────────────
        style = "\n".join(writing.splitlines()[:60])  # 规范要点（人设/钩子/节奏/格式）
        slug = "wechat-article-" + date.today().isoformat()
        out_name = f"{slug}.md"
        article_session = uuid.uuid4().hex[:12]
        prompt = (
            f"请以「江小湖」的人设为公众号「程序员江湖」写一篇完整文章。\n"
            f"选题：《{primary['title']}》，切入角度：{primary.get('angle','')}\n"
            f"事实边界：热点新闻本身只作引子一句话带过，文章主体写技术原理与工程实践，"
            f"不引用未经核实的新闻细节，不写具体未核实的数字。\n\n"
            f"写作规范（必须遵守）：\n{style}\n\n"
            f"硬性要求：1200-1800 字；开头必须有钩子；段落短；技术概念配可运行例子；"
            f"Markdown 格式：# 标题 → > 一句话摘要 → 正文（## 二级、### 三级最多两层）；"
            f"结尾 1-3 句总结 + 自然行动引导。\n"
            f"输出方式：直接在回复里给出完整文章 Markdown（第一行就是「# 文章标题」），"
            f"除文章正文外不要输出任何别的说明。不要提问、不要请求确认，一次完成。"
        )
        t0 = time.time()
        article_reply, q = chat(prompt, session_id=article_session, max_seconds=600)
        if q:
            print(f"    [!] agent 发起提问（已记录）：{q}")
        # 提取正文：从第一个「# 」标题行起到结尾（剥掉 agent 的任何前后缀白话）
        lines = (article_reply or "").splitlines()
        start = next((i for i, ln in enumerate(lines) if ln.startswith("# ")), None)
        article_md = "\n".join(lines[start:]).strip() if start is not None else (article_reply or "").strip()
        md_file = APPS / "outputs" / "wechat-drafts" / out_name
        md_file.parent.mkdir(parents=True, exist_ok=True)
        md_file.write_text(article_md, encoding="utf-8")
        word_count = len(article_md)
        print(f"[5/6] 文章已生成并落内容库：{md_file.name}（{word_count} 字，{time.time()-t0:.0f}s）")
        generated["article"] = {"path": str(md_file), "chars": word_count}

        # ── 5. 公众号草稿（只建草稿，绝不发布）──────────────────────
        if not args.skip_draft:
            from wechat_mp.draft import run_draft

            result = run_draft(
                md_file,
                sub=primary.get("sub") or "Agent 实战",
                title=primary.get("mp_title") or primary["title"],
                author="江小湖",
            )
            generated["draft"] = result
            print(f"[6/6] 公众号草稿已创建：{result['media_id']}（未发布）")
        else:
            print("[6/6] --skip-draft：跳过草稿上传")

        print("\n===== 生成数据汇总 =====")
        print(json.dumps(generated, ensure_ascii=False, indent=2, default=str))
        return 0
    finally:
        if not args.keep_server:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == "__main__":
    sys.exit(main())
