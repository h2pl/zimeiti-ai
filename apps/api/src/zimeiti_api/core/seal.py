"""凭证加密落盘 CLI（宪法 II：凭证只存密文）。

用法：
    uv run python -m zimeiti_api.core.seal <account>

从环境变量/登录态读取平台凭证并加密写入 data/credentials/<account>.sealed：
  - gzh 账号：WECHAT_MP_APPID / WECHAT_MP_APPSECRET → {"app_id","app_secret"}
  - xhs 账号：data/login/xhs_state.json 登录态内容 → {"login_state", "sealed_at"}
    （xhs 实际会话由 xiaohongshu-mcp 服务持有；sealed 凭证作为
     PublishExecutor 凭证前置门禁的「已登录证明」，参考 tools._account_credentials）
环境变量/登录态缺失时 fail-closed 拒绝，不落任何明文。
"""

import os
import sys
from datetime import datetime


def main(argv: list[str] | None = None) -> int:
    from dotenv import load_dotenv

    load_dotenv()  # 凭证通常写在 apps/api/.env，与 config 同一加载约定
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("用法: uv run python -m zimeiti_api.core.seal <account>  （如 gzh-main / xhs-main）")
        return 2
    account = argv[0]

    from zimeiti_api.core.credentials import save_account_credentials

    if account.startswith("xhs"):
        from zimeiti_api.config import LOGIN_STATE_PATH

        state_file = os.environ.get("XHS_LOGIN_STATE", LOGIN_STATE_PATH)
        if not os.path.exists(state_file):
            print(f"[FAIL] xhs 登录态不存在：{state_file}（先运行 xiaohongshu-login 扫码）")
            return 1
        payload = {
            "login_state": open(state_file, encoding="utf-8").read(),  # noqa: PTH123 - 密文内持久化
            "sealed_at": datetime.now().isoformat(timespec="seconds"),
        }
        path = save_account_credentials(account, payload)
        print(f"[OK] 已加密保存 {account} 登录态凭证 → {path}")
        return 0

    app_id = os.environ.get("WECHAT_MP_APPID", "")
    app_secret = os.environ.get("WECHAT_MP_APPSECRET", "")
    if not app_id or not app_secret:
        print("[FAIL] 缺少 WECHAT_MP_APPID / WECHAT_MP_APPSECRET 环境变量，拒绝落盘（fail-closed）")
        return 1
    path = save_account_credentials(account, {"app_id": app_id, "app_secret": app_secret})
    print(f"[OK] 已加密保存 {account} 凭证 → {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
