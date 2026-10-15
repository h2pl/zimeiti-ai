"""微信公众号配置管理

支持三种配置方式（优先级从高到低）：
  1. 代码中直接传参: WeChatClient(app_id=..., app_secret=...)
  2. 配置文件: ~/.wechat-mp.json
  3. 环境变量: WECHAT_MP_APPID / WECHAT_MP_APPSECRET
"""

import json
import os
from pathlib import Path
from typing import Optional

CONFIG_PATH = Path.home() / ".wechat-mp.json"


def load_config() -> dict:
    """加载配置，合并配置文件和环境变量"""
    config = {}

    # 从配置文件读取
    if CONFIG_PATH.exists():
        try:
            config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    # 环境变量覆盖
    if os.environ.get("WECHAT_MP_APPID"):
        config["app_id"] = os.environ["WECHAT_MP_APPID"]
    if os.environ.get("WECHAT_MP_APPSECRET"):
        config["app_secret"] = os.environ["WECHAT_MP_APPSECRET"]

    return config


def save_config(app_id: str, app_secret: str, **extra) -> Path:
    """保存配置到 ~/.wechat-mp.json，支持额外字段如名片信息"""
    config = {
        "app_id": app_id,
        "app_secret": app_secret,
    }
    config.update(extra)
    CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    return CONFIG_PATH


def update_config(**fields) -> Path:
    """更新配置中的部分字段，保留已有配置"""
    config = load_config()
    config.update(fields)
    CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    return CONFIG_PATH


def get_app_id() -> Optional[str]:
    """获取 app_id"""
    return load_config().get("app_id")


def get_app_secret() -> Optional[str]:
    """获取 app_secret"""
    return load_config().get("app_secret")
