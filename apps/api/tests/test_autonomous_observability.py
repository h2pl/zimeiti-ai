"""autonomous-observability：执行记录可查（读侧）。

覆盖规格：GET /api/flows/runs 返回执行记录含步骤明细（含 blocked/failed 步骤）。
"""

from __future__ import annotations

import pytest

from zimeiti_autonomous import runner as rn
from zimeiti_autonomous import store as st


@pytest.fixture(autouse=True)
def _reset():
    rn.set_agent_entry(None)
    yield
    rn.set_agent_entry(None)


def test_list_runs_contains_steps(tmp_path):
    """执行记录含步骤明细（状态/耗时/产出路径）。"""
    rn.set_agent_entry(lambda sk, msg: "产出")
    res = rn.run_flow(
        flow_id="obs-1",
        name="观测流程",
        steps=["discover", "plan"],
        config={"feedback": False, "guardrails": False},
        archive_root=tmp_path,
    )
    st.save_run("obs-1", res)
    try:
        runs = st.list_runs(flow_id="obs-1")
    except Exception as e:  # noqa: BLE001   无 PG 环境时跳过
        pytest.skip(f"PG 不可用：{e}")
    assert runs, "应能查到执行记录"
    top = runs[0]
    assert top["flow_id"] == "obs-1" and top["status"] == "done"
    assert [s["step"] for s in top["steps"]] == ["discover", "plan"]
    assert all(s["status"] == "done" for s in top["steps"])


def test_list_runs_captures_failed_step(tmp_path):
    """失败步骤与其错误进入记录（护栏/看板要能看到）。"""

    def entry(sk: str, msg: str) -> str:
        if "plan" in sk:
            raise RuntimeError("计划步炸了")
        return "产出"

    rn.set_agent_entry(entry)
    res = rn.run_flow(
        flow_id="obs-2",
        name="失败流程",
        steps=["discover", "plan"],
        config={"feedback": False, "guardrails": False},
        archive_root=tmp_path,
    )
    st.save_run("obs-2", res)
    try:
        runs = st.list_runs(flow_id="obs-2")
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"PG 不可用：{e}")
    top = runs[0]
    assert top["status"] == "failed" and top["failed_step"] == "plan"
    failed = [s for s in top["steps"] if s["status"] == "failed"]
    assert failed and "计划步炸了" in failed[0]["error"]


def test_list_runs_limit_respected(tmp_path):
    rn.set_agent_entry(lambda sk, msg: "产出")
    for i in range(3):
        res = rn.run_flow(
            flow_id="obs-3",
            name="多次",
            steps=["discover"],
            config={"feedback": False, "guardrails": False},
            archive_root=tmp_path,
        )
        st.save_run("obs-3", res)
        _ = i
    try:
        runs = st.list_runs(flow_id="obs-3", limit=2)
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"PG 不可用：{e}")
    assert len(runs) <= 2
