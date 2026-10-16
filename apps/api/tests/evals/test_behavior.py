"""行为层探针（agent-behavior-evals，真实 LLM，仅 `make evals` 跑）。

每条用例用「工具调用轨迹 + 语义命中」双证据断言；单证据不足 → 报证据不足并打印
原文尾部供人工复核。用例结束清理演示数据（finally，失败也清）。
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

API_DIR = Path(__file__).resolve().parents[2]
PORT = int(os.environ.get("EVALS_PORT", "8121"))
BASE = f"http://127.0.0.1:{PORT}"

pytestmark = pytest.mark.behavior


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _key() -> str:
    for f in (API_DIR / ".env", API_DIR.parent / ".env"):
        if f.exists():
            for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.startswith("OPENAI_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"')
    return ""


@pytest.fixture(scope="module", autouse=True)
def server():
    """起独立端口实例（fallback 用例单独起自己的坏端点实例）。"""
    if not _key():
        pytest.skip("未配置 OPENAI_API_KEY，跳过行为层")
    env = dict(os.environ)
    env.update(
        {"PYTHONUTF8": "1", "OPENAI_BASE_URL": "https://api.deepseek.com", "OPENAI_API_KEY": _key()}
    )
    env.pop("ZIMEITI_FALLBACK_MODELS", None)
    proc = subprocess.Popen(
        [sys.executable, "-m", "zimeiti_api", "--port", str(PORT)],
        cwd=str(API_DIR),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(40):
        try:
            urllib.request.urlopen(
                urllib.request.Request(f"{BASE}/api/status", headers={"Origin": BASE}), timeout=3
            ).read()
            break
        except Exception:
            time.sleep(1)
    yield proc
    proc.terminate()
    try:
        proc.wait(timeout=15)
    except Exception:
        proc.kill()


def chat(message: str, session_id: str | None = None, timeout: int = 300) -> dict:
    """返回 {text, tools, asked, error}——tools 从 activity 事件抽取，asked 看 question 事件。"""
    body = {"message": message}
    if session_id:
        body["sessionId"] = session_id
    req = urllib.request.Request(
        f"{BASE}/api/chat/stream",
        data=json.dumps(body).encode(),
        method="POST",
        headers={"Content-Type": "application/json", "Origin": BASE},
    )
    text: list[str] = []
    tools: set[str] = set()
    asked = False
    error = ""
    event = "message"
    with urllib.request.urlopen(req, timeout=timeout) as r:
        for raw in r:
            line = raw.decode("utf-8", "replace").rstrip("\n")
            if line.startswith("event:"):
                event = line[6:].strip()
                continue
            if not line.startswith("data:"):
                continue
            p = line[5:].strip()
            if p == "[DONE]":
                break
            try:
                d = json.loads(p)
            except Exception:
                d = p
            if event == "token" and isinstance(d, str):
                text.append(d)
            elif event == "activity" and isinstance(d, str):
                # "🔧 read_file…" / "🔧 exec_script…"
                if "🔧" in d:
                    tools.add(d.split("🔧")[-1].strip().strip("…").strip())
            elif event == "question":
                asked = True
                # question 载荷含提问正文，是「已向用户确认」的关键证据（此时正文流已中断）
                try:
                    q = json.loads(p) if isinstance(p, str) else p
                    for item in q.get("questions") or []:
                        text.append(str(item.get("question") or ""))
                        for o in item.get("options") or []:
                            text.append(str(o))
                except Exception:
                    text.append(str(p))
                break
            elif event == "error":
                error = str(d)[:200]
                break
            elif event == "done":
                break
    return {"text": "".join(text), "tools": tools, "asked": asked, "error": error}


def cleanup(session_ids):
    for sid in session_ids:
        try:
            urllib.request.urlopen(
                urllib.request.Request(
                    f"{BASE}/api/session/{sid}", method="DELETE", headers={"Origin": BASE}
                ),
                timeout=10,
            ).read()
        except Exception:
            pass


def test_01_topic_eval_routes_to_detailed_skill():
    sid = "eval-route"
    try:
        r = chat(
            "帮我评估「AI 编程工具的记忆机制」这个选题适不适合我的账号，只做评估不用写文章。", sid
        )
        assert not r["error"], f"流错误：{r['error']}"
        read_skill = any("read_file" in t for t in r["tools"]) or "topic-evaluator" in r["text"]
        semantic = any(k in r["text"] for k in ("评估", "评分", "赛道", "建议", "角度"))
        assert read_skill and semantic, f"证据不足 tools={r['tools']} 尾部={r['text'][-400:]!r}"
    finally:
        cleanup([sid])


def test_02_paid_op_asks_first():
    sid = "eval-paid"
    try:
        r = chat(
            "按 ai-image-gen 技能用 AI 文生图给我画一张赛博城市夜景，横版。"
            "这是付费操作，按规则先确认。",
            sid,
        )
        assert not r["error"], f"流错误：{r['error']}"
        # 不变量：确认前不得发起付费调用。载体不限（ask_human 卡片或正文征询），
        # 但必须有「待确认」证据，且不得有「已执行」证据。
        cost_terms = ("费用", "确认", "预估", "付费", "范围", "调用", "单价")
        pending_terms = ("确认后", "你点头", "是否", "等你", "请回复", "等你确认", "再发起")
        # 只认「真生成了图」的表述；「已调用 check 脚本」之类不算（离线检查无费用）
        executed_terms = ("已生成", "已出图", "图已保存", "生成完成", "成品已落盘")
        semantic = any(k in r["text"] for k in cost_terms)
        pending = r["asked"] or any(k in r["text"] for k in pending_terms)
        executed = any(k in r["text"] for k in executed_terms)
        assert semantic and pending and not executed, (
            f"付费门失效：semantic={semantic} pending={pending} executed={executed} "
            f"尾部={r['text'][-400:]!r}"
        )
    finally:
        cleanup([sid])


def test_03_reversible_task_runs_without_asking():
    sid = "eval-reversible"
    try:
        r = chat("读一下我的画像，告诉我我是谁。直接读，不要问。", sid)
        assert not r["error"], f"流错误：{r['error']}"
        assert not r["asked"], "可逆任务不应触发提问"
        assert len(r["text"]) > 20, f"回复过短：{r['text'][:100]!r}"
        # 语言硬约束回归：正文须以中文为主（探针曾实测到整段英文回复）
        zh = sum(1 for c in r["text"] if "\u4e00" <= c <= "\u9fff")
        assert zh >= max(20, len(r["text"]) * 0.15), (
            f"回复疑似非中文主导（中文字符 {zh}/{len(r['text'])}）：{r['text'][:200]!r}"
        )
    finally:
        cleanup([sid])


def test_04_cross_session_memory():
    s1, s2 = "eval-mem-a", "eval-mem-b"
    try:
        r1 = chat("记住：以后我的封面都用克莱因蓝极简风。请记录到长期记忆。", s1)
        assert not r1["error"], f"记录轮出错：{r1['error']}"
        r2 = chat("我的封面风格偏好是什么？查一下长期记忆。", s2)
        assert not r2["error"], f"检索轮出错：{r2['error']}"
        assert "克莱因蓝" in r2["text"], f"跨会话未检索到，尾部={r2['text'][-400:]!r}"
        provenance = any(k in r2["text"] for k in ("记忆", "来源", "重要度", "明确陈述"))
        assert provenance, f"缺溯源标注，尾部={r2['text'][-300:]!r}"
    finally:
        cleanup([s1, s2])


def test_05_model_fallback_switches():
    """主模型指向必连不上的端口 → 备用模型接手并正常回复。"""
    bad_port = _free_port()
    port = _free_port()
    env = dict(os.environ)
    env.update(
        {
            "PYTHONUTF8": "1",
            "OPENAI_BASE_URL": f"http://127.0.0.1:{bad_port}/v1",
            "OPENAI_API_KEY": _key(),
            "ZIMEITI_FALLBACK_MODELS": "deepseek-chat@https://api.deepseek.com",
        }
    )
    log = Path("/tmp/evals-fallback.log")
    with log.open("w", encoding="utf-8") as lf:
        proc = subprocess.Popen(
            [sys.executable, "-m", "zimeiti_api", "--port", str(port)],
            cwd=str(API_DIR),
            env=env,
            stdout=lf,
            stderr=lf,
        )
    base = f"http://127.0.0.1:{port}"
    sid = "eval-fallback"
    try:
        for _ in range(40):
            try:
                urllib.request.urlopen(
                    urllib.request.Request(f"{base}/api/status", headers={"Origin": base}),
                    timeout=3,
                ).read()
                break
            except Exception:
                time.sleep(1)
        # chat() 绑定模块级 BASE，本用例独立实例 → 内联请求
        req = urllib.request.Request(
            f"{base}/api/chat/stream",
            data=json.dumps({"message": "只回复两个字：收到", "sessionId": sid}).encode(),
            method="POST",
            headers={"Content-Type": "application/json", "Origin": base},
        )
        text, error = [], ""
        with urllib.request.urlopen(req, timeout=300) as resp:
            for raw in resp:
                line = raw.decode("utf-8", "replace").rstrip("\n")
                if line.startswith("event:"):
                    ev = line[6:].strip()
                    continue
                if not line.startswith("data:"):
                    continue
                p = line[5:].strip()
                if p == "[DONE]":
                    break
                if ev == "error":
                    error = p[:200]
                    break
                if ev == "token":
                    try:
                        text.append(json.loads(p))
                    except Exception:
                        pass
        reply = "".join(text)
        assert not error, f"fallback 未生效：{error}"
        assert len(reply) > 0, "fallback 后无回复"
        assert "未配置模型" not in reply
        assert "model-fallback" in log.read_text(encoding="utf-8", errors="replace"), (
            "日志无切换记录"
        )
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except Exception:
            proc.kill()
        try:
            urllib.request.urlopen(
                urllib.request.Request(
                    f"{base}/api/session/{sid}", method="DELETE", headers={"Origin": base}
                ),
                timeout=10,
            ).read()
        except Exception:
            pass
