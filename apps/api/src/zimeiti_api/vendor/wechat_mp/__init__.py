"""微信公众号 API 客户端（vendor 自 my-tools/wechat-mp-toolkit，v0.1.0）。

来源：E:/Projects/my-tools/wechat-mp-toolkit/src/wechat_mp/client.py
本地唯一改动（适配 zimeiti-ai）：
  1. 删除 config.py 依赖——app_id/app_secret 改为必传构造参数
     （凭证由 zimeiti_api.credentials Fernet 解密后注入，宪法 II 凭证只存密文）；
  2. 凭证缺失报错信息同步更新。
其余逻辑与上游保持一字不差（AccessToken 缓存/40001 自动刷新/全量 API 封装）。
"""
from .client import WeChatClient

__all__ = ["WeChatClient"]
