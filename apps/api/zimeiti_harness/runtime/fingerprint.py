"""进程启动指纹：检测「代码在进程启动后被变更」（stale-process-guard）。

背景（harness-business-split 报障）：长跑进程启动于重构前，harness 内
`from ..memory.tools import ...` 这类函数级懒加载按包 `__path__`（磁盘目录）
解析——模块已被 git mv 走 → `No module named 'zimeiti_api.memory.tools'`
这种无法行动的 ImportError。守卫在同一层（harness 入口）最早拦下，
把「现象天书」换成「请重启后端」的行动指引。

设计要点（design D1/D2）：
- 内容 sha1 而非 mtime——git checkout/merge 重写文件但内容不变，不误报
- 60s TTL 缓存——每请求全量哈希 ~100 个小文件 <50ms，缓存后近零
- 相对 POSIX 路径 + sorted——跨平台确定
"""

from __future__ import annotations

import hashlib
import subprocess
import time
from pathlib import Path

API_DIR = Path(__file__).resolve().parent.parent.parent
_TARGETS = ("zimeiti_api", "zimeiti_harness")
_TTL = 60.0

_SNAPSHOT: dict | None = None
_CACHE: dict | None = None
_CACHE_AT = 0.0


class StaleProcessError(RuntimeError):
    """进程启动后源码已变更——需重启后端。"""


def _hash_tree() -> dict[str, str]:
    files: dict[str, str] = {}
    for pkg in _TARGETS:
        for py in sorted((API_DIR / pkg).rglob("*.py")):
            if "__pycache__" in py.parts:
                continue
            rel = py.relative_to(API_DIR).as_posix()
            # usedforsecurity=False：内容寻址指纹，非安全用途（bandit B324）
            files[rel] = hashlib.sha1(py.read_bytes(), usedforsecurity=False).hexdigest()
    return files


def _git_head() -> str:
    import shutil

    git = shutil.which("git") or "git"  # 全路径，避免 B607
    try:
        return subprocess.run(
            [git, "rev-parse", "--short", "HEAD"],
            cwd=API_DIR.parent.parent,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
    except Exception:  # noqa: BLE001   非 git 环境（如打包部署）降级为空
        return ""


def current() -> dict:
    """当前磁盘指纹（60s TTL 缓存）。"""
    global _CACHE, _CACHE_AT
    now = time.monotonic()
    if _CACHE is not None and now - _CACHE_AT < _TTL:
        return _CACHE
    snap = {"head": _git_head(), "files": _hash_tree()}
    _CACHE, _CACHE_AT = snap, now
    return snap


def capture() -> dict:
    """进程启动时调用：固化启动快照（app.py lifespan）。"""
    global _SNAPSHOT
    _SNAPSHOT = current()
    return _SNAPSHOT


def ensure_fresh() -> None:
    """chat 入口调用：源码未变更放行；变更则抛可行动错误（绝不尝试执行旧路径）。"""
    if _SNAPSHOT is None:  # 未 capture（如测试直连）——惰性固化当前态
        capture()
        return
    now = current()
    if now["files"] != _SNAPSHOT["files"]:
        # 内容变更的路径（增删 + 哈希不同都算；前缀 ❌ 由 chat_router 统一加）
        changed = sorted(
            p
            for p in set(now["files"]) | set(_SNAPSHOT["files"])
            if now["files"].get(p) != _SNAPSHOT["files"].get(p)
        )[:5]
        raise StaleProcessError(
            "后端代码已变更（本进程启动于旧版代码）——请重启后端"
            "（Ctrl+C 后重新 make api / make dev）再试。"
            f"变动文件（至多 5 个）：{changed}"
        )
