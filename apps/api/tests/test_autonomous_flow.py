"""autonomous-flow：运营流程编排（zimeiti_autonomous 包）。

覆盖规格四条：
- 流程定义与持久化（五层步骤裁剪 + 幂等建表）
- 逐步执行与记录（上一步摘要注入、产出归档、失败即停）
- agent 入口注入纪律（未注入显式报错）
- 既有 case/prompt 不回归（scheduler 分发分支）
"""

from __future__ import annotations

import pytest

from zimeiti_autonomous import flows as fl
from zimeiti_autonomous import runner as rn
from zimeiti_autonomous import store as st


@pytest.fixture(autouse=True)
def _reset_entry():
    """每个用例独立：清注入的 agent 入口。"""
    rn.set_agent_entry(None)
    yield
    rn.set_agent_entry(None)


def _fake_entry(session_key: str, message: str) -> str:
    """假 agent 入口：把收到的 prompt 原样回显（便于断言摘要传递）。"""
    return f"OK::{message[:40]}"


# ── 1. 流程定义与裁剪 ──────────────────────────────────────────────────────
def test_step_enum_and_validation():
    assert set(fl.STEPS) == {"discover", "plan", "produce", "publish", "review"}
    assert fl.validate_steps(["discover", "plan"]) == ["discover", "plan"]
    # 非法步骤 / 空步骤集 → ValueError（配置面要早失败）
    with pytest.raises(ValueError):
        fl.validate_steps(["discover", "nope"])
    with pytest.raises(ValueError):
        fl.validate_steps([])


def test_validate_steps_preserves_given_order():
    """步骤按用户给定顺序执行（有序子集，非固定五层顺序）。"""
    assert fl.validate_steps(["review", "discover"]) == ["review", "discover"]


def test_store_upsert_and_get(tmp_path, monkeypatch):
    """流程持久化：写入后可取回（用 sqlite 以外的内存实现不现实 → 走 PG 若可用，否则跳过）。"""
    pytest.importorskip("psycopg")
    try:
        st.setup()
    except Exception as e:  # noqa: BLE001   无 PG 环境时跳过（CI 依赖 PG）
        pytest.skip(f"PG 不可用：{e}")
    fid = st.create_flow("单元测试流程", ["discover", "plan"], "08:00", "{}")
    got = st.get_flow(fid)
    assert got and got["name"] == "单元测试流程" and got["steps"] == ["discover", "plan"]
    st.delete_flow(fid)


# ── 2. 逐步执行 ────────────────────────────────────────────────────────────
def test_run_flow_serial_with_summary_chain(tmp_path):
    """串行执行：每步收到上一步摘要（摘要注入可观测）。"""
    rn.set_agent_entry(_fake_entry)
    seen: list[str] = []

    def entry(sk: str, msg: str) -> str:
        seen.append(msg)
        return f"产出-{len(seen)}"

    rn.set_agent_entry(entry)
    res = rn.run_flow(
        flow_id="f-test",
        name="测试流程",
        steps=["discover", "plan"],
        config={"topic": "AI 热点"},
        archive_root=tmp_path,
    )
    assert res["status"] == "done"
    assert [s["step"] for s in res["steps"]] == ["discover", "plan"]
    assert all(s["status"] == "done" for s in res["steps"])
    # 第二步 prompt 必须带上一步产出（摘要链）
    assert "产出-1" in seen[1]
    # 产出归档落盘
    assert (tmp_path / "f-test" / "01-discover.md").is_file()
    assert (tmp_path / "f-test" / "02-plan.md").is_file()


def test_run_flow_stops_on_failure(tmp_path):
    """单步失败即停：后续步骤不执行，记录失败原因与位置。"""
    calls: list[str] = []

    def entry(sk: str, msg: str) -> str:
        calls.append(sk)
        if len(calls) == 1:
            raise RuntimeError("这一步炸了")
        return "ok"

    rn.set_agent_entry(entry)
    res = rn.run_flow(
        flow_id="f-fail",
        name="失败流程",
        steps=["discover", "plan", "review"],
        config={},
        archive_root=tmp_path,
    )
    assert res["status"] == "failed"
    assert res["failed_step"] == "discover"
    assert "这一步炸了" in (res["steps"][0]["error"] or "")
    # 后续两步未执行（无记录或标记 skipped）
    assert len([s for s in res["steps"] if s["status"] == "done"]) == 0


# ── 3. 注入纪律 ────────────────────────────────────────────────────────────
def test_run_flow_requires_injected_entry(tmp_path):
    rn.set_agent_entry(None)
    with pytest.raises(RuntimeError) as ei:
        rn.run_flow(
            flow_id="f-noentry", name="x", steps=["discover"], config={}, archive_root=tmp_path
        )
    assert "agent 入口未注入" in str(ei.value)


def test_autonomous_package_does_not_import_harness():
    """分层纪律：自主包不得 import harness 的 agent 入口（组装层注入）。"""
    import re
    from pathlib import Path as _P

    root = _P(__file__).resolve().parent.parent / "zimeiti_autonomous"
    bad = []
    for py in root.rglob("*.py"):
        t = py.read_text(encoding="utf-8")
        if re.search(r"from zimeiti_harness|import zimeiti_harness", t):
            bad.append(py.name)
    assert not bad, f"autonomous 包不得 import harness：{bad}"


# ── 4. 既有任务类型不回归 ──────────────────────────────────────────────────
def test_scheduler_dispatches_flow_kind(monkeypatch):
    """kind=flow 走 runner；case/prompt 分支不受影响（仅断言分发函数存在且可分辨）。"""
    from zimeiti_api.automations import scheduler as sch

    assert callable(getattr(sch, "_run_flow", None)), "scheduler 需提供 flow 分发"
    assert callable(getattr(sch, "_run_case", None))
    assert callable(getattr(sch, "_run_prompt", None))
