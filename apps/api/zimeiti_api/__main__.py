"""生产启动入口：python -m zimeiti_api [--host H] [--port P]。

psycopg 异步（checkpointer 连接池）不能用 Windows 默认 ProactorEventLoop，
必须在任何事件循环创建前设 Selector 策略——本模块先设策略再 import app。
（uvicorn 的 auto/asyncio factory 在 win32 硬编码 Proactor，只有 loop="none"
才走当前 policy，故 loop="none"。）
"""

from __future__ import annotations

import argparse
import asyncio
import os

if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def main() -> None:
    ap = argparse.ArgumentParser(description="zimeiti-ai API（PG 数据层）启动入口")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()

    # 守卫白名单按端口计算（governance.guard 导入期读取 EASEL_PORT）——
    # 必须在 import app 前设置。
    os.environ["EASEL_PORT"] = str(args.port)

    import uvicorn

    uvicorn.run("zimeiti_api.app:app", host=args.host, port=args.port, loop="none")


if __name__ == "__main__":
    main()
