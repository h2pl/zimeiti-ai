"""归因数据源（agent-ops-workflow G0）：发布成功后落 outputs/_analytics/ 记录。

TDD RED：analytics 模块尚不存在，本测试先行失败；实现后 GREEN。
"""

from pathlib import Path

import pytest

from zimeiti_api.core.paths import OUTPUTS_DIR

MOD = "zimeiti_api.content.ops_analytics"


def _fresh_analytics_dir(monkeypatch, tmp_path: Path) -> Path:
    """把 analytics 记录目录重定向到临时目录（不碰真实内容库）。"""
    ana = tmp_path / "_analytics"
    ana.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(f"{MOD}._ANALYTICS_DIR", ana, raising=False)
    return ana


def test_record_and_read_publish(monkeypatch, tmp_path):
    ana = _fresh_analytics_dir(monkeypatch, tmp_path)
    from zimeiti_api.content import ops_analytics as oa

    oa.record_publish("wechat-oa", "outputs/wechat-drafts/demo.md", "media-123")
    records = oa.read_records("wechat-oa")
    assert len(records) == 1
    r = records[0]
    assert r["media_id"] == "media-123"
    assert r["content_path"].endswith("demo.md")
    assert r["status"] == "pending-feedback"
    # 落盘真实存在且为合法 JSON
    assert list(ana.rglob("*.json"))


def test_record_idempotent_by_media_id(monkeypatch, tmp_path):
    _fresh_analytics_dir(monkeypatch, tmp_path)
    from zimeiti_api.content import ops_analytics as oa

    oa.record_publish("wechat-oa", "a.md", "media-1")
    oa.record_publish("wechat-oa", "a.md", "media-1")  # 同 media_id 不重复
    oa.record_publish("wechat-oa", "b.md", "media-2")
    assert len(oa.read_records("wechat-oa")) == 2


def test_read_missing_returns_empty(monkeypatch, tmp_path):
    _fresh_analytics_dir(monkeypatch, tmp_path)
    from zimeiti_api.content import ops_analytics as oa

    assert oa.read_records("bilibili") == []


def test_rejects_path_escape(monkeypatch, tmp_path):
    _fresh_analytics_dir(monkeypatch, tmp_path)
    from zimeiti_api.content import ops_analytics as oa

    with pytest.raises(ValueError):
        oa.record_publish("wechat-oa", "../../etc/passwd", "m-1")


def test_outputs_dir_used_by_default():
    """默认目录锚在内容库 outputs/_analytics（真实文件系统，非虚拟）。"""
    from zimeiti_api.content import ops_analytics as oa

    assert oa._ANALYTICS_DIR == OUTPUTS_DIR / "_analytics"
