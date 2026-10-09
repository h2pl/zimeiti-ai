"""公众号草稿箱发布（Task 6.3，宪法原则 I/II/V）。

API 客户端移植自 my-tools/wechat-mp-toolkit（参考来源：作者自有项目），
仅保留 AccessToken 缓存、草稿新增、草稿计数三个接口。
认证订阅号凭据来自环境变量 WECHAT_MP_APPID / WECHAT_MP_APPSECRET。
"""

import json
import time
from pathlib import Path
from typing import Any

import httpx

from zimeiti_api.config import DATABASE_URL  # noqa: F401 - 保持 config 加载 .env

BASE_URL = "https://api.weixin.qq.com/cgi-bin"


class GzhClient:
    """公众号 API 客户端（最小子集）。"""

    def __init__(self, app_id: str, app_secret: str, token_cache: Path | None = None):
        self.app_id = app_id
        self.app_secret = app_secret
        self._cache = Path(token_cache) if token_cache else Path(".wechat_token_cache.json")

    def get_access_token(self, force: bool = False) -> str:
        """获取 access_token，本地缓存避免频繁请求。"""
        now = time.time()
        self._cache.parent.mkdir(parents=True, exist_ok=True)
        if not force and self._cache.exists():
            try:
                cached = json.loads(self._cache.read_text(encoding="utf-8"))
                if cached.get("expires_at", 0) > now + 60:
                    return cached["access_token"]
            except (json.JSONDecodeError, KeyError):
                pass
        resp = httpx.get(
            f"{BASE_URL}/token",
            params={
                "grant_type": "client_credential",
                "appid": self.app_id,
                "secret": self.app_secret,
            },
            timeout=15,
        )
        data = resp.json()
        if "access_token" not in data:
            raise RuntimeError(f"获取 access_token 失败: {data}")
        self._cache.write_text(
            json.dumps(
                {"access_token": data["access_token"], "expires_at": now + data["expires_in"]}
            ),
            encoding="utf-8",
        )
        return data["access_token"]

    def add_draft(self, articles: list[dict[str, Any]]) -> str:
        """新增草稿，返回 media_id。"""
        token = self.get_access_token()
        resp = httpx.post(
            f"{BASE_URL}/draft/add",
            params={"access_token": token},
            json={"articles": articles},
            timeout=15,
        )
        data = resp.json()
        if "media_id" not in data:
            raise RuntimeError(f"新增草稿失败: {data}")
        return data["media_id"]

    def draft_count(self) -> int:
        """草稿总数（读回对账用）。"""
        token = self.get_access_token()
        resp = httpx.get(f"{BASE_URL}/draft/count", params={"access_token": token}, timeout=15)
        return resp.json().get("total_count", 0)


def publish_gzh_draft(client: GzhClient, draft: Any) -> dict[str, str]:
    """上传草稿箱并读回对账，返回三档 outcome。

    认证订阅号：草稿箱 API 可用；群发留人工在公众号后台操作（宪法 I）。
    """
    articles = [
        {
            "title": draft.title[:64],
            "content": f"<p>{draft.body}</p>",
            "digest": draft.summary,
            "author": "zimeiti-ai",
        }
    ]
    media_id = client.add_draft(articles)
    count = client.draft_count()
    readback = "verified" if count > 0 else "unverified"
    return {"platform_result": media_id, "readback": readback}
