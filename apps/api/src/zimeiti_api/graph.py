"""最小执行图（双形态共用，T1 定案）。

工作台形态：用户 Web/对话逐环节驱动（Easel 式交互）。
托管形态：定时/事件触发 + 主 agent 编排 + 审批 interrupt（xiaobei 式治理）。
差别只在「谁触发」与「interrupt 等待的介质」；工具/subagent/审批配置完全共用。
"""

from pathlib import Path
from typing import Any

from deepagents import create_deep_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph

from zimeiti_api.tools import build_default_tools

SYSTEM_PROMPT = (
    "你是 zimeiti-ai 自媒体运营 agent。"
    "按用户/托管循环的指示完成选题、创作与发布。"
    "选题与发布都需要人工参与：选题要等用户挑选，发布动作会自动进入人工审批。"
)


def build_minimal_agent(
    model: BaseChatModel,
    checkpointer: BaseCheckpointSaver,
    profile: dict[str, Any],
    executor: Any,
    cycle_dir: Path | str,
    tools: list | None = None,
    output_root: Path | str | None = None,
    platform_router: Any | None = None,
) -> CompiledStateGraph:
    """构建最小闭环 agent。

    tools 为 None 时使用默认工具集（含合规/执行器/闸门全接线，评审 C1-C4 修复）；
    platform_router 可注入平台调用路由（默认 real_platform_router，测试注入记录型）；
    测试可显式传入精简工具集（如仅 stub publish）验证循环语义。
    """
    all_tools = (
        tools
        if tools is not None
        else build_default_tools(profile, model, executor, cycle_dir, output_root, platform_router)
    )
    return create_deep_agent(
        model=model,
        tools=list(all_tools),
        system_prompt=SYSTEM_PROMPT,
        # 选题/发布是人工闸门（宪法 I；PRD A1/A3）；ask_human 支持执行中结构化提问
        # （P1⑧，参考: Easel gateway_questions——工具不执行，人答以 respond 决策回填）
        interrupt_on={"publish": True, "select_topic": True, "ask_human": True},
        checkpointer=checkpointer,
    )
