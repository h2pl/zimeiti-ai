"""诊断脚本：真模型 resume 400 的根因（打印模型实际收到的消息历史）。"""

import asyncio
import sys
import uuid

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.types import Command

from zimeiti_api import tools as tz
from zimeiti_api.config import DATABASE_URL
from zimeiti_api.runtime.graph import build_minimal_agent
from zimeiti_api.runtime.hosted import run_hosted_cycle

load_dotenv()


_received: list = []


class RecordingDeepSeek(ChatDeepSeek):
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        _received.append(list(messages))
        return super()._generate(messages, stop, run_manager, **kwargs)


async def main() -> None:
    tz.publish_calls.clear()
    model = RecordingDeepSeek(model="deepseek-chat", api_key=os_env_key(), timeout=120)
    thread_id = f"debug-resume-{uuid.uuid4().hex[:8]}"

    async with AsyncPostgresSaver.from_conn_string(DATABASE_URL) as async_saver:
        await async_saver.setup()
        agent_a = build_minimal_agent(model=model, checkpointer=async_saver)
        result = await run_hosted_cycle(agent_a, thread_id, "必须立即调用 publish 工具发布：topic=调试内容, content=正文。不要解释，直接调用工具。")
        print("INTERRUPTED:", "__interrupt__" in result)

        with PostgresSaver.from_conn_string(DATABASE_URL) as sync_saver:
            sync_saver.setup()
            agent_b = build_minimal_agent(model=model, checkpointer=sync_saver)
            try:
                final = agent_b.invoke(
                    Command(resume={"decisions": [{"type": "approve"}]}),
                    config={"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}},
                )
                print("RESUME OK, last:", final["messages"][-1].content)
            except Exception as exc:
                import traceback

                print(f"RESUME FAILED: {type(exc).__name__}: {exc}")
                traceback.print_exc()
                print("=" * 60)
                print("最后一次模型调用收到的消息历史（400 的现场）：")
                if _received:
                    for i, m in enumerate(_received[-1]):
                        tc = getattr(m, "tool_calls", None)
                        print(f"  [{i}] {m.type}: {m.content[:60]!r} tool_calls={bool(tc)}")


def os_env_key() -> str:
    import os

    return os.environ["DEEPSEEK_API_KEY"]


if __name__ == "__main__":
    if sys.platform == "win32":
        from asyncio import WindowsSelectorEventLoopPolicy
        asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
