"""临时编辑脚本：抽取 _stream_frames + 重构 chat_stream（用完即删）。"""
from pathlib import Path

f = Path("src/zimeiti_api/app.py")
s = f.read_text(encoding="utf-8")

old = '''    @app.post("/api/chat/sessions/{thread_id}/stream")
    async def chat_stream(thread_id: str, body: dict):
        """流式对话（D2）：token 增量 + interrupt 帧 + done。"""
        from zimeiti_api.runtime.chat import get_session

        session = get_session(thread_id)
        if session is None:
            raise HTTPException(status_code=404, detail=f"会话不存在: {thread_id}")
        message = str(body.get("message", "")).strip()
        if not message:
            raise HTTPException(status_code=400, detail="消息不能为空")
        account = session["account"]
        from zimeiti_api.content.profiles import load_profile
        from zimeiti_api.models import get_model

        profile = load_profile(account)

        from zimeiti_api.runtime.checkpoints import get_checkpointer
        from zimeiti_api.runtime.graph import build_minimal_agent

        async def gen():
            from langchain_core.messages import AIMessageChunk, HumanMessage

            yield _sse("start", {"thread_id": thread_id})
            try:
                async with get_checkpointer() as saver:
                    agent = build_minimal_agent(
                        get_model(), saver, profile, EXECUTOR, cycle_dir=str(
                            Path(OUTPUTS_DIR) / account / thread_id
                        )
                    )
                    config: RunnableConfig = {
                        "configurable": {"thread_id": thread_id, "checkpoint_ns": ""}
                    }
                    # stream_mode 双模式为 langgraph 运行时合法参数（mypy overload 不覆盖列表形态）
                    stream = cast(
                        "AsyncIterator[tuple[str, Any]]",
                        agent.astream(
                            {"messages": [HumanMessage(message)]},
                            config,
                            stream_mode=["messages", "updates"],
                        ),
                    )
                    async for mode, payload in stream:
                        if mode == "messages":
                            chunk, _meta = payload
                            if isinstance(chunk, AIMessageChunk) and chunk.content:
                                # S2：list 型 content 取 str 块拼接（评审 S2）
                                text = (
                                    chunk.text()
                                    if hasattr(chunk, "text")
                                    else str(chunk.content)
                                )
                                yield _sse("token", {"text": text})
                        elif isinstance(payload, dict) and "__interrupt__" in payload:
                            payloads = hosted.extract_interrupt_payload(
                                {"__interrupt__": payload["__interrupt__"]}
                            )
                            if payloads:
                                hosted._add_pending(
                                    thread_id, message, account=account,
                                    kind="question", question=payloads,
                                )
                            else:
                                hosted._add_pending(thread_id, message, account=account)
                            audit.record("awaiting_approval", thread_id=thread_id)
                            # D5：interrupt 帧携带载荷（前端内联卡片免二次拉取）
                            yield _sse(
                                "interrupt",
                                {"pending": True, **(payloads or {})},
                            )
                touch_session(thread_id)
                yield _sse("done", {})
            except Exception as exc:  # noqa: BLE001 - 流内错误以 error 帧下发
                yield _sse("error", {"message": str(exc)[:300]})
                yield _sse("done", {})

        from fastapi.responses import StreamingResponse

        return StreamingResponse(gen(), media_type="text/event-stream")'''

new = '''    def _stream_frames(thread_id: str, account: str, inp: dict):
        """SSE 帧公共生成器（feat-chat-resume-tools D1/D2）：chat 与 resume 共用。

        token = AIMessageChunk 增量；tool = updates 节点执行（D2）；
        interrupt = 闸门（登记 pending + 携带载荷）；done/error 收尾。
        """
        from langchain_core.messages import HumanMessage

        from zimeiti_api.content.profiles import load_profile
        from zimeiti_api.models import get_model
        from zimeiti_api.runtime.checkpoints import get_checkpointer
        from zimeiti_api.runtime.graph import build_minimal_agent

        async def gen():
            profile = load_profile(account)
            yield _sse("start", {"thread_id": thread_id})
            try:
                async with get_checkpointer() as saver:
                    agent = build_minimal_agent(
                        get_model(), saver, profile, EXECUTOR, cycle_dir=str(
                            Path(OUTPUTS_DIR) / account / thread_id
                        )
                    )
                    config: RunnableConfig = {
                        "configurable": {"thread_id": thread_id, "checkpoint_ns": ""}
                    }
                    # stream_mode 双模式为 langgraph 运行时合法参数（mypy overload 不覆盖列表形态）
                    stream = cast(
                        "AsyncIterator[tuple[str, Any]]",
                        agent.astream(inp, config, stream_mode=["messages", "updates"]),
                    )
                    async for mode, payload in stream:
                        if mode == "messages":
                            chunk, _meta = payload
                            if isinstance(chunk, AIMessageChunk) and chunk.content:
                                text = (
                                    chunk.text()
                                    if hasattr(chunk, "text")
                                    else str(chunk.content)
                                )
                                yield _sse("token", {"text": text})
                        elif isinstance(payload, dict):
                            if "__interrupt__" in payload:
                                payloads = hosted.extract_interrupt_payload(
                                    {"__interrupt__": payload["__interrupt__"]}
                                )
                                if payloads:
                                    hosted._add_pending(
                                        thread_id, "", account=account,
                                        kind="question", question=payloads,
                                    )
                                else:
                                    hosted._add_pending(thread_id, "", account=account)
                                audit.record("awaiting_approval", thread_id=thread_id)
                                # D5：interrupt 帧携带载荷（前端内联卡片免二次拉取）
                                yield _sse("interrupt", {"pending": True, **(payloads or {})})
                            else:
                                # D2 tool 帧：updates 的单键节点名（__interrupt__ 除外）
                                for node in payload:
                                    if not node.startswith("__"):
                                        yield _sse("tool", {"tool": node, "status": "done"})
                touch_session(thread_id)
                yield _sse("done", {})
            except Exception as exc:  # noqa: BLE001 - 流内错误以 error 帧下发
                yield _sse("error", {"message": str(exc)[:300]})
                yield _sse("done", {})

        return gen()

    @app.post("/api/chat/sessions/{thread_id}/stream")
    async def chat_stream(thread_id: str, body: dict):
        """流式对话（D2）：token/tool/interrupt/done 帧。"""
        from zimeiti_api.runtime.chat import get_session

        session = get_session(thread_id)
        if session is None:
            raise HTTPException(status_code=404, detail=f"会话不存在: {thread_id}")
        message = str(body.get("message", "")).strip()
        if not message:
            raise HTTPException(status_code=400, detail="消息不能为空")
        account = session["account"]
        from fastapi.responses import StreamingResponse

        gen = _stream_frames(thread_id, account, {"messages": [HumanMessage(message)]})
        return StreamingResponse(gen, media_type="text/event-stream")'''

assert old in s, "anchor not found"
s = s.replace(old, new)
f.write_text(s, encoding="utf-8")
print("refactored")
