"""stale-process-guard：代码变更未重启守卫（fingerprint）。

覆盖规格三条：
- 指纹一致 → ensure_fresh 放行（no-op）
- 指纹不一致 → StaleProcessError，文案含重启指引、无 ImportError 文本
- 同内容重复计算哈希稳定（mtime 抖动不误报）
"""

from __future__ import annotations

import time

import pytest

from zimeiti_harness.runtime import fingerprint as fp


@pytest.fixture(autouse=True)
def _reset_cache():
    fp._CACHE = None
    fp._CACHE_AT = 0.0
    yield
    fp._CACHE = None
    fp._CACHE_AT = 0.0


def test_snapshot_stable_for_same_content():
    """同内容两次计算一致（排除 mtime 噪声）。"""
    a = fp.current()
    time.sleep(0.05)
    b = fp.current()
    assert a == b
    assert a["head"] == fp.capture()["head"]


def test_ensure_fresh_passes_when_unchanged():
    fp.capture()
    fp.ensure_fresh()  # 不抛即放行


def test_ensure_fresh_blocks_after_change(monkeypatch):
    fp.capture()
    # 模拟「进程启动后源码被改动」：篡改进程内快照的一个文件哈希
    snap = fp._SNAPSHOT
    assert snap is not None
    tampered = dict(snap)
    files = dict(tampered["files"])
    first = next(iter(files))
    files[first] = "0" * 40
    tampered["files"] = files
    monkeypatch.setattr(fp, "_SNAPSHOT", tampered)
    with pytest.raises(fp.StaleProcessError) as ei:
        fp.ensure_fresh()
    msg = str(ei.value)
    assert "重启" in msg and "后端" in msg
    assert "ImportError" not in msg and "No module" not in msg


def test_hash_tree_covers_both_packages_and_excludes_pycache():
    snap = fp.current()
    paths = snap["files"]
    assert any(p.startswith("zimeiti_api/") for p in paths)
    assert any(p.startswith("zimeiti_harness/") for p in paths)
    assert not any("__pycache__" in p for p in paths)
    assert all(p.endswith(".py") for p in paths)
