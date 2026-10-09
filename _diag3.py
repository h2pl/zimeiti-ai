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


async def main():
    os.environ["ZIMEITI_CREDENTIALS_DIR"] = "apps/api/_diag_creds3"
    os.makedirs("apps/api/_diag_creds3", exist_ok=True)
    open("apps/api/_diag_creds3/xhs-main.sealed", "w").write("x")

    model = ttc.SeqModel(responses=ttc_test_responses())
    thread_id = f"diag3-{uuid.uuid4().hex[:8]}"
    async with get_checkpointer() as saver:
        tmp = _pathlib.Path("_diag_out")
        agent = ttc._agent(model, saver, tmp)
        result = await run_hosted_cycle(agent, thread_id, "做一期 AI 提效内容并发布")
        print("keys:", list(result.keys()))
        for i in range(6):
            state = await agent.aget_state({"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}})
            print(f"[{i}] next:", state.next)
            if not state.next:
                break
            result = await agent.ainvoke(None, config={"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}})
            print(f"[{i}] keys:", list(result.keys()))
            if "__interrupt__" in result:
                break


def ttc_test_responses():
    from langchain_core.messages import AIMessage

    return [
        AIMessage(content="", tool_calls=[{"name": "discover_topics", "args": {"manual_direction": "AI 提效指南"}, "id": "t1"}]),
        AIMessage(content="", tool_calls=[{"name": "select_topic", "args": {"title": "AI 提效指南"}, "id": "t2"}]),
        AIMessage(content="", tool_calls=[{"name": "create_drafts", "args": {}, "id": "t3"}]),
        AIMessage(content=ttc.GOOD_JSON),
        AIMessage(content="", tool_calls=[{"name": "publish", "args": {}, "id": "t4"}]),
        AIMessage(content="发布完成"),
    ]


import pathlib as _pathlib

def output_root_fix():
    return _pathlib.Path("_diag_out")

asyncio.run(main())
