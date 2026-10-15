"""微信公众号 API 客户端库"""
__version__ = "0.1.0"

from .client import WeChatClient
from .config import load_config, save_config, update_config, get_app_id, get_app_secret
