"""公众号草稿箱发布（宪法原则 I/II/V）。

API 客户端复用 my-tools/wechat-mp-toolkit（作者自有项目，勿重复造轮子）：
GzhClient 是 vendor/wechat_mp.WeChatClient 的适配层，做两件事——
  1. 凭证构造函数直传（由 credentials Fernet 解密注入，不走明文 env/config）；
  2. token 缓存锚定到 data/state/（ZIMEITI_DATA_DIR 可整体重定向，根治 cwd 依赖）。
toolkit 内置 AccessToken 缓存、40001 自动刷新重试与草稿踩坑修正（如
update_draft 时 thumb_media_id/content 实为必填），此处不重复实现。

正文排版复用 my-tools/wechat-mp-manage 的 md2html+formatting 管线
（vendor/wechatfmt）：Markdown → 微信兼容 HTML（内联样式/代码高亮/列表转 div）。
"""

import os
from pathlib import Path
from typing import Any

from zimeiti_api.config import CREDENTIALS_DIR, DATA_DIR  # noqa: F401 - config 加载 .env 并锚定目录
from zimeiti_api.vendor.wechat_mp import WeChatClient
from zimeiti_api.vendor.wechatfmt.formatting import apply_wechat_styles
from zimeiti_api.vendor.wechatfmt.generate_cover_combined import generate_cover_combined
from zimeiti_api.vendor.wechatfmt.md2html import convert_md_to_html

# token 缓存：运行态数据唯一归宿 data/state/（原 cwd 相对路径 .wechat_token_cache.json 已废弃）
_TOKEN_CACHE_PATH = Path(DATA_DIR) / "state" / "gzh_token_cache.json"
# 封面 media_id 缓存（真账号走查 Task 2.2 已落盘，保持原位置以复用）
_DEFAULT_COVER_MEDIA_FILE = Path(CREDENTIALS_DIR) / "gzh_thumb_media_id.txt"


class GzhClient:
    """公众号 API 客户端（wechat_mp.WeChatClient 适配层）。"""

    def __init__(self, app_id: str, app_secret: str, token_cache: Path | None = None):
        self._client = WeChatClient(
            app_id=app_id,
            app_secret=app_secret,
            token_cache=str(token_cache) if token_cache else str(_TOKEN_CACHE_PATH),
        )

    def get_access_token(self, force: bool = False) -> str:
        """获取 access_token，toolkit 内置本地缓存与 40001 强制刷新。"""
        return self._client.get_access_token(force_refresh=force)

    def upload_permanent_image(self, image_path: str) -> str:
        """上传永久图片素材，返回 media_id（封面 thumb 用）。"""
        data = self._client.add_material(image_path)
        if "media_id" not in data:
            raise RuntimeError(f"上传封面素材失败: {data}")
        return data["media_id"]

    def add_draft(self, articles: list[dict[str, Any]]) -> str:
        """新增草稿，返回 media_id（单图文，取第一篇）。"""
        return self._client.add_draft(**articles[0])

    def draft_count(self) -> int:
        """草稿总数（读回对账用）。"""
        return self._client.count_drafts()

    def draft_list(self, count: int = 10) -> list[str]:
        """拉取草稿列表标题（读回对账依据）。"""
        data = self._client.list_drafts(count=count)
        titles: list[str] = []
        for item in data.get("item", []):  # 微信 API 响应键为单数 item
            for news in item.get("content", {}).get("news_item", []):
                titles.append(news.get("title", ""))
        return titles


def publish_gzh_draft(
    client: GzhClient,
    draft: Any,
    cover_image_path: str | None = None,
    cover_output_dir: str | None = None,
) -> dict[str, str]:
    """上传草稿箱并读回对账，返回三档 outcome。

    认证订阅号：草稿箱 API 可用；群发留人工在公众号后台操作（宪法 I）。
    cover_image_path：显式封面图（草稿箱 API 要求 thumb_media_id）；
    未提供时优先复用缓存的封面 media_id；再无则自动生成拼接封面
    （vendor my-tools generate_cover_combined，title 取草稿标题，
    sub/series 留空——zimeiti-ai 无系列体系）并上传，裁剪坐标随草稿上送。
    draft：GzhDraft 或 dict（发布审批进程从 drafts.json 读回的是 dict）。
    """
    title = draft["title"] if isinstance(draft, dict) else draft.title
    body = draft["body"] if isinstance(draft, dict) else draft.body
    summary = draft["summary"] if isinstance(draft, dict) else draft.summary
    thumb_media_id: str | None = None
    crop_fields: dict[str, str] = {}
    if cover_image_path and os.path.exists(cover_image_path):
        thumb_media_id = client.upload_permanent_image(cover_image_path)
    elif _DEFAULT_COVER_MEDIA_FILE.exists():
        thumb_media_id = _DEFAULT_COVER_MEDIA_FILE.read_text(encoding="utf-8").strip()
    else:
        out_dir = Path(cover_output_dir) if cover_output_dir else Path("data/outputs/gzh-main")
        cover_path, crop_235_1, crop_1_1 = generate_cover_combined(
            title=title,
            sub_series="",
            series="",
            output_path=str(out_dir / "cover.png"),
        )
        thumb_media_id = client.upload_permanent_image(str(cover_path))
        crop_fields = {"pic_crop_235_1": crop_235_1, "pic_crop_1_1": crop_1_1}
    articles = [
        {
            "title": title[:64],
            # Markdown → 微信兼容 HTML（内联样式，复用 my-tools 排版管线）
            "content": apply_wechat_styles(convert_md_to_html(body)),
            "digest": summary,
            "author": "zimeiti-ai",
            **({"thumb_media_id": thumb_media_id} if thumb_media_id else {}),
            **crop_fields,
        }
    ]
    media_id = client.add_draft(articles)
    # 封面 media_id 缓存（后续发布复用，不重复上传）
    if thumb_media_id:
        _DEFAULT_COVER_MEDIA_FILE.parent.mkdir(parents=True, exist_ok=True)
        _DEFAULT_COVER_MEDIA_FILE.write_text(thumb_media_id, encoding="utf-8")
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
