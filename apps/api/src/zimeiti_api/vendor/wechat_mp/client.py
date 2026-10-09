"""微信公众号 API 客户端

vendor 来源：E:/Projects/my-tools/wechat-mp-toolkit/src/wechat_mp/client.py（v0.1.0）

封装微信公众号平台（认证订阅号）全部可用 API：
  - AccessToken 管理（自动缓存与刷新）
  - 素材管理（永久素材上传、获取、删除、列表）
  - 临时素材管理（图片/语音/视频/缩略图上传与下载）
  - 草稿管理（新增、获取、删除、修改、列表、计数）
  - 发布管理（提交发布、发布状态、已发布文章列表）
  - 群发消息（文本/图片/图文/视频群发、预览、删除、状态查询、速度控制）
  - 留言管理（打开/关闭留言、精选、删除、回复）
  - 自定义菜单（创建/查询/删除、个性化菜单）
  - 用户管理（关注者列表、用户信息、备注、黑名单）
  - 用户标签（创建/查询/编辑/删除、打标签/取消标签）
  - 二维码（临时/永久带参二维码、短链转换）
  - 客服管理（账号增删改查、客服消息发送、输入状态）
  - 自动回复（查询当前自动回复规则）
  - JS-SDK（jsapi_ticket 缓存与签名生成）
  - 网页授权 OAuth2（授权链接生成、code 换 token、获取用户信息）
  - 数据统计（用户增减/累计、图文阅读/转发/分享、消息分发、被动回复）
  - 基础工具（服务器 IP 列表、清空配额）

本地唯一改动：删除 config.py 依赖，app_id/app_secret 改为必传构造参数
（凭证由 zimeiti_api.credentials Fernet 解密后注入，宪法 II 凭证只存密文）。
"""

import json
import os
import time
from pathlib import Path
from typing import Optional

try:
    import requests
except ImportError:
    raise ImportError("需要 requests 库: pip install requests")

BASE_URL = "https://api.weixin.qq.com/cgi-bin"


class WeChatClient:
    """微信公众号 API 客户端"""

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        token_cache: Optional[str] = None,
    ):
        self.app_id = app_id
        self.app_secret = app_secret
        self._token_cache_path = Path(
            token_cache or Path(__file__).parent.parent.parent / ".wechat_token_cache.json"
        )

    # ─── AccessToken ────────────────────────────────────────────────

    def get_access_token(self, force_refresh: bool = False) -> str:
        """获取 access_token，自动缓存避免频繁请求

        Args:
            force_refresh: 强制重新获取（清除缓存）
        """
        now = time.time()

        if not force_refresh and self._token_cache_path.exists():
            try:
                cached = json.loads(self._token_cache_path.read_text())
                if cached.get("expires_at", 0) > now + 60:
                    return cached["access_token"]
            except (json.JSONDecodeError, KeyError):
                pass

        if not self.app_id or not self.app_secret:
            raise ValueError(
                "公众号凭据缺失：app_id/app_secret 必须由调用方注入"
                "（zimeiti-ai 从加密凭证 data/credentials/<account>.sealed 解密获得）"
            )

        resp = requests.get(
            f"{BASE_URL}/token",
            params={
                "grant_type": "client_credential",
                "appid": self.app_id,
                "secret": self.app_secret,
            },
            timeout=10,
        )
        data = resp.json()
        if "access_token" not in data:
            raise RuntimeError(f"获取 access_token 失败: {data}")

        self._token_cache_path.write_text(json.dumps({
            "access_token": data["access_token"],
            "expires_at": now + data.get("expires_in", 7200) - 300,
        }))

        return data["access_token"]

    def _invalidate_token_cache(self):
        """清除 token 缓存，下次调用时强制重新获取"""
        if self._token_cache_path.exists():
            try:
                self._token_cache_path.unlink()
            except OSError:
                pass

    def _post(self, path: str, body: dict = None, params: dict = None, timeout: int = 30) -> dict:
        """发送 POST 请求，40001 错误自动刷新 token 重试一次"""
        if params is None:
            params = {"access_token": self.get_access_token()}
        elif "access_token" not in params:
            params["access_token"] = self.get_access_token()

        resp = requests.post(
            f"{BASE_URL}/{path}",
            params=params,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8") if body else None,
            json=None if body else None,
            headers={"Content-Type": "application/json"},
            timeout=timeout,
        )
        data = json.loads(resp.content.decode("utf-8"))
        if data.get("errcode") == 40001:
            params["access_token"] = self.get_access_token(force_refresh=True)
            resp = requests.post(
                f"{BASE_URL}/{path}",
                params=params,
                data=json.dumps(body, ensure_ascii=False).encode("utf-8") if body else None,
                json=None if body else None,
                headers={"Content-Type": "application/json"},
                timeout=timeout,
            )
            data = json.loads(resp.content.decode("utf-8"))
        return data

    def _get(self, path: str, params: dict = None, timeout: int = 15) -> dict:
        """发送 GET 请求，40001 错误自动刷新 token 重试一次"""
        if params is None:
            params = {"access_token": self.get_access_token()}
        elif "access_token" not in params:
            params["access_token"] = self.get_access_token()

        resp = requests.get(f"{BASE_URL}/{path}", params=params, timeout=timeout)
        data = json.loads(resp.content.decode("utf-8"))
        if data.get("errcode") == 40001:
            params["access_token"] = self.get_access_token(force_refresh=True)
            resp = requests.get(f"{BASE_URL}/{path}", params=params, timeout=timeout)
            data = json.loads(resp.content.decode("utf-8"))
        return data

    # ─── 永久素材管理 ────────────────────────────────────────────────

    def upload_thumb(self, image_path: str) -> str:
        """上传封面图片（永久素材），返回 media_id"""
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片文件不存在: {image_path}")

        def _do_upload():
            with open(image_path, "rb") as f:
                return requests.post(
                    f"{BASE_URL}/material/add_material",
                    params={"access_token": self.get_access_token(), "type": "thumb"},
                    files={"media": (os.path.basename(image_path), f, "image/jpeg")},
                    timeout=30,
                ).json()

        data = _do_upload()
        if data.get("errcode") == 40001:
            self.get_access_token(force_refresh=True)  # 强制刷新 token
            data = _do_upload()
        if "media_id" not in data:
            raise RuntimeError(f"上传封面失败: {data}")
        return data["media_id"]

    def upload_image(self, image_path: str) -> dict:
        """上传图文正文内的图片，返回微信 CDN URL（用于文章正文内嵌，不占用素材库配额）"""
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片文件不存在: {image_path}")

        def _do_upload():
            with open(image_path, "rb") as f:
                return requests.post(
                    f"{BASE_URL}/media/uploadimg",
                    params={"access_token": self.get_access_token()},
                    files={"media": (os.path.basename(image_path), f, "image/jpeg")},
                    timeout=30,
                ).json()

        data = _do_upload()
        if data.get("errcode") == 40001:
            self.get_access_token(force_refresh=True)  # 强制刷新 token
            data = _do_upload()
        if "url" not in data:
            raise RuntimeError(f"上传图片失败: {data}")
        return data

    def add_material(self, image_path: str, title: str = "") -> dict:
        """新增永久素材（图片），返回 media_id 和 url"""
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片文件不存在: {image_path}")

        params = {"access_token": self.get_access_token(), "type": "image"}
        files = {"media": (os.path.basename(image_path), open(image_path, "rb"), "image/jpeg")}
        data_extra = {}
        if title:
            data_extra["description"] = json.dumps({"title": title}, ensure_ascii=False)

        resp = requests.post(
            f"{BASE_URL}/material/add_material",
            params=params,
            files=files,
            data=data_extra if data_extra else None,
            timeout=30,
        )
        data = resp.json()
        if "media_id" not in data:
            raise RuntimeError(f"新增永久素材失败: {data}")
        return data

    def get_material(self, media_id: str) -> dict:
        """获取永久素材"""
        return self._post("material/get_material", {"media_id": media_id})

    def delete_material(self, media_id: str) -> dict:
        """删除永久素材"""
        data = self._post("material/del_material", {"media_id": media_id})
        if data.get("errcode", -1) != 0:
            raise RuntimeError(f"删除素材失败: {data}")
        return data

    def count_materials(self) -> dict:
        """获取素材总数"""
        return self._post("material/get_materialcount")

    def list_materials(self, media_type: str = "image", offset: int = 0, count: int = 20) -> dict:
        """获取素材列表

        Args:
            media_type: 素材类型 image/voice/video/news
            offset: 偏移量
            count: 数量（1-20）
        """
        return self._post("material/batchget_material", {
            "type": media_type,
            "offset": offset,
            "count": count,
        })

    # ─── 临时素材管理 ────────────────────────────────────────────────
    # 临时素材有效期 3 天，主要用于客服消息、群发消息等场景

    def upload_media(self, file_path: str, media_type: str = "image") -> dict:
        """上传临时素材（图片/语音/视频/缩略图），有效期3天

        Args:
            file_path: 本地文件路径
            media_type: 素材类型 image/voice/video/thumb
        Returns:
            含 media_id / type / created_at 的 dict
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        mime_map = {
            "image": "image/jpeg",
            "voice": "audio/amr",
            "video": "video/mp4",
            "thumb": "image/jpeg",
        }
        mime = mime_map.get(media_type, "application/octet-stream")

        def _do_upload():
            with open(file_path, "rb") as f:
                return requests.post(
                    f"{BASE_URL}/media/upload",
                    params={"access_token": self.get_access_token(), "type": media_type},
                    files={"media": (os.path.basename(file_path), f, mime)},
                    timeout=60,
                ).json()

        data = _do_upload()
        if data.get("errcode") == 40001:
            self.get_access_token(force_refresh=True)
            data = _do_upload()
        if "media_id" not in data:
            raise RuntimeError(f"上传临时素材失败: {data}")
        return data

    def get_media_url(self, media_id: str) -> str:
        """获取临时素材的下载 URL

        Args:
            media_id: 临时素材的 media_id（3天有效）
        Returns:
            可直接下载的完整 URL
        """
        from urllib.parse import quote
        return (
            f"{BASE_URL}/media/get"
            f"?access_token={self.get_access_token()}&media_id={quote(media_id)}"
        )

    def get_jssdk_voice_url(self, media_id: str) -> str:
        """获取 JS-SDK uploadVoice 上传的临时语音素材下载 URL（speex 格式，16K 采样率）"""
        from urllib.parse import quote
        return (
            f"{BASE_URL}/media/get/jssdk"
            f"?access_token={self.get_access_token()}&media_id={quote(media_id)}"
        )

    # ─── 草稿管理 ──────────────────────────────────────────────────

    def add_draft(
        self,
        title: str,
        content: str,
        *,
        author: str = "",
        thumb_media_id: str = "",
        content_source_url: str = "",
        digest: str = "",
        need_open_comment: int = 1,
        only_fans_can_comment: int = 0,
        pic_crop_235_1: str = "",
        pic_crop_1_1: str = "",
    ) -> str:
        """新增图文草稿，返回 media_id

        Args:
            pic_crop_235_1: 2.35:1 封面裁剪坐标，格式 "X1_Y1_X2_Y2"（0~1 比例值）
            pic_crop_1_1: 1:1 封面裁剪坐标，格式 "X1_Y1_X2_Y2"（0~1 比例值）
        """
        article = {"title": title, "content": content}
        if author:
            article["author"] = author
        if thumb_media_id:
            article["thumb_media_id"] = thumb_media_id
        if content_source_url:
            article["content_source_url"] = content_source_url
        if digest:
            article["digest"] = digest
        article["need_open_comment"] = need_open_comment
        article["only_fans_can_comment"] = only_fans_can_comment
        if pic_crop_235_1:
            article["pic_crop_235_1"] = pic_crop_235_1
        if pic_crop_1_1:
            article["pic_crop_1_1"] = pic_crop_1_1

        data = self._post("draft/add", {"articles": [article]})
        if "media_id" not in data:
            raise RuntimeError(f"创建草稿失败: {data}")
        return data["media_id"]

    def get_draft(self, media_id: str) -> dict:
        """获取草稿详情"""
        return self._post("draft/get", {"media_id": media_id})

    def delete_draft(self, media_id: str) -> dict:
        """删除草稿"""
        data = self._post("draft/delete", {"media_id": media_id})
        if data.get("errcode", -1) != 0:
            raise RuntimeError(f"删除草稿失败: {data}")
        return data

    def update_draft(self, media_id: str, index: int, article: dict) -> dict:
        """修改草稿

        注意：articles 中 thumb_media_id 和 content 均为必填字段。
        微信文档将 thumb_media_id 标注为选填，但实际缺失时返回 40007；
        缺失 content 时返回 44004。两者都容易误导。
        如果之前只传了部分字段导致 40007，补全 thumb_media_id + content 即可。

        Args:
            media_id: 草稿 media_id
            index: 文章在草稿中的位置（从 0 开始）
            article: 修改后的文章字段（thumb_media_id 和 content 必填）
        """
        body = {"media_id": media_id, "index": index, "articles": article}
        data = self._post("draft/update", body)
        if data.get("errcode", -1) != 0:
            raise RuntimeError(f"修改草稿失败: {data}")
        return data

    def list_drafts(self, offset: int = 0, count: int = 20) -> dict:
        """获取草稿列表"""
        data = self._post("draft/batchget", {
            "offset": offset,
            "count": count,
            "no_content": 1,
        })
        if "errcode" in data and data["errcode"] != 0:
            raise RuntimeError(f"获取草稿列表失败: {data}")
        return data

    def count_drafts(self) -> int:
        """获取草稿总数"""
        data = self._post("draft/count")
        if "total_count" not in data:
            raise RuntimeError(f"获取草稿数量失败: {data}")
        return data["total_count"]

    # ─── 已发布文章管理 ──────────────────────────────────────────────

    def list_articles(self, offset: int = 0, count: int = 20) -> dict:
        """获取已发布文章列表"""
        data = self._post("freepublish/batchget", {
            "offset": offset,
            "count": count,
            "no_content": 1,
        })
        if "errcode" in data and data["errcode"] != 0:
            raise RuntimeError(f"获取已发布文章失败: {data}")
        return data

    def delete_article(self, article_id: str) -> dict:
        """删除已发布文章"""
        data = self._post("freepublish/delete", {"article_id": article_id})
        if data.get("errcode", -1) != 0:
            raise RuntimeError(f"删除文章失败: {data}")
        return data

    # ─── 留言管理 ──────────────────────────────────────────────────

    def open_comment(self, msg_data_id: str, index: int = 0) -> dict:
        """打开已群发文章的留言"""
        data = self._post("comment/open", {"msg_data_id": msg_data_id, "index": index})
        if data.get("errcode", -1) != 0:
            raise RuntimeError(f"打开留言失败: {data}")
        return data

    def close_comment(self, msg_data_id: str, index: int = 0) -> dict:
        """关闭已群发文章的留言"""
        data = self._post("comment/close", {"msg_data_id": msg_data_id, "index": index})
        if data.get("errcode", -1) != 0:
            raise RuntimeError(f"关闭留言失败: {data}")
        return data

    def list_comments(self, msg_data_id: str, index: int = 0, begin: int = 0, count: int = 50, comment_type: int = 0) -> dict:
        """获取文章留言列表

        Args:
            msg_data_id: 群发返回的 msg_data_id
            index: 多图文中的位置
            begin: 起始位置
            count: 获取数量（最多50）
            comment_type: 0=全部, 1=普通评论, 2=精选评论
        """
        data = self._post("comment/list", {
            "msg_data_id": msg_data_id,
            "index": index,
            "begin": begin,
            "count": count,
            "type": comment_type,
        })
        if data.get("errcode", -1) != 0:
            raise RuntimeError(f"获取留言失败: {data}")
        return data

    def mark_comment_elect(self, comment_id: int) -> dict:
        """将留言标记为精选"""
        data = self._post("comment/markelect", {"comment_id": comment_id})
        if data.get("errcode", -1) != 0:
            raise RuntimeError(f"精选留言失败: {data}")
        return data

    def unmark_comment_elect(self, comment_id: int) -> dict:
        """取消留言精选"""
        data = self._post("comment/unmarkelect", {"comment_id": comment_id})
        if data.get("errcode", -1) != 0:
            raise RuntimeError(f"取消精选失败: {data}")
        return data

    def delete_comment(self, comment_id: int) -> dict:
        """删除留言"""
        data = self._post("comment/delete", {"comment_id": comment_id})
        if data.get("errcode", -1) != 0:
            raise RuntimeError(f"删除留言失败: {data}")
        return data

    def reply_comment(self, msg_data_id: str, index: int, comment_id: int, content: str) -> dict:
        """回复留言"""
        data = self._post("comment/reply/add", {
            "msg_data_id": msg_data_id,
            "index": index,
            "comment_id": comment_id,
            "content": content,
        })
        if data.get("errcode", -1) != 0:
            raise RuntimeError(f"回复留言失败: {data}")
        return data

    def delete_comment_reply(self, comment_id: int, reply_id: int) -> dict:
        """删除留言回复"""
        data = self._post("comment/reply/delete", {
            "comment_id": comment_id,
            "reply_id": reply_id,
        })
        if data.get("errcode", -1) != 0:
            raise RuntimeError(f"删除回复失败: {data}")
        return data

    def _check(self, data: dict, action: str) -> dict:
        """统一校验 errcode，非 0 抛错"""
        if data.get("errcode", 0) not in (0, None):
            raise RuntimeError(f"{action}失败: {data}")
        return data

    # ─── 自定义菜单 ────────────────────────────────────────────────

    def create_menu(self, buttons: list) -> dict:
        """创建自定义菜单

        Args:
            buttons: 菜单按钮列表（最多3个一级菜单，每个一级最多5个二级）
                示例: [{"type": "click", "name": "今日歌曲", "key": "MUSIC"},
                       {"name": "菜单", "sub_button": [
                           {"type": "view", "name": "搜索", "url": "https://..."}]}]
        """
        return self._check(self._post("menu/create", {"button": buttons}), "创建菜单")

    def get_menu(self) -> dict:
        """查询当前菜单（含个性化菜单）"""
        return self._get("menu/get")

    def delete_menu(self) -> dict:
        """删除全部自定义菜单（含个性化菜单）"""
        return self._check(self._get("menu/delete"), "删除菜单")

    def get_menu_config(self) -> dict:
        """获取自定义菜单配置（含后台手动配置的菜单，is_menu_open 等）"""
        return self._get("get_current_selfmenu_info")

    def add_conditional_menu(self, buttons: list, matchrule: dict) -> dict:
        """创建个性化菜单，返回 menuid

        Args:
            buttons: 菜单按钮列表
            matchrule: 匹配规则，如 {"tag_id": "2", "sex": "1",
                       "country": "中国", "province": "广东", "city": "广州",
                       "client_platform_type": "2", "language": "zh_CN"}
        """
        data = self._post("menu/addconditional", {"button": buttons, "matchrule": matchrule})
        if "menuid" not in data:
            raise RuntimeError(f"创建个性化菜单失败: {data}")
        return data

    def delete_conditional_menu(self, menuid: str) -> dict:
        """删除指定个性化菜单"""
        return self._check(self._post("menu/delconditional", {"menuid": menuid}), "删除个性化菜单")

    def try_match_menu(self, user_id: str) -> dict:
        """测试个性化菜单匹配结果

        Args:
            user_id: 粉丝 openid 或微信号
        """
        return self._post("menu/trymatch", {"user_id": user_id})

    # ─── 用户管理 ──────────────────────────────────────────────────

    def list_users(self, next_openid: str = "") -> dict:
        """获取关注者 openid 列表（一次最多1万）"""
        params = {"access_token": self.get_access_token()}
        if next_openid:
            params["next_openid"] = next_openid
        return self._get("user/get", params)

    def get_user_info(self, openid: str, lang: str = "zh_CN") -> dict:
        """获取单个用户基本信息（含 UnionID）"""
        return self._get("user/info", {
            "access_token": self.get_access_token(),
            "openid": openid,
            "lang": lang,
        })

    def batch_get_user_info(self, openids: list, lang: str = "zh_CN") -> dict:
        """批量获取用户信息（最多100个）"""
        user_list = [{"openid": o, "lang": lang} for o in openids]
        return self._post("user/info/batchget", {"user_list": user_list})

    def update_user_remark(self, openid: str, remark: str) -> dict:
        """设置用户备注名（最多30字符）"""
        return self._check(self._post("user/info/updateremark", {
            "openid": openid, "remark": remark,
        }), "设置备注名")

    # ─── 黑名单管理 ────────────────────────────────────────────────

    def get_blacklist(self, begin_openid: str = "") -> dict:
        """获取黑名单列表"""
        return self._post("tags/members/getblacklist", {"begin_openid": begin_openid})

    def batch_blacklist(self, openids: list) -> dict:
        """批量拉黑用户（最多20个）"""
        return self._check(self._post("tags/members/batchblacklist",
                                      {"openid_list": openids}), "拉黑用户")

    def batch_unblacklist(self, openids: list) -> dict:
        """批量取消拉黑用户（最多20个）"""
        return self._check(self._post("tags/members/batchunblacklist",
                                      {"openid_list": openids}), "取消拉黑")

    # ─── 用户标签 ──────────────────────────────────────────────────

    def create_tag(self, name: str) -> dict:
        """创建标签（最多100个，名称最长30字节）"""
        data = self._post("tags/create", {"tag": {"name": name}})
        if "tag" not in data:
            raise RuntimeError(f"创建标签失败: {data}")
        return data

    def list_tags(self) -> dict:
        """获取已创建的标签列表"""
        return self._get("tags/get")

    def update_tag(self, tag_id: int, name: str) -> dict:
        """编辑标签"""
        return self._check(self._post("tags/update",
                                      {"tag": {"id": tag_id, "name": name}}), "编辑标签")

    def delete_tag(self, tag_id: int) -> dict:
        """删除标签"""
        return self._check(self._post("tags/delete", {"tag": {"id": tag_id}}), "删除标签")

    def get_tag_users(self, tag_id: int, next_openid: str = "") -> dict:
        """获取某标签下的粉丝列表"""
        return self._post("user/tag/get", {"tagid": tag_id, "next_openid": next_openid})

    def batch_tagging(self, tag_id: int, openids: list) -> dict:
        """批量为用户打标签（最多50个）"""
        return self._check(self._post("tags/members/batchtagging",
                                      {"tagid": tag_id, "openid_list": openids}), "打标签")

    def batch_untagging(self, tag_id: int, openids: list) -> dict:
        """批量为用户取消标签（最多50个）"""
        return self._check(self._post("tags/members/batchuntagging",
                                      {"tagid": tag_id, "openid_list": openids}), "取消标签")

    def get_user_tags(self, openid: str) -> dict:
        """获取用户身上的标签列表"""
        return self._post("tags/getidlist", {"openid": openid})

    # ─── 二维码 ────────────────────────────────────────────────────

    def create_qrcode_temp(self, scene: "int|str", expire_seconds: int = 604800) -> dict:
        """创建临时带参二维码

        Args:
            scene: 场景值，int 走 scene_id，str 走 scene_str
            expire_seconds: 有效秒数，最大 2592000（30天）
        """
        if isinstance(scene, int):
            action_info = {"scene": {"scene_id": scene}}
        else:
            action_info = {"scene": {"scene_str": str(scene)}}
        data = self._post("qrcode/create", {
            "expire_seconds": expire_seconds,
            "action_name": "QR_SCENE" if isinstance(scene, int) else "QR_STR_SCENE",
            "action_info": action_info,
        })
        if "ticket" not in data:
            raise RuntimeError(f"创建临时二维码失败: {data}")
        return data

    def create_qrcode_limit(self, scene: "int|str") -> dict:
        """创建永久带参二维码

        Args:
            scene: int 走 scene_id（最大10万），str 走 scene_str
        """
        if isinstance(scene, int):
            action_name = "QR_LIMIT_SCENE"
            action_info = {"scene": {"scene_id": scene}}
        else:
            action_name = "QR_LIMIT_STR_SCENE"
            action_info = {"scene": {"scene_str": str(scene)}}
        data = self._post("qrcode/create", {
            "action_name": action_name,
            "action_info": action_info,
        })
        if "ticket" not in data:
            raise RuntimeError(f"创建永久二维码失败: {data}")
        return data

    def get_qrcode_url(self, ticket: str) -> str:
        """通过 ticket 换取二维码图片的展示 URL"""
        from urllib.parse import quote
        return f"https://mp.weixin.qq.com/cgi-bin/showqrcode?ticket={quote(ticket)}"

    def long2short(self, long_url: str) -> dict:
        """将长链接转成短链接（long2shorturl）"""
        data = self._post("shorturl", {"action": "long2short", "long_url": long_url})
        if "short_url" not in data:
            raise RuntimeError(f"长链转短链失败: {data}")
        return data

    # ─── 客服管理 ──────────────────────────────────────────────────

    def list_kf_accounts(self) -> dict:
        """获取所有客服账号"""
        return self._get("customservice/getkflist")

    def add_kf_account(self, kf_account: str, nickname: str) -> dict:
        """添加客服账号

        Args:
            kf_account: 完整客服账号，格式 账号前缀@公众号微信号
        """
        return self._check(self._post("customservice/kfaccount/add",
                                      {"kf_account": kf_account, "nickname": nickname}), "添加客服")

    def update_kf_account(self, kf_account: str, nickname: str) -> dict:
        """修改客服账号昵称"""
        return self._check(self._post("customservice/kfaccount/update",
                                      {"kf_account": kf_account, "nickname": nickname}), "修改客服")

    def delete_kf_account(self, kf_account: str) -> dict:
        """删除客服账号"""
        return self._check(self._get("customservice/kfaccount/del",
                                     {"access_token": self.get_access_token(),
                                      "kf_account": kf_account}), "删除客服")

    def send_kf_text(self, openid: str, content: str, kf_account: str = "") -> dict:
        """发送客服文本消息（仅限用户48小时内有交互）

        Args:
            kf_account: 指定以某个客服身份发送（可选）
        """
        body = {"touser": openid, "msgtype": "text", "text": {"content": content}}
        if kf_account:
            body["customservice"] = {"kf_account": kf_account}
        return self._check(self._post("message/custom/send", body), "发送客服消息")

    def send_kf_image(self, openid: str, media_id: str) -> dict:
        """发送客服图片消息（media_id 支持临时素材或永久素材）"""
        return self._check(self._post("message/custom/send", {
            "touser": openid, "msgtype": "image", "image": {"media_id": media_id},
        }), "发送客服图片")

    def send_kf_news(self, openid: str, articles: list) -> dict:
        """发送客服图文消息（图文链接卡片，点击跳转外链）

        Args:
            openid: 用户 openid
            articles: 图文列表，每项含 title/description/url/picurl
        """
        return self._check(self._post("message/custom/send", {
            "touser": openid, "msgtype": "news", "news": {"articles": articles},
        }), "发送客服图文")

    def send_kf_typing(self, openid: str, command: str = "Typing") -> dict:
        """下发客服输入状态（Typing/CancelTyping）"""
        return self._check(self._post("message/custom/typing",
                                      {"touser": openid, "command": command}), "下发输入状态")

    # ─── 自动回复（只读） ──────────────────────────────────────────

    def get_autoreply_info(self) -> dict:
        """获取公众号当前的自动回复规则（关注回复/消息回复/关键词回复）

        注意：微信仅开放查询，设置自动回复需在公众平台后台手动操作。
        """
        return self._get("get_current_autoreply_info")

    # ─── JS-SDK ────────────────────────────────────────────────────

    def get_jsapi_ticket(self, force_refresh: bool = False) -> str:
        """获取 jsapi_ticket（用于 JS-SDK 签名），带缓存"""
        cache_path = self._token_cache_path.with_name(".wechat_jsapi_ticket_cache.json")
        now = time.time()
        if not force_refresh and cache_path.exists():
            try:
                cached = json.loads(cache_path.read_text())
                if cached.get("expires_at", 0) > now + 60:
                    return cached["ticket"]
            except (json.JSONDecodeError, KeyError):
                pass
        data = self._get("ticket/getticket", {
            "access_token": self.get_access_token(), "type": "jsapi",
        })
        if data.get("ticket"):
            cache_path.write_text(json.dumps({
                "ticket": data["ticket"],
                "expires_at": now + data.get("expires_in", 7200) - 300,
            }))
            return data["ticket"]
        raise RuntimeError(f"获取 jsapi_ticket 失败: {data}")

    def get_jsapi_signature(self, url: str) -> dict:
        """生成 JS-SDK config 所需的签名信息

        Args:
            url: 当前网页完整 URL（不含 # 及其后部分）
        Returns:
            含 appId / timestamp / nonceStr / signature 的 dict
        """
        import hashlib
        import secrets
        ticket = self.get_jsapi_ticket()
        noncestr = secrets.token_hex(8)
        timestamp = str(int(time.time()))
        raw = f"jsapi_ticket={ticket}&noncestr={noncestr}&timestamp={timestamp}&url={url}"
        signature = hashlib.sha1(raw.encode("utf-8")).hexdigest()
        return {
            "appId": self.app_id,
            "timestamp": timestamp,
            "nonceStr": noncestr,
            "signature": signature,
        }

    # ─── 网页授权（OAuth2，sns 域） ────────────────────────────────

    def get_oauth_url(self, redirect_uri: str, scope: str = "snsapi_userinfo",
                      state: str = "") -> str:
        """生成网页授权跳转 URL（引导用户点击）

        Args:
            redirect_uri: 授权后回调地址（需在后台配置授权域名，会自动 urlencode）
            scope: snsapi_base（静默，仅 openid）或 snsapi_userinfo（弹窗，含用户信息）
            state: 自定义参数，回调时原样带回
        """
        from urllib.parse import quote
        return (
            "https://open.weixin.qq.com/connect/oauth2/authorize"
            f"?appid={self.app_id}&redirect_uri={quote(redirect_uri, safe='')}"
            f"&response_type=code&scope={scope}&state={state}#wechat_redirect"
        )

    def oauth_get_access_token(self, code: str) -> dict:
        """用网页授权 code 换取网页授权 access_token + openid（sns 域，独立于普通 token）"""
        resp = requests.get("https://api.weixin.qq.com/sns/oauth2/access_token", params={
            "appid": self.app_id, "secret": self.app_secret,
            "code": code, "grant_type": "authorization_code",
        }, timeout=10)
        data = resp.json()
        if "access_token" not in data:
            raise RuntimeError(f"网页授权换 token 失败: {data}")
        return data

    def oauth_get_user_info(self, oauth_access_token: str, openid: str,
                            lang: str = "zh_CN") -> dict:
        """用网页授权 token 拉取用户信息（scope 需为 snsapi_userinfo）"""
        resp = requests.get("https://api.weixin.qq.com/sns/userinfo", params={
            "access_token": oauth_access_token, "openid": openid, "lang": lang,
        }, timeout=10)
        data = json.loads(resp.content.decode("utf-8"))
        if "openid" not in data:
            raise RuntimeError(f"获取网页授权用户信息失败: {data}")
        return data

    # ─── 数据统计 ──────────────────────────────────────────────────

    def _datacube(self, path: str, begin_date: str, end_date: str) -> dict:
        """数据统计通用调用（日期格式 YYYY-MM-DD，跨度按接口限制）"""
        return self._post(f"datacube/{path}",
                          {"begin_date": begin_date, "end_date": end_date})

    # -- 用户数据 --

    def get_user_summary(self, begin_date: str, end_date: str) -> dict:
        """获取用户增减数据（最大跨度7天）"""
        return self._datacube("getusersummary", begin_date, end_date)

    def get_user_cumulate(self, begin_date: str, end_date: str) -> dict:
        """获取累计用户数据（最大跨度7天）"""
        return self._datacube("getusercumulate", begin_date, end_date)

    # -- 图文数据 --

    def get_article_summary(self, begin_date: str, end_date: str) -> dict:
        """获取图文群发每日数据（最大跨度1天）"""
        return self._datacube("getarticlesummary", begin_date, end_date)

    def get_article_total(self, begin_date: str, end_date: str) -> dict:
        """获取图文群发总数据（最大跨度1天）"""
        return self._datacube("getarticletotal", begin_date, end_date)

    def get_user_read(self, begin_date: str, end_date: str) -> dict:
        """获取图文阅读概况数据（最大跨度3天）"""
        return self._datacube("getuserread", begin_date, end_date)

    def get_user_read_hour(self, begin_date: str, end_date: str) -> dict:
        """获取图文阅读分时数据（最大跨度1天）"""
        return self._datacube("getuserreadhour", begin_date, end_date)

    def get_user_share(self, begin_date: str, end_date: str) -> dict:
        """获取图文转发概况数据（最大跨度7天）"""
        return self._datacube("getusershare", begin_date, end_date)

    def get_user_share_hour(self, begin_date: str, end_date: str) -> dict:
        """获取图文转发分时数据（最大跨度1天）"""
        return self._datacube("getusersharehour", begin_date, end_date)

    def get_article_read(self, begin_date: str, end_date: str) -> dict:
        """获取发表内容阅读指标（最大跨度3天）"""
        return self._datacube("getarticleread", begin_date, end_date)

    def get_article_share(self, begin_date: str, end_date: str) -> dict:
        """获取发表内容分享指标（最大跨度3天）"""
        return self._datacube("getarticleshare", begin_date, end_date)

    def get_biz_summary(self, begin_date: str, end_date: str) -> dict:
        """获取发表内容汇总概览数据（最大跨度1天）"""
        return self._datacube("getbizsummary", begin_date, end_date)

    def get_article_total_detail(self, begin_date: str, end_date: str) -> dict:
        """获取发表内容详细数据（最大跨度1天）"""
        return self._datacube("getarticletotaldetail", begin_date, end_date)

    # -- 消息数据 --

    def get_upstream_msg(self, begin_date: str, end_date: str) -> dict:
        """获取消息发送概况数据（用户上行消息，最大跨度7天）"""
        return self._datacube("getupstreammsg", begin_date, end_date)

    def get_upstream_msg_hour(self, begin_date: str, end_date: str) -> dict:
        """获取消息发送分时统计数据（最大跨度1天）"""
        return self._datacube("getupstreammsghour", begin_date, end_date)

    def get_upstream_msg_week(self, begin_date: str, end_date: str) -> dict:
        """获取消息发送周数据（最大跨度30天）"""
        return self._datacube("getupstreammsgweek", begin_date, end_date)

    def get_upstream_msg_month(self, begin_date: str, end_date: str) -> dict:
        """获取消息发送月数据（最大跨度30天）"""
        return self._datacube("getupstreammsgmonth", begin_date, end_date)

    def get_upstream_msg_dist(self, begin_date: str, end_date: str) -> dict:
        """获取消息发送分布数据（最大跨度15天）"""
        return self._datacube("getupstreammsgdist", begin_date, end_date)

    def get_upstream_msg_dist_week(self, begin_date: str, end_date: str) -> dict:
        """获取消息发送分布周数据（最大跨度30天）"""
        return self._datacube("getupstreammsgdistweek", begin_date, end_date)

    def get_upstream_msg_dist_month(self, begin_date: str, end_date: str) -> dict:
        """获取消息发送分布月数据（最大跨度30天）"""
        return self._datacube("getupstreammsgdistmonth", begin_date, end_date)

    # -- 接口数据 --

    def get_interface_summary(self, begin_date: str, end_date: str) -> dict:
        """获取被动回复数据（最大跨度30天）"""
        return self._datacube("getinterfacesummary", begin_date, end_date)

    def get_interface_summary_hour(self, begin_date: str, end_date: str) -> dict:
        """获取被动回复分时数据（最大跨度1天）"""
        return self._datacube("getinterfacesummaryhour", begin_date, end_date)

    # ─── 基础工具 ──────────────────────────────────────────────────

    def get_api_domain_ip(self) -> dict:
        """获取微信 API 接口 IP 地址列表"""
        return self._get("get_api_domain_ip")

    def get_callback_ip(self) -> dict:
        """获取微信服务器回调 IP 地址列表"""
        return self._get("getcallbackip")

    def clear_quota(self) -> dict:
        """清空接口调用次数配额（每月10次）"""
        return self._check(self._post("clear_quota", {"appid": self.app_id}), "清空配额")

    # ─── 群发消息 ────────────────────────────────────────────────────

    def mass_send_text(self, content: str, tag_id: Optional[int] = None,
                       is_to_all: bool = True) -> dict:
        """群发文本消息

        Args:
            content: 文本内容
            tag_id: 按标签群发；为 None 且 is_to_all=True 时群发给所有关注者
            is_to_all: True=群发给所有人（tag_id 不为 None 时生效）
        """
        filter_rule = {"is_to_all": is_to_all}
        if tag_id is not None:
            filter_rule["tag_id"] = tag_id
        return self._check(self._post("message/mass/sendall", {
            "filter": filter_rule,
            "text": {"content": content},
            "msgtype": "text",
        }), "群发文本")

    def mass_send_image(self, media_id: str, tag_id: Optional[int] = None,
                        is_to_all: bool = True) -> dict:
        """群发图片消息（需先上传临时或永久图片素材）"""
        filter_rule = {"is_to_all": is_to_all}
        if tag_id is not None:
            filter_rule["tag_id"] = tag_id
        return self._check(self._post("message/mass/sendall", {
            "filter": filter_rule,
            "image": {"media_id": media_id},
            "msgtype": "image",
        }), "群发图片")

    def mass_send_news(self, media_id: str, tag_id: Optional[int] = None,
                       is_to_all: bool = True) -> dict:
        """群发图文消息（需先通过草稿接口或素材管理创建图文素材）"""
        filter_rule = {"is_to_all": is_to_all}
        if tag_id is not None:
            filter_rule["tag_id"] = tag_id
        return self._check(self._post("message/mass/sendall", {
            "filter": filter_rule,
            "mpnews": {"media_id": media_id},
            "msgtype": "mpnews",
        }), "群发图文")

    def mass_send_video(self, media_id: str, title: str = "", description: str = "",
                        tag_id: Optional[int] = None, is_to_all: bool = True) -> dict:
        """群发视频消息

        注意：视频需先通过 upload_media 上传临时素材获取 media_id，
        再通过 upload_mass_video 转换为群发可用的 media_id。
        """
        filter_rule = {"is_to_all": is_to_all}
        if tag_id is not None:
            filter_rule["tag_id"] = tag_id
        body = {
            "filter": filter_rule,
            "mpvideo": {"media_id": media_id},
            "msgtype": "mpvideo",
        }
        if title:
            body["mpvideo"]["title"] = title
        if description:
            body["mpvideo"]["description"] = description
        return self._check(self._post("message/mass/sendall", body), "群发视频")

    def upload_mass_video(self, media_id: str, title: str, description: str = "") -> dict:
        """将临时视频素材转为群发专用素材，返回新的 media_id

        Args:
            media_id: 通过 upload_media 上传的临时视频 media_id
            title: 视频标题
            description: 视频描述
        """
        body = {"media_id": media_id, "title": title}
        if description:
            body["description"] = description
        data = self._post("media/uploadvideo", body)
        if "media_id" not in data:
            raise RuntimeError(f"转换群发视频素材失败: {data}")
        return data

    def mass_send_voice(self, media_id: str, tag_id: Optional[int] = None,
                        is_to_all: bool = True) -> dict:
        """群发语音消息"""
        filter_rule = {"is_to_all": is_to_all}
        if tag_id is not None:
            filter_rule["tag_id"] = tag_id
        return self._check(self._post("message/mass/sendall", {
            "filter": filter_rule,
            "voice": {"media_id": media_id},
            "msgtype": "voice",
        }), "群发语音")

    def mass_preview_text(self, content: str, openid: str) -> dict:
        """预览群发文本消息（发送给指定 openid 测试效果）"""
        return self._check(self._post("message/mass/preview", {
            "touser": openid,
            "text": {"content": content},
            "msgtype": "text",
        }), "预览群发文本")

    def mass_preview_news(self, media_id: str, openid: str) -> dict:
        """预览群发图文消息"""
        return self._check(self._post("message/mass/preview", {
            "touser": openid,
            "mpnews": {"media_id": media_id},
            "msgtype": "mpnews",
        }), "预览群发图文")

    def mass_preview_image(self, media_id: str, openid: str) -> dict:
        """预览群发图片消息"""
        return self._check(self._post("message/mass/preview", {
            "touser": openid,
            "image": {"media_id": media_id},
            "msgtype": "image",
        }), "预览群发图片")

    def mass_delete(self, msg_id: int, article_idx: int = 0) -> dict:
        """删除群发消息

        Args:
            msg_id: 群发消息的 msg_id
            article_idx: 要删除的文章在图文消息中的位置（从0开始），0=删除整条
        """
        body = {"msg_id": msg_id}
        if article_idx > 0:
            body["article_idx"] = article_idx
        return self._check(self._post("message/mass/delete", body), "删除群发")

    def get_mass_status(self, msg_id: int) -> dict:
        """查询群发消息发送状态

        Returns:
            msg_status: 1=成功, 2=发送中, 3=已删除, 4=发送失败
        """
        return self._post("message/mass/get", {"msg_id": msg_id})

    def set_mass_speed(self, speed: int) -> dict:
        """设置群发速度

        Args:
            speed: 0=最快, 1=中等, 2=较慢, 3=慢（默认0）
        """
        return self._check(self._post("message/mass/speed/set", {
            "speed": speed, "realspeed": speed,
        }), "设置群发速度")

    def get_mass_speed(self) -> dict:
        """获取当前群发速度设置"""
        return self._post("message/mass/speed/get", {})
