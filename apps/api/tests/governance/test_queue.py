def test_cancelled_is_terminal(tmp_path, monkeypatch):
    """feat-publish-orchestration：cancelled 为终态——pending 可取消，终态不可覆盖。"""
    from zimeiti_api.governance import queue

    monkeypatch.setattr(queue, "_queue_path", lambda: tmp_path / "q.json")
    eid = queue.schedule("xhs-main", "outputs/xhs-main/s1", "2026-10-13T09:00:00", title="t")
    assert queue.mark(eid, "cancelled", "用户取消") is True
    entries = queue.list_entries()
    assert entries[0]["status"] == "cancelled"
    # 终态幂等：再 mark 忽略
    assert queue.mark(eid, "failed") is False
    assert entries[0]["status"] == "cancelled"
