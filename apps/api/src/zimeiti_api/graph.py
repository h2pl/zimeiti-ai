"""最小执行图（Task 2.2）。

工作台与托管两形态共用：create_deep_agent 配置完全相同，
差别只在触发方式（Web 交互 / 定时任务）与 interrupt 等待介质（design T1）。
"""

from collections.abc import Sequence

from deepagents import create_deep_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph

from zimeiti_api.tools import publish_tool

SYSTEM_PROMPT = (
    "你是 zimeiti-ai 自媒体运营 agent。"
    "按用户/托管循环的指示完成选题、创作与发布。"
    "发布动作会自动进入人工审批。"
)


def build_minimal_agent(
    model: BaseChatModel,
    tools: Sequence | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> CompiledStateGraph:
    """构建最小闭环 agent：选题/创作工具 + 发布审批（interrupt_on）。"""
    all_tools = [publish_tool, *(tools or [])]
    return create_deep_agent(
        model=model,
        tools=all_tools,
        system_prompt=SYSTEM_PROMPT,
        interrupt_on={"publish": True},
        checkpointer=checkpointer,
    )
