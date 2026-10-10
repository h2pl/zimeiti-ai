"""托管循环（Task 2.3）：定时/事件触发、审批阻断、断点恢复、审计。

断点恢复原理：图状态全部持久化在 Postgres checkpointer；
"进程重启" = 用同一 thread_id 新建 agent 实例继续，已完成节点不会重跑。
"""

import json
import uuid
from pathlib import Path

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from zimeiti_api import audit
from zimeiti_api.config import PENDING_PATH as _CONFIG_PENDING

PENDING_PATH = Path(_CONFIG_PENDING)


def list_pending_approvals() -> list[dict]:
    """待审批列表（Web 审批页数据源）。"""
    if not PENDING_PATH.exists():
        return []
    return json.loads(PENDING_PATH.read_text(encoding="utf-8"))


def _add_pending(
    thread_id: str,
    instruction: str,
    account: str = "",
    kind: str = "approval",
    question: dict | None = None,
) -> None:
    PENDING_PATH.parent.mkdir(parents=True, exist_ok=True)
    pending = list_pending_approvals()
    # account 随中断落盘：恢复端点据此加载正确画像（修复硬编码 xhs-main 遗留项）
    entry: dict = {"thread_id": thread_id, "instruction": instruction, "account": account}
    if kind != "approval":
        entry["kind"] = kind
        entry.update(question or {})
    pending.append(entry)
    PENDING_PATH.write_text(json.dumps(pending, ensure_ascii=False), encoding="utf-8")
    # 审批待办通知（P0④；未配置 webhook 时静默）
    from zimeiti_api import notify

    if kind == "question":
        q_text = (question or {}).get("question", "")
        notify.send(
            "question_required",
            f"agent 有问题需要人回答：{thread_id}（{account or '未知账号'}）——{q_text}",
        )
    else:
        notify.send(
            "approval_required",
            f"有待审批项需要处理：{thread_id}（{account or '未知账号'}）——请打开审批页确认",
        )


def extract_interrupt_payload(result: dict) -> dict | None:
    """从中断结果提取 ask_human 的 question/options（P1⑧）。非提问中断返回 None。"""
    for it in result.get("__interrupt__") or []:
        val = getattr(it, "value", it)
        try:
            if isinstance(val, dict):
                for req in val.get("action_requests") or []:
                    if req.get("name") == "ask_human":
                        args = req.get("args") or {}
                        options = [
                            o.strip() for o in str(args.get("options", "")).split("|") if o.strip()
                        ]
                        return {"question": str(args.get("question", "")), "options": options}
        except AttributeError:
            continue
    return None


def _remove_pending(thread_id: str) -> None:
    if not PENDING_PATH.exists():
        return
    pending = [p for p in list_pending_approvals() if p["thread_id"] != thread_id]
    PENDING_PATH.write_text(json.dumps(pending, ensure_ascii=False), encoding="utf-8")


async def run_hosted_cycle(
    agent, thread_id: str | None, instruction: str, account: str = ""
) -> dict:
    """触发一轮托管循环：从新 thread 运行到审批中断点。

    thread_id 不传时自动生成唯一 ID——严禁跨运行复用 thread_id，
    否则残留中断态会污染消息历史（见 design.md 已知问题）。
    account：账号名，随中断写入 pending 供审批恢复端点加载正确画像。
    """
    thread_id = thread_id or f"cycle-{uuid.uuid4().hex[:12]}"
    audit.record("cycle_started", thread_id=thread_id, instruction=instruction)
    try:
        result = await agent.ainvoke(
            {"messages": [HumanMessage(instruction)]},
            config={"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}},
        )
    except Exception as exc:
        audit.record("cycle_failed", thread_id=thread_id, error=str(exc))
        raise
    if "__interrupt__" in result:
        payload = extract_interrupt_payload(result)
        if payload:
            _add_pending(thread_id, instruction, account=account, kind="question", question=payload)
        else:
            _add_pending(thread_id, instruction, account=account)
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
    _remove_pending(thread_id)
    audit.record("cycle_completed", thread_id=thread_id)
    return result


def audit_list() -> list[dict]:
    return audit.list_entries()
