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


def dump(res, tag):
    print(f"--- {tag}: keys={list(res.keys())}")
    for m in res["messages"][-4:]:
        tc = getattr(m, "tool_calls", None)
        print(f"    {m.type}: {str(m.content)[:40]!r} tool_calls={[t['name'] for t in tc] if tc else []}")


async def main():
    os.environ["ZIMEITI_CREDENTIALS_DIR"] = "apps/api/_diag_creds4"
    os.makedirs("apps/api/_diag_creds4", exist_ok=True)
    open("apps/api/_diag_creds4/xhs-main.sealed", "w").write("x")

    model = ttc.SeqModel(responses=ttc_test_responses())
    thread_id = f"diag4-{uuid.uuid4().hex[:8]}"
    async with get_checkpointer() as saver:
        agent = ttc._agent(model, saver, ttc_test_tmp())
        result = await run_hosted_cycle(agent, thread_id, "做一期 AI 提效内容并发布")
        dump(result, "cycle")
        res = await resume_after_approval(agent, thread_id, approved=True)
        dump(res, "resume1")
        res2 = await resume_after_approval(agent, thread_id, approved=True)
        dump(res2, "resume2")


def ttc_test_tmp():
    import tempfile

    d = tempfile.mkdtemp(prefix="diag4-")
    import pathlib as _p

    return _p.Path(d) / "cycle"


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


asyncio.run(main())
