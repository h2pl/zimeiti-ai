"""ops_daily 定时调度验收：pull→auto 校准串接、状态游标持久化、失败不中断。"""

import json

import pytest

from zimeiti_api.operations import daily as ops_daily
from zimeiti_api.operations.daily import run_daily


class _FakeDB:
    """run_daily 的 db 仅被 fake 的 pull/auto 使用，无需真实 PG。"""


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    """隔离外部副作用：pull 与 auto_calibrate 打桩（嵌套结构对齐 pull_platform 真实返回）。"""
    monkeypatch.setattr(
        "zimeiti_api.operations.metrics.pull_platform",
        lambda db, site, b=None, e=None: {site: {"ok": True, "metrics": {"x": 1.0}}},
    )
    monkeypatch.setattr(
        "zimeiti_api.operations.calibration.auto_calibrate",
        lambda db, platform, last_calibrated_at=None, force=False: {"skipped": False},
    )


def test_daily_pulls_and_calibrates_both_accounts(tmp_path, monkeypatch):
    state_file = tmp_path / "state.json"
    seen_platforms = []

    def fake_auto(db, platform, last_calibrated_at=None, force=False):
        seen_platforms.append(platform)
        return {"skipped": False, "reports": ["x.md"]}

    monkeypatch.setattr("zimeiti_api.operations.calibration.auto_calibrate", fake_auto)
    run = run_daily(_FakeDB(), state_path=state_file)

    assert seen_platforms == ["gzh-main", "xhs-main"]
    assert run["pull"]["gzh-main"] == {"gzh": {"ok": True, "metrics": {"x": 1.0}}}
    assert run["pull"]["xhs-main"]["xhs"]["ok"] is True
    # 成功校准后游标落盘（下次运行据此计数新快照）
    state = json.loads(state_file.read_text(encoding="utf-8"))
    assert state["gzh-main"]["last_calibrated_at"]
    assert state["xhs-main"]["last_calibrated_at"]


def test_daily_first_run_uses_epoch_cursor(tmp_path, monkeypatch):
    """首轮无游标必须传 epoch（全部快照视为新），否则 new_count 恒 0 永远跳过（死锁）。"""
    seen_cursors = []

    def fake_auto(db, platform, last_calibrated_at=None, force=False):
        seen_cursors.append(last_calibrated_at)
        return {"skipped": True}

    monkeypatch.setattr("zimeiti_api.operations.calibration.auto_calibrate", fake_auto)
    state_file = tmp_path / "state.json"  # 不存在 → 首轮
    run_daily(_FakeDB(), state_path=state_file)
    assert seen_cursors == ["1970-01-01T00:00:00", "1970-01-01T00:00:00"]

    # 已有游标则原样传递
    state_file.write_text(
        json.dumps({"gzh-main": {"last_calibrated_at": "2026-10-01T00:00:00"}}),
        encoding="utf-8",
    )
    run_daily(_FakeDB(), state_path=state_file)
    assert seen_cursors[2] == "2026-10-01T00:00:00"


def test_daily_below_threshold_keeps_cursor(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "zimeiti_api.operations.calibration.auto_calibrate",
        lambda db, platform, last_calibrated_at=None, force=False: {
            "skipped": True,
            "new_snapshots": 2,
        },
    )
    state_file = tmp_path / "state.json"
    run = run_daily(_FakeDB(), state_path=state_file)
    assert run["calibration"]["gzh-main"]["skipped"] is True
    state = json.loads(state_file.read_text(encoding="utf-8"))
    assert "gzh-main" not in state  # 跳过不写游标


def test_daily_pull_failure_continues_other_platform(tmp_path, monkeypatch):
    calls = []

    def fake_pull(db, site, b=None, e=None):
        calls.append(site)
        if site == "gzh":
            raise RuntimeError("凭证失效")
        return {"xhs": {"ok": True, "metrics": {"fans": 1}}}

    monkeypatch.setattr("zimeiti_api.operations.metrics.pull_platform", fake_pull)
    state_file = tmp_path / "state.json"
    run = run_daily(_FakeDB(), state_path=state_file)
    assert calls == ["gzh", "xhs"]  # gzh 失败后 xhs 照常
    assert "凭证失效" in run["pull"]["gzh-main"]["gzh"]["error"]
    assert run["pull"]["xhs-main"]["xhs"]["ok"] is True
    assert run["calibration"]["gzh-main"] == {"skipped": False}  # 校准不受 pull 失败影响


def test_daily_calibration_failure_keeps_cursor(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "zimeiti_api.operations.calibration.auto_calibrate",
        lambda db, platform, last_calibrated_at=None, force=False: (_ for _ in ()).throw(
            RuntimeError("无可校准数据")
        ),
    )
    state_file = tmp_path / "state.json"
    run = run_daily(_FakeDB(), state_path=state_file)
    assert "无可校准数据" in run["calibration"]["xhs-main"]["error"]
    assert json.loads(state_file.read_text(encoding="utf-8")) == {}


def test_run_log_appended_to_data_metrics(tmp_path, monkeypatch):
    """运行日志落 data/metrics/ops_daily.jsonl，每次一条可观测。"""
    log_file = tmp_path / "ops_daily.jsonl"
    monkeypatch.setattr(ops_daily, "_log_path", lambda: log_file)
    run_daily(_FakeDB(), state_path=tmp_path / "state.json")
    run_daily(_FakeDB(), state_path=tmp_path / "state.json")
    lines = log_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    rec = json.loads(lines[-1])
    assert set(rec) >= {"ts", "pull", "calibration"}


def test_state_roundtrip_survives_corrupt_file(tmp_path):
    state_file = tmp_path / "state.json"
    state_file.write_text("{broken", encoding="utf-8")
    assert ops_daily.load_state(state_file) == {}  # 损坏不炸，从头计数
