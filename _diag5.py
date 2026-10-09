import asyncio
import os
import sys
import uuid

if sys.platform == "win32":
    from asyncio import WindowsSelectorEventLoopPolicy
    asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())

sys.path.insert(0, "apps/api")
sys.path.insert(0, "apps/api/tests")

from dotenv import load_dotenv

load_dotenv()

import test_tools_chain as ttc
from zimeiti_api.checkpoints import get_checkpointer
from zimeiti_api.hosted import run_hosted_cycle, resume_after_approval
from zimeiti_api.publisher import PublishExecutor



def ttc_test_responses():
    from langchain_core.messages import AIMessage

    return [
        AIMessage(content="", tool_calls=[{'name': 'discover_topics', 'args': {'manual_direction': 'AI 提效指南'}, 'id': 't1'}]),
        AIMessage(content="", tool_calls=[{'name': 'select_topic', 'args': {'title': 'AI 提效指南'}, 'id': 't2'}]),
        AIMessage(content="", tool_calls=[{'name': 'create_drafts', 'args': {}, 'id': 't3'}]),
        AIMessage(content=ttc.GOOD_JSON),
        AIMessage(content="", tool_calls=[{'name': 'publish', 'args': {}, 'id': 't4'}]),
        AIMessage(content='发布完成'),
    ]


async def main():
    platform_calls = []
    import zimeiti_api.tools as tools_mod

    orig = tools_mod.default_platform_call
    tools_mod.default_platform_call = lambda d: (platform_calls.append(d["title"]), orig(d))[1]

    model = ttc.SeqModel(responses=ttc_test_responses())
    thread_id = f"diag5-{uuid.uuid4().hex[:8]}"
    async with get_checkpointer() as saver:
        agent = ttc._agent(model, saver, ttc._diag_tmp())
        cycle = await run_hosted_cycle(agent, thread_id, "做一期 AI 提效内容并发布")
        res = await resume_after_approval(agent, thread_id, approved=True)
        final = await resume_after_approval(agent, thread_id, approved=True)
        for m in final["messages"][-5:]:
            tc = getattr(m, "tool_calls", None)
            print(f"{m.type}: {str(m.content)[:70]!r} tc={[t['name'] for t in tc] if tc else []}")
        print("platform_calls:", platform_calls)


asyncio.run(main())
