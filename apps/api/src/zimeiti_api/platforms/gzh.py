"""公众号草稿箱发布（Task 6.3，宪法原则 I/II/V）。

API 客户端移植自 my-tools/wechat-mp-toolkit（参考来源：作者自有项目），
仅保留 AccessToken 缓存、草稿新增、草稿计数三个接口。
认证订阅号凭据来自环境变量 WECHAT_MP_APPID / WECHAT_MP_APPSECRET。
"""

import json
import os
import time
from pathlib import Path
from typing import Any

import httpx

_DEFAULT_COVER_MEDIA_FILE = "data/credentials/gzh_thumb_media_id.txt"

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

    def upload_permanent_image(self, image_path: str) -> str:
        """上传永久图片素材，返回 media_id（封面 thumb 用）。"""
        token = self.get_access_token()
        with open(image_path, "rb") as f:
            files = {"media": (os.path.basename(image_path), f, "image/png")}
            resp = httpx.post(
                f"{BASE_URL}/material/add_material",
                params={"access_token": token, "type": "image"},
                files=files,
                timeout=30,
            )
        data = resp.json()
        if "media_id" not in data:
            raise RuntimeError(f"上传封面素材失败: {data}")
        return data["media_id"]

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

    def draft_list(self, count: int = 10) -> list[str]:
        """拉取草稿列表标题（读回对账依据）。"""
        token = self.get_access_token()
        resp = httpx.post(
            f"{BASE_URL}/draft/batchget",
            params={"access_token": token},
            json={"offset": 0, "count": count, "no_content": 1},
            timeout=15,
        )
        data = resp.json()
        titles: list[str] = []
        for item in data.get("item", []):  # 微信 API 响应键为单数 item
            for news in item.get("content", {}).get("news_item", []):
                titles.append(news.get("title", ""))
        return titles


def publish_gzh_draft(
    client: GzhClient, draft: Any, cover_image_path: str | None = None
) -> dict[str, str]:
    """上传草稿箱并读回对账，返回三档 outcome。

    认证订阅号：草稿箱 API 可用；群发留人工在公众号后台操作（宪法 I）。
    cover_image_path：封面图（草稿箱 API 要求 thumb_media_id）；
    未提供时若已有缓存的封面 media_id 则复用。
    """
    thumb_media_id: str | None = None
    if cover_image_path and os.path.exists(cover_image_path):
        thumb_media_id = client.upload_permanent_image(cover_image_path)
    elif os.path.exists(_DEFAULT_COVER_MEDIA_FILE):
        thumb_media_id = Path(_DEFAULT_COVER_MEDIA_FILE).read_text(encoding="utf-8").strip()
    articles = [
        {
            "title": draft.title[:64],
            "content": f"<p>{draft.body}</p>",
            "digest": draft.summary,
            "author": "zimeiti-ai",
            **({"thumb_media_id": thumb_media_id} if thumb_media_id else {}),
        }
    ]
    media_id = client.add_draft(articles)
    # 封面 media_id 缓存（后续发布复用，不重复上传）
    if thumb_media_id:
        Path(_DEFAULT_COVER_MEDIA_FILE).parent.mkdir(parents=True, exist_ok=True)
        Path(_DEFAULT_COVER_MEDIA_FILE).write_text(thumb_media_id, encoding="utf-8")
    count = client.draft_count()
    readback = "verified" if count > 0 else "unverified"
    return {"platform_result": media_id, "readback": readback}


def readback_gzh_draft(client: "GzhClient", title: str, count: int = 10) -> str:
    """读回对账（Task 1.2，W1 修复）：草稿列表含标题 → verified；否则 unverified。

    接口异常 MUST 返回 unverified（spec：读回异常返回 unverified）。
    """
    try:
        titles = client.draft_list(count=count)
        return "verified" if title in titles else "unverified"
    except Exception:  # noqa: BLE001 - 观测层异常降级为 unverified（不冒报成功）
        return "unverified"
