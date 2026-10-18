"""wechat-bridge-media 探针：入站媒体落盘附注 + 出站 MEDIA 回发（全 fake，零网络零 token）。"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
WECHAT_DIR = ROOT / "apps" / "wechat"
FAILS: list[str] = []


def check(name: str, ok: bool, extra: str = "") -> None:
    print(f"{'[PASS]' if ok else '[FAIL]'} {name}{(' — ' + extra) if extra else ''}")
    if not ok:
        FAILS.append(name)


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        env = dict(os.environ, WECHAT_STATE_DIR=td, PYTHONUTF8="1")
        proc = subprocess.run(
            ["node", "tools/driver_media_probe.mjs"],
            capture_output=True, timeout=180, cwd=str(WECHAT_DIR), env=env,
        )
        if proc.returncode != 0:
            print(proc.stderr.decode()[:400])
            return 1
        out = json.loads(proc.stdout.decode())

    agent_saw = "\n".join(out["agentSaw"])
    check("入站图片附注路径", "用户发送了图片" in agent_saw and "已保存到" in agent_saw,
          agent_saw.replace("\n", " ")[:90])
    check("入站确认回发", any("已收到图片" in s["content"] for s in out["sent"]))
    check("入站媒体落盘", len(out["mediaDirFiles"]) >= 1, str(out["mediaDirFiles"]))
    check("出站先发文本", any(s["content"] == "这是海报" for s in out["sent"]))
    check("出站 MEDIA 行不出现",
          not any("MEDIA:" in s["content"] for s in out["sent"]))
    check("出站媒体发送", len(out["mediaSent"]) == 1
          and out["mediaSent"][0]["filePath"] == "/tmp/poster.png",
          str(out["mediaSent"]))

    print(f"\n小结: {'PASS' if not FAILS else 'FAIL ' + ','.join(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
