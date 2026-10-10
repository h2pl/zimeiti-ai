"""运维触发标记消费验收（web-pages-batch T4）。"""

import json

import pytest

from zimeiti_api.runtime import gateway


@pytest.mark.asyncio
async def test_consume_manual_triggers(tmp_path, monkeypatch):
    monkeypatch.setattr(gateway, "_trigger_path", lambda: tmp_path / "ops-trigger.json")
    executed = []

    async def fake_run_job(name):
        executed.append(name)
        return {"job": name}

    monkeypatch.setattr(gateway, "_run_job", fake_run_job)
    (tmp_path / "ops-trigger.json").write_text(
        json.dumps({"hosted_content": True}), encoding="utf-8"
    )
    ran = await gateway._consume_manual_triggers()
    assert ran == ["hosted_content"]
    assert not (tmp_path / "ops-trigger.json").exists()  # 消费后清除

    # 空标记：不执行
    assert await gateway._consume_manual_triggers() == []
    assert executed == ["hosted_content"]


@pytest.mark.asyncio
async def test_consume_corrupt_marker_discards(tmp_path, monkeypatch):
    monkeypatch.setattr(gateway, "_trigger_path", lambda: tmp_path / "ops-trigger.json")
    (tmp_path / "ops-trigger.json").write_text("{broken", encoding="utf-8")
    executed = []
    monkeypatch.setattr(gateway, "_run_job", lambda name: executed.append(name) or {})

    # 用 async 包装
    async def fake_run(name):
        executed.append(name)
        return {"job": name}

    monkeypatch.setattr(gateway, "_run_job", fake_run)
    assert await gateway._consume_manual_triggers() == []
    assert executed == []
