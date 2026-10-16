"""compaction 前 episodic flush（agent-memory-system，design D3）。

deepagents 的 SummarizationMiddleware 无公开前后钩子，用替代挂点：agent_runtime.ask()
在放行前调用本模块——消息数超过阈值时，把最后 N 条消息截断写入 episodic 记忆
（origin=system，importance=3 低权重，只作保险不作主来源）。零 LLM 成本。
"""

from __future__ import annotations

from . import store


def flush_if_long(session_key: str, messages: list[dict]) -> int:
    """消息数超阈值时截断落库，返回写入条数（0=未触发）。"""
    if len(messages) <= store._FLUSH_THRESHOLD:
        return 0
    tail = messages[-store._FLUSH_TAIL :]
    lines = []
    for m in tail:
        role = m.get("role", "?")
        content = str(m.get("content", ""))[: store._FLUSH_CHARS]
        lines.append(f"[{role}] {content}")
    store.record(
        "\n".join(lines),
        origin="system",
        importance=3,
        tags=["flush"],
        scope="episodic",
    )
    return 1
