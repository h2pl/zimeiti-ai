"""结果通知 webhook（P0④，参考: Easel skill-publish-notify 的渠道推送形态）。

配置：env ZIMEITI_NOTIFY_WEBHOOK（未配置 → 静默跳过，全部动作不受影响）。
格式自动适配：飞书自定义机器人（open.feishu.cn）用其消息格式，其余统一
JSON {"event","text","ts"}（钉钉/企微/TG webhook 各自适配后续按需加）。

调用点：审批待办（hosted 中断）、发布成败、login_wall/soft_block 风控事件、
晨报摘要。通知是观测层——发送失败绝不影响主链路。
"""

import os
from datetime import datetime

import requests


def _feishu_payload(text: str) -> dict:
    return {"msg_type": "text", "content": {"text": text}}


def _generic_payload(event: str, text: str) -> dict:
    return {"event": event, "text": text, "ts": datetime.now().isoformat(timespec="seconds")}


def send(event: str, text: str) -> bool:
    """发送通知。未配置 webhook / 发送失败 → False（静默，不影响主链路）。

    URL 解析优先级：env ZIMEITI_NOTIFY_WEBHOOK > 运行时设置
    （core/settings 的 notify_webhook_url，SettingsPage 可即时修改）。
    """
    url = os.environ.get("ZIMEITI_NOTIFY_WEBHOOK", "").strip()
    if not url:
        from zimeiti_api.core.settings import get_setting

        url = get_setting("notify_webhook_url").strip()
    if not url:
        return False
    if "open.feishu.cn" in url or "feishu" in url:
        payload = _feishu_payload(f"[{event}] {text}")
    else:
        payload = _generic_payload(event, text)
    try:
        resp = requests.post(url, json=payload, timeout=10)
        return 200 <= resp.status_code < 300
    except Exception:  # noqa: BLE001 - 通知是观测层，失败静默
        return False
