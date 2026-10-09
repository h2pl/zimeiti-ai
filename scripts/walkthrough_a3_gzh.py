"""Task 2.2 真账号走查 A3-gzh：真实创作 → 合规 → 草稿箱上传 → 读回 verified。

证据落盘：data/outputs/gzh-main/<slug>/drafts.json + 审计 JSONL + 本脚本输出。
频控：PublishExecutor daily_limit=2（宪法 III）。
"""

import asyncio
import base64
import json
import os
import sys
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    from asyncio import WindowsSelectorEventLoopPolicy

    asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
os.chdir(ROOT / "apps/api")

from dotenv import load_dotenv

load_dotenv()

from zimeiti_api import audit
from zimeiti_api.compliance import ComplianceGate
from zimeiti_api.creation import create_drafts
from zimeiti_api.models import get_model
from zimeiti_api.platforms.gzh import GzhClient
from zimeiti_api.profiles import load_profile
from zimeiti_api.publisher import PublishExecutor
from zimeiti_api.tools import real_platform_router
from zimeiti_api.topics import select_topic

SLUG = datetime.now().strftime("%Y%m%d-%H%M%S")
OUT_DIR = Path("data/outputs/gzh-main") / SLUG
TOPIC_TITLE = "实测：用 AI Agent 把公众号排版时间从 1 小时压到 3 分钟"

def make_png(width: int = 900, height: int = 383, rgb: tuple = (26, 26, 46)) -> bytes:
    """纯标准库生成纯色 PNG（公众号封面 2.35:1）。"""
    import struct
    import zlib

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    raw = b"".join(b"\x00" + bytes(rgb) * width for _ in range(height))
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw))
            + chunk(b"IEND", b""))


def prepare_default_cover() -> Path:
    cover = Path("data/credentials/gzh_default_cover.png")
    cover.parent.mkdir(parents=True, exist_ok=True)
    if not cover.exists():
        cover.write_bytes(make_png())
    return cover


async def main() -> int:
    print("[A3-gzh] 开始真账号走查")
    profile = load_profile("gzh-main")
    topic = select_topic({
        "title": TOPIC_TITLE,
        "reason": "A3 验收走查（用户确认执行）",
        "direction": "以 zimeiti-ai 项目实测为主线，讲清 agent 自动排版提效的路径",
    })

    model = get_model()
    drafts = create_drafts(model, topic, profile)
    gate = ComplianceGate()
    review = gate.review(drafts.gzh.body)
    if not review["passed"]:
        print("[BLOCKED] 合规未通过:", review["violations"])
        return 2
    print(f"[A2] 草稿生成并过合规：标题={drafts.gzh.title!r} 正文 {len(drafts.gzh.body)} 字")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "drafts.json").write_text(
        json.dumps(
            {"topic": topic.title, "account": "gzh-main", "created_at": SLUG,
             "compliance": review, "drafts": {"gzh": vars(drafts.gzh)}},
            ensure_ascii=False, indent=2, default=str,
        ),
        encoding="utf-8",
    )

    cover = prepare_default_cover()

    # 凭证密封信封（宪法 II）：appid/secret 加密后交给执行器校验
    from cryptography.fernet import Fernet

    from zimeiti_api.credentials import encrypt_secret

    master = os.environ.get("ZIMEITI_MASTER_KEY")
    if not master:
        key_file = Path("data/credentials/.master_key")
        key_file.parent.mkdir(parents=True, exist_ok=True)
        if not key_file.exists():
            key_file.write_text(Fernet.generate_key().decode(), encoding="utf-8")
        master = key_file.read_text(encoding="utf-8").strip()
        os.environ["ZIMEITI_MASTER_KEY"] = master
    sealed = encrypt_secret(
        json.dumps({"app_id": os.environ["WECHAT_MP_APPID"],
                    "app_secret": os.environ["WECHAT_MP_APPSECRET"]})
    )
    client = GzhClient(
        os.environ["WECHAT_MP_APPID"], os.environ["WECHAT_MP_APPSECRET"],
        token_cache="data/credentials/.gzh_token_cache.json",
    )
    executor = PublishExecutor(daily_limit=2, allowed_accounts={"gzh-main"})

    audit.record("walkthrough_a3_gzh_started", slug=SLUG)
    result = executor.publish(
        "gzh-main",
        drafts.gzh,
        platform_call=real_platform_router,
        credentials_sealed=sealed,
    )
    audit.record("walkthrough_a3_gzh_result", slug=SLUG, **result)
    print(f"[A3] 发布结果：{json.dumps(result, ensure_ascii=False)}")

    if result["readback"] == "verified":
        print("[A3] 验证通过（verified）——请到公众号后台草稿箱人工确认内容排版")
        return 0
    print("[A3] 读回未核实，检查审计与平台状态")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
