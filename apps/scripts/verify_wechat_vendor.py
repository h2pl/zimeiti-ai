"""微信桥 vendor 合规与完整性守卫（wechat-bridge-scaffold，随 make check 执行）。

三条断言（对应规格）：
1. 合规三件套：vendor LICENSE + 仓库 NOTICE（含包名/版本/「未改动」声明）
2. vendor 完整性：全部文件与 MANIFEST.json 的内容哈希一致（防改动/漂移）
3. 零 openclaw 引擎依赖：apps/wechat 源码（vendor 除外）不得 import openclaw
   引擎；对 openclaw/plugin-sdk/* 的引用必须落在 shim exports 声明的子路径内
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
WECHAT_DIR = ROOT / "apps" / "wechat"
VENDOR_DIR = WECHAT_DIR / "vendor" / "openclaw-weixin"
MANIFEST = VENDOR_DIR / "MANIFEST.json"
SHIM_PKG = WECHAT_DIR / "shim" / "openclaw" / "package.json"

FAILS: list[str] = []


def fail(msg: str) -> None:
    FAILS.append(msg)
    print(f"  - {msg}")


def check_compliance() -> None:
    print("[1/3] 合规三件套")
    if not (VENDOR_DIR / "LICENSE").is_file():
        fail("vendor/openclaw-weixin/LICENSE 缺失")
        return
    text = (VENDOR_DIR / "LICENSE").read_text(encoding="utf-8", errors="replace")
    if "MIT" not in text:
        fail("vendor LICENSE 不是 MIT")
    if "Tencent" not in text:
        fail("vendor LICENSE 缺 Tencent 版权头")

    notice_path = WECHAT_DIR / "NOTICE"
    if not notice_path.is_file():
        fail("apps/wechat/NOTICE 缺失")
        return
    notice = notice_path.read_text(encoding="utf-8", errors="replace")
    for needle in ("openclaw-weixin", "2.4.10", "MIT", "未改动"):
        if needle not in notice:
            fail(f"NOTICE 缺关键信息：{needle}")


def check_integrity() -> None:
    print("[2/3] vendor 完整性（哈希）")
    if not MANIFEST.is_file():
        fail("MANIFEST.json 缺失")
        return
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    recorded: dict[str, str] = manifest["files"]

    actual: dict[str, str] = {}
    for f in sorted(VENDOR_DIR.rglob("*")):
        if f.is_file():
            rel = f.relative_to(VENDOR_DIR).as_posix()
            if rel == "MANIFEST.json":
                continue
            actual[rel] = hashlib.sha256(f.read_bytes()).hexdigest()

    for rel, want in recorded.items():
        got = actual.get(rel)
        if got is None:
            fail(f"vendor 文件被删除：{rel}")
        elif got != want:
            fail(f"vendor 文件被改动：{rel}")
    for rel in actual:
        if rel not in recorded:
            fail(f"vendor 目录出现清单外文件：{rel}")


def check_no_openclaw_engine() -> None:
    print("[3/3] 零 openclaw 引擎依赖")
    # 3a) 源码不得 import openclaw 引擎能力（shim 只提供 plugin-sdk/*）
    sdk_import = re.compile(r"""from\s+["']openclaw/plugin-sdk/([a-z-]+)["']""")
    allowed = set()
    if SHIM_PKG.is_file():
        allowed = {m.split("/")[-1] for m in json.loads(SHIM_PKG.read_text(encoding="utf-8"))["exports"]}
    for py in list((WECHAT_DIR / "src").rglob("*.js")) + list((WECHAT_DIR / "shim").rglob("*.js")) + list((WECHAT_DIR / "test").rglob("*.js")):
        text = py.read_text(encoding="utf-8", errors="replace")
        for m in sdk_import.finditer(text):
            if m.group(1) not in allowed:
                fail(f"{py.relative_to(ROOT)}: import 了 shim 未提供的 openclaw/plugin-sdk/{m.group(1)}")
        for m in re.finditer(r"""from\s+["']openclaw["']|require\(["']openclaw["']\)""", text):
            fail(f"{py.relative_to(ROOT)}: 直接 import openclaw 引擎")

    # 3b) package.json 不得依赖 openclaw 引擎包（shim 以 file: 形式提供是允许的）
    pkg = json.loads((WECHAT_DIR / "package.json").read_text(encoding="utf-8"))
    dep = pkg.get("dependencies", {}).get("openclaw", "")
    if dep and not str(dep).startswith("file:"):
        fail(f"package.json 的 openclaw 依赖指向非本地 shim：{dep}")


def main() -> int:
    print("微信桥 vendor 守卫（wechat-bridge-scaffold）")
    if not WECHAT_DIR.is_dir():
        print("  (apps/wechat 不存在，跳过)")
        return 0
    check_compliance()
    check_integrity()
    check_no_openclaw_engine()
    if FAILS:
        print(f"FAIL：{len(FAILS)} 项")
        return 1
    print("PASS：合规三件套齐备、vendor 未被改动、零 openclaw 引擎依赖")
    return 0


if __name__ == "__main__":
    sys.exit(main())
