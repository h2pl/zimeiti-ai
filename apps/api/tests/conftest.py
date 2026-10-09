"""pytest 全局配置。

Windows 下 psycopg async 必须用 SelectorEventLoop——
在 import 阶段全局设置（比 event_loop_policy fixture 更可靠，pytest-asyncio 1.x 已弃用后者）。
"""

import asyncio
import os
import sys
import tempfile

if sys.platform == "win32":
    from asyncio import WindowsSelectorEventLoopPolicy

    asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())

# 测试的可变产物（审计/待审批注册表）写入临时目录，避免污染仓库文件
_TEST_STATE = tempfile.mkdtemp(prefix="zimeiti-test-")
os.environ["AUDIT_PATH"] = os.path.join(_TEST_STATE, "audit.jsonl")
os.environ.setdefault("ZIMEITI_MASTER_KEY", "test-master-key-not-production")

import zimeiti_api.hosted as _hosted  # noqa: E402

from pathlib import Path as _P
_hosted.PENDING_PATH = _P(_TEST_STATE) / "pending_approvals.json"
