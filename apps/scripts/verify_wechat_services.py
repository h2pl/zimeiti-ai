"""微信桥服务单元守卫（wechat-bridge-ops，随 make check 执行）。

校验 services/ 模板的关键项（自恢复/启动前等待/路径占位符齐全），防止模板被
改坏导致「以为装上了，其实没起来」。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SERVICES = ROOT / "apps" / "wechat" / "services"

FAILS: list[str] = []


def check(name: str, ok: bool) -> None:
    print(f"  {'[PASS]' if ok else '[FAIL]'} {name}")
    if not ok:
        FAILS.append(name)


def main() -> int:
    print("微信桥服务单元守卫（wechat-bridge-ops）")
    unit = SERVICES / "zimeiti-wechat.service"
    plist = SERVICES / "com.zimeiti.wechat.plist"
    installer = SERVICES / "install-service.sh"

    if not unit.is_file() or not plist.is_file() or not installer.is_file():
        print("  (services/ 模板不齐，跳过)")
        return 0

    u = unit.read_text(encoding="utf-8")
    check("systemd: Restart=always（崩溃自恢复）", "Restart=always" in u)
    check("systemd: ExecStart 指向 index.js start", "ExecStart=" in u and "index.js" in u and "start" in u)
    check("systemd: 启动前等待 zimeiti /api/status", "/api/status" in u)
    check("systemd: 占位符齐全（__WECHAT_DIR__/__NODE_BIN__/__ZIMEITI_API__）",
          all(p in u for p in ("__WECHAT_DIR__", "__NODE_BIN__", "__ZIMEITI_API__")))
    check("systemd: WantedBy=default.target", "WantedBy=default.target" in u)

    p = plist.read_text(encoding="utf-8")
    check("launchd: KeepAlive true", "<key>KeepAlive</key>" in p and "<true/>" in p)
    check("launchd: RunAtLoad true", "<key>RunAtLoad</key>" in p)
    check("launchd: ProgramArguments 含 index.js start", "index.js" in p and "start" in p)
    check("launchd: 占位符齐全",
          all(x in p for x in ("__WECHAT_DIR__", "__NODE_BIN__", "__ZIMEITI_API__")))
    check("launchd: 日志路径", "StandardOutPath" in p)

    s = installer.read_text(encoding="utf-8")
    check("installer: 平台判别（Linux/Darwin/unsupported）",
          all(k in s for k in ("Linux", "Darwin", "unsupported")))
    check("installer: 卸载分支", "--uninstall" in s)
    check("installer: render 替换占位符", "sed" in s and "__WECHAT_DIR__" in s)

    if FAILS:
        print(f"FAIL：{len(FAILS)} 项")
        return 1
    print("PASS：systemd/launchd 模板与安装脚本关键项齐备")
    return 0


if __name__ == "__main__":
    sys.exit(main())
