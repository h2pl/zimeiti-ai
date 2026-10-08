"""托管循环（Task 2.3）：定时/事件触发、审批阻断、断点恢复、审计。

断点恢复原理：图状态全部持久化在 Postgres checkpointer；
"进程重启" = 用同一 thread_id 新建 agent 实例继续，已完成节点不会重跑。
"""

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from zimeiti_api import audit


async def run_hosted_cycle(agent, thread_id: str, instruction: str) -> dict:
    """触发一轮托管循环：从新 thread 运行到审批中断点。"""
    audit.record("cycle_started", thread_id=thread_id, instruction=instruction)
    result = await agent.ainvoke(
        {"messages": [HumanMessage(instruction)]},
        config={"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}},
    )
    if "__interrupt__" in result:
        audit.record("awaiting_approval", thread_id=thread_id)
    else:
        audit.record("cycle_completed", thread_id=thread_id)
    return result


async def resume_after_approval(agent, thread_id: str, approved: bool) -> dict:
    """人工审批后恢复循环（可跨进程，状态在 checkpointer）。"""
    audit.record("approval_received" if approved else "approval_rejected", thread_id=thread_id)
    decision = "approve" if approved else "reject"
    result = await agent.ainvoke(
        Command(resume={"decisions": [{"type": decision}]}),
        config={"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}},
    )
    audit.record("cycle_completed", thread_id=thread_id)
    return result


def audit_list() -> list[dict]:
    return audit.list_entries()
