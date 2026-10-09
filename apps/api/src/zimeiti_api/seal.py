"""凭证加密落盘 CLI（宪法 II：凭证只存密文）。

用法：
    uv run python -m zimeiti_api.seal <account>

从环境变量读取平台凭证并加密写入 data/credentials/<account>.sealed：
  - gzh 账号：WECHAT_MP_APPID / WECHAT_MP_APPSECRET → {"app_id","app_secret"}
环境变量缺失时 fail-closed 拒绝，不落任何明文。
"""

import os
import sys


def main(argv: list[str] | None = None) -> int:
    from dotenv import load_dotenv

    load_dotenv()  # 凭证通常写在 apps/api/.env，与 config 同一加载约定
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("用法: uv run python -m zimeiti_api.seal <account>  （如 gzh-main）")
        return 2
    account = argv[0]
    app_id = os.environ.get("WECHAT_MP_APPID", "")
    app_secret = os.environ.get("WECHAT_MP_APPSECRET", "")
    if not app_id or not app_secret:
        print("[FAIL] 缺少 WECHAT_MP_APPID / WECHAT_MP_APPSECRET 环境变量，拒绝落盘（fail-closed）")
        return 1
    from zimeiti_api.credentials import save_account_credentials

    path = save_account_credentials(account, {"app_id": app_id, "app_secret": app_secret})
    print(f"[OK] 已加密保存 {account} 凭证 → {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
