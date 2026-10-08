"""账号画像（Task 3.1/3.2）：schema 校验、加载、创作注入与多账号隔离。

存储：profiles/<account>/profile.yaml（人可读、可 git 版本化）。
必填五维：positioning/style/audience/platform_rules/preferences。
preferences（偏好红线）缺失视为致命错误。
"""

from pathlib import Path
from typing import Any

import yaml

REQUIRED_FIELDS = ("positioning", "style", "audience", "platform_rules", "preferences")
DEFAULT_BASE_DIR = Path("profiles")


def validate_profile(data: dict[str, Any]) -> bool:
    """校验画像完整性；缺失必填字段抛 ValueError 并点名缺失项。"""
    missing = [f for f in REQUIRED_FIELDS if not data.get(f)]
    if missing:
        raise ValueError(f"画像缺少必填字段: {', '.join(missing)}")
    return True


def load_profile(account: str, base_dir: Path | str | None = None) -> dict[str, Any]:
    """从 profiles/<account>/profile.yaml 加载并校验画像。"""
    base = Path(base_dir) if base_dir else DEFAULT_BASE_DIR
    f = base / account / "profile.yaml"
    if not f.exists():
        raise FileNotFoundError(f"画像文件不存在: {f}")
    data = yaml.safe_load(f.read_text(encoding="utf-8"))
    validate_profile(data)
    if data.get("account") != account:
        data["account"] = account
    return data


def build_profile_context(profile: dict[str, Any]) -> str:
    """把画像渲染为创作上下文文本（注入 agent 的 system prompt 附加段）。

    只包含本账号画像——多账号隔离由调用方保证每次仅传单一画像。
    """
    validate_profile(profile)
    return (
        f"当前账号画像「{profile['account']}」：\n"
        f"- 定位：{profile['positioning']}\n"
        f"- 风格：{profile['style']}\n"
        f"- 受众：{profile['audience']}\n"
        f"- 平台规则：{profile['platform_rules']}\n"
        f"- 偏好红线（必须遵守）：{profile['preferences']}"
    )
