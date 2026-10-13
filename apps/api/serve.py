"""API 启动入口：先设 Windows Selector 事件循环策略，再起 uvicorn。

为什么需要这个文件（pg-data-layer 变更）：
psycopg 异步（checkpointer 连接池 AsyncPostgresSaver）不能用 Windows 默认的
ProactorEventLoop。`python -m uvicorn app:app` 的启动顺序是 asyncio.run 先建
loop、再 import app——app.py 里 set_event_loop_policy 已晚（策略只影响之后
创建的 loop）。故必须在建 loop 之前设策略，即用本文件编程式启动：

    python serve.py [--host 127.0.0.1] [--port 8000]

Makefile 的 `make api` 已改为走本入口。
"""
from __future__ import annotations

import argparse
import asyncio
import os

# 必须在任何事件循环创建前设置（uvicorn.run 内部才建 loop）
if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def main() -> None:
    ap = argparse.ArgumentParser(description="zimeiti-ai API（PG 数据层）启动入口")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()

    import uvicorn

    # loop="none"：让 uvicorn 不指定 loop factory，回退到「当前 policy 建 loop」——
    # uvicorn 的 auto/asyncio factory 在 win32 上硬编码 ProactorEventLoop
    # （uvicorn/loops/asyncio.py），无视 set_event_loop_policy；只有 none 才
    # 走 policy，我们的 Selector 策略才生效（psycopg 异步的硬要求）。
    uvicorn.run("app:app", host=args.host, port=args.port, loop="none")


if __name__ == "__main__":
    main()
