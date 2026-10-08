"""pytest 全局配置：Windows 下 psycopg async 需要 SelectorEventLoop。"""

import asyncio
import sys

import pytest

if sys.platform == "win32":
    from asyncio import SelectorEventLoop

    @pytest.fixture
    def event_loop_policy():
        return asyncio.WindowsSelectorEventLoopPolicy()
