"""业务工具集（Task 2.2 起逐步充实）。

publish 为发布占位实现：Phase E 替换为真实平台发布脚本（读回对账）。
工具名 publish 与 design D3 的 interrupt_on 配置绑定。
publish_calls 记录实际调用（测试与审计观测用）。
"""

from langchain_core.tools import tool

publish_calls: list[str] = []


@tool
def publish(topic: str, content: str) -> str:
    """发布内容到指定平台。执行前必须经过人工审批（HITL）。"""
    publish_calls.append(topic)
    return f"published: {topic}"


publish_tool = publish
