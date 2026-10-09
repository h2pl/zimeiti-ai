"""诊断 xhs API 鉴权：检查 web_session 缺失与签名连通性（不发布）。"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
import os

os.chdir(ROOT / "apps/api")

from dotenv import load_dotenv

load_dotenv()

from zimeiti_api.platforms.xhs import XhsApiClient
from zimeiti_api.platforms.xhs_signer import XhsSigner

ST = "data/login/xhs_state.json"


def main() -> int:
    data = json.loads(Path(ST).read_text(encoding="utf-8"))
    names = sorted({c["name"] for c in data["cookies"]})
    print("[diag] storage_state cookie keys:", names)
    print("[diag] web_session in storage:", "web_session" in names)

    with XhsSigner(ST) as signer:
        ctx_cookies = {c["name"] for c in signer._context.cookies()}
        print("[diag] signer browser cookies have web_session:", "web_session" in ctx_cookies)
        # 签名浏览器访问 www 后若 SSO 出 web_session，回写 storage_state 供 API 复用
        merged = signer._context.cookies()
        Path(ST).write_text(json.dumps({"cookies": merged}, ensure_ascii=False), encoding="utf-8")
        print("[diag] merged storage_state saved, keys:", sorted({c["name"] for c in merged}))

        api = XhsApiClient(storage_state=ST)
        try:
            client = api._make_client(signer)
            res = client.get_self_info()
            print("[diag] get_self_info:", json.dumps(res, ensure_ascii=False)[:300])
        except Exception as exc:  # noqa: BLE001
            print("[diag] get_self_info FAILED:", str(exc)[:300])
        try:
            client = api._make_client(signer)
            res = client.get_notes_summary()
            print("[diag] get_notes_summary(creator 内置签名):", str(res)[:200])
        except Exception as exc:  # noqa: BLE001
            print("[diag] get_notes_summary FAILED:", str(exc)[:300])
    return 0


if __name__ == "__main__":
    sys.exit(main())
