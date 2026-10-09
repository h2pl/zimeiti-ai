"""pytest 全局配置。

Windows 下 psycopg async 必须用 SelectorEventLoop——
在 import 阶段全局设置（比 event_loop_policy fixture 更可靠，pytest-asyncio 1.x 已弃用后者）。
"""

import asyncio
import sys

if sys.platform == "win32":
    from asyncio import WindowsSelectorEventLoopPolicy

    asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())
