"""publish_queue 排期队列验收：幂等回填、冷却保留 pending、停用即 failed、健康巡检。"""

import json
from datetime import datetime, timedelta

import pytest

from zimeiti_api.core import notify
from zimeiti_api.governance import platform_state, risk
from zimeiti_api.governance import queue as publish_queue
from zimeiti_api.runtime import health


@pytest.fixture
def qfile(tmp_path, monkeypatch):
    f = tmp_path / "queue.json"
    monkeypatch.setattr(publish_queue, "_queue_path", lambda: f)
    monkeypatch.setattr(platform_state, "_state_path", lambda: tmp_path / "ps.json")
    monkeypatch.setattr(platform_state, "DEFAULT_ACCOUNTS", ("xhs-main", "gzh-main"))
    platform_state.ensure_defaults()
    return f


def _entry(account="xhs-main", minutes_ago=5):
    return {
        "id": "e1",
        "account": account,
        "drafts_path": "outputs/x/d",
        "title": "t",
        "run_at": (datetime.now() - timedelta(minutes=minutes_ago)).isoformat(timespec="seconds"),
        "status": "pending",
    }


class TestQueueSemantics:
    def test_schedule_and_due(self, qfile):
        entry_id = publish_queue.schedule(
            "xhs-main", "outputs/x/d", datetime.now().isoformat(timespec="seconds")
        )
        due = publish_queue.due()
        assert len(due) == 1 and due[0]["id"] == entry_id
        # 未来时间未到期
        publish_queue.schedule(
            "xhs-main",
            "outputs/x/d",
            (datetime.now() + timedelta(hours=2)).isoformat(timespec="seconds"),
        )
        assert len(publish_queue.due()) == 1

    def test_mark_idempotent(self, qfile):
        entry_id = publish_queue.schedule(
            "xhs-main", "p", datetime.now().isoformat(timespec="seconds")
        )
        assert publish_queue.mark(entry_id, "done", "ok") is True
        assert publish_queue.mark(entry_id, "failed", "试图覆盖") is False  # 终态不可覆盖
        entries = json.loads(qfile.read_text(encoding="utf-8"))
        assert entries[0]["status"] == "done"
        with pytest.raises(ValueError):
            publish_queue.mark(entry_id, "pending")  # 非终态非法


class TestRunDue:
    def test_disabled_platform_fails_immediately(self, qfile, monkeypatch):
        platform_state.set_enabled("xhs-main", False, "登录失效")
        e = _entry()
        qfile.write_text(json.dumps([e]), encoding="utf-8")
        called = []
        monkeypatch.setattr(
            publish_queue, "execute_approved_publish", lambda a, p: called.append(1) or {}
        )
        results = publish_queue.run_due()
        assert results[0]["status"] == "failed"
        assert called == []  # 停用平台绝不执行

    def test_cooldown_keeps_pending(self, qfile, monkeypatch):
        e = _entry()
        qfile.write_text(json.dumps([e]), encoding="utf-8")
        monkeypatch.setattr(risk, "in_cooldown", lambda a, now=None: True)
        results = publish_queue.run_due()
        assert results[0] == {"id": "e1", "status": "pending", "reason": "cooldown"}
        entries = json.loads(qfile.read_text(encoding="utf-8"))
        assert entries[0]["status"] == "pending"  # 冷却保留，下轮再试

    def test_success_marks_done(self, qfile, monkeypatch):
        e = _entry()
        qfile.write_text(json.dumps([e]), encoding="utf-8")
        monkeypatch.setattr(
            publish_queue,
            "execute_approved_publish",
            lambda a, p: {"platform_result": "ok", "readback": "verified"},
        )
        results = publish_queue.run_due()
        assert results[0]["status"] == "done"
        entries = json.loads(qfile.read_text(encoding="utf-8"))
        assert entries[0]["status"] == "done"
        assert entries[0]["detail"]  # 回填结果证据

    def test_soft_block_failure_keeps_pending(self, qfile, monkeypatch):
        e = _entry()
        qfile.write_text(json.dumps([e]), encoding="utf-8")
        monkeypatch.setattr(platform_state, "_state_path", lambda: qfile.parent / "ps.json")
        platform_state.ensure_defaults()

        def boom(a, p):
            raise RuntimeError("error_code=300017 请求太频繁")

        monkeypatch.setattr(publish_queue, "execute_approved_publish", boom)
        monkeypatch.setattr(risk, "_cooldown_path", lambda: qfile.parent / "cd.json")
        monkeypatch.setattr(notify, "send", lambda event, text: True)
        results = publish_queue.run_due()
        assert results[0] == {"id": "e1", "status": "pending", "reason": "cooldown"}


# ── 健康巡检 + 晨报（P0⑦） ─────────────────────────────────────────


class TestHealth:
    def test_check_xhs_missing_state(self, monkeypatch, tmp_path):
        import zimeiti_api.runtime.health as h

        monkeypatch.setattr("zimeiti_api.config.LOGIN_STATE_PATH", str(tmp_path / "nope.json"))
        assert h.check_xhs()["ok"] is False

    def test_check_xhs_with_web_session(self, monkeypatch, tmp_path):
        import zimeiti_api.runtime.health as h

        f = tmp_path / "state.json"
        f.write_text(
            json.dumps({"cookies": [{"name": "web_session", "value": "x"}]}), encoding="utf-8"
        )
        monkeypatch.setattr("zimeiti_api.config.LOGIN_STATE_PATH", str(f))
        assert h.check_xhs()["ok"] is True

    def test_run_health_check_disables_and_notifies(self, monkeypatch, tmp_path):
        monkeypatch.setattr(platform_state, "_state_path", lambda: tmp_path / "ps.json")
        monkeypatch.setattr("zimeiti_api.config.LOGIN_STATE_PATH", str(tmp_path / "nope.json"))
        sent = []
        monkeypatch.setattr(notify, "send", lambda event, text: sent.append(event) or True)
        platform_state.ensure_defaults()
        report = health.run_health_check()
        assert report["accounts"]["xhs-main"]["ok"] is False
        assert platform_state.is_enabled("xhs-main") is False
        assert "login_wall" in sent

    def test_morning_digest_format(self):
        text = health.build_morning_digest(
            {"accounts": {"xhs-main": {"ok": False}, "gzh-main": {"ok": True}}},
            {"ops_data": {"runs": [{"interrupted": True}, {"skipped": "x"}, {"error": "e"}]}},
        )
        assert "失效 xhs-main" in text
        assert "ops_data: 成功1 跳过1 失败1" in text
