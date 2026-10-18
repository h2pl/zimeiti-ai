"""wechat-bridge-transport 端到端探针：真实 zimeiti + 假 ilink transport。

验证闭环：微信消息（假）→ zimeiti agent（真实服务，无密钥优雅降级，零 token）
→ 回发（假 transport 记录）。另验证会话稳定性、「新会话」指令、后端不可达的
如实提示。不接真微信（真扫码联调步骤见 apps/wechat/README）。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8123"
ROOT = Path(__file__).resolve().parent.parent.parent  # 仓库根（scripts 在 apps/scripts 下）
WECHAT_DIR = ROOT / "apps" / "wechat"
FAILS: list[str] = []


def check(name: str, ok: bool, extra: str = "") -> None:
    print(f"{'[PASS]' if ok else '[FAIL]'} {name}{(' — ' + extra) if extra else ''}")
    if not ok:
        FAILS.append(name)


def run_driver(messages: list[dict], state_dir: str, base: str = BASE) -> dict:
    env = dict(os.environ, ZIMEITI_API=base, WECHAT_STATE_DIR=state_dir, PYTHONUTF8="1")
    proc = subprocess.run(
        ["node", "tools/driver_probe.mjs"],
        input=json.dumps(messages).encode(), capture_output=True, timeout=300,
        cwd=str(WECHAT_DIR), env=env,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"driver 失败：{proc.stderr.decode()[:300]}")
    return json.loads(proc.stdout.decode())


def main() -> int:
    # 服务应由调用方（run.sh 段）先起好；这里只自证连通
    try:
        with urllib.request.urlopen(f"{BASE}/api/status", timeout=5) as r:
            r.read()
    except Exception as e:  # noqa: BLE001
        print(f"[FAIL] zimeiti 服务未就绪（{BASE}）：{e}")
        return 1

    with tempfile.TemporaryDirectory() as td:
        # 1) 两条消息：闭环 + 会话稳定 + typing 先行
        r1 = run_driver([
            {"from_user_id": "u-probe-1", "content": "你好"},
            {"from_user_id": "u-probe-1", "content": "继续聊聊"},
        ], td)
        sent = r1["sent"]
        check("两条消息都有回发", len(sent) == 2, f"sent={len(sent)}")
        check("回发对象正确", all(s["to"] == "u-probe-1" for s in sent))
        check("回复非空", all(s["content"].strip() for s in sent), sent[0]["content"][:60] if sent else "")
        check("同用户会话稳定", len(set(r1["sessionIds"])) == 1 and len(r1["sessionIds"]) == 2,
              str(r1["sessionIds"]))
        check("typing 先行", r1["typings"].count("u-probe-1") >= 1)

        # 2) 「新会话」指令：不进 agent，映射重置
        r2 = run_driver([
            {"from_user_id": "u-probe-2", "content": "第一句"},
            {"from_user_id": "u-probe-2", "content": "新会话"},
            {"from_user_id": "u-probe-2", "content": "第二句"},
        ], td)
        check("指令回发确认", any("新会话" in s["content"] for s in r2["sent"]))
        check("指令不产生 agent 调用", len(r2["sessionIds"]) == 2, str(r2["sessionIds"]))
        check("指令后仍是同会话派生", r2["sessionIds"][0] == r2["sessionIds"][1])

        # 3) 不同用户：独立会话
        r3 = run_driver([
            {"from_user_id": "u-a", "content": "hi"},
            {"from_user_id": "u-b", "content": "hi"},
        ], td)
        check("不同用户会话独立", len(set(r3["sessionIds"])) == 2, str(r3["sessionIds"]))

    # 4) 后端不可达：如实提示（指向一个没人监听的端口）
    with tempfile.TemporaryDirectory() as td2:
        proc = subprocess.run(
            ["node", "tools/driver_probe.mjs"],
            input=json.dumps([{"from_user_id": "u-x", "content": "在吗"}]).encode(),
            capture_output=True, timeout=120, cwd=str(WECHAT_DIR),
            env=dict(os.environ, ZIMEITI_API="http://127.0.0.1:9",
                     WECHAT_STATE_DIR=td2, PYTHONUTF8="1"),
        )
        out = json.loads(proc.stdout.decode())
        msg = out["sent"][0]["content"] if out["sent"] else ""
        check("后端不可达时用户收到可行动提示", "不可达" in msg or "稍后" in msg, msg[:80])

    print(f"\n小结: {'PASS' if not FAILS else 'FAIL ' + ','.join(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
