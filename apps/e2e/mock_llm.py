"""OpenAI 兼容流式 mock LLM（browser-e2e 专用）。

zimeiti 后端以显式环境变量指向本端点（OPENAI_BASE_URL），使对话/画像向导
走真实后端链路但模型响应确定性（MOCK: 前缀）。端口 18900 仅回环。
"""

from __future__ import annotations

import asyncio
import json
import threading

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

MOCK_PORT = 18900


def _last_user_text(messages: list) -> str:
    for m in reversed(messages or []):
        if m.get("role") == "user":
            c = m.get("content")
            if isinstance(c, list):
                return " ".join(str(p.get("text", "")) for p in c if isinstance(p, dict))
            return str(c or "")
    return ""


def _reply_for(messages: list) -> str:
    user = _last_user_text(messages).strip()
    head = user[:60] if user else "(空消息)"
    return f"MOCK: 已收到「{head}」——browser-e2e 确定性回复，链路畅通。"


def create_app() -> FastAPI:
    api = FastAPI()

    @api.post("/v1/chat/completions")
    async def completions(request: Request):
        body = await request.json()
        reply = _reply_for(body.get("messages") or [])
        if body.get("stream"):
            chunk = {
                "id": "e2e-mock",
                "object": "chat.completion.chunk",
                "choices": [{"index": 0, "delta": {}, "finish_reason": None}],
            }

            async def gen():
                for ch in reply:
                    chunk["choices"][0]["delta"] = {"content": ch}
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.005)
                chunk["choices"][0]["delta"] = {}
                chunk["choices"][0]["finish_reason"] = "stop"
                yield f"data: {json.dumps(chunk)}\n\n"
                yield "data: [DONE]\n\n"

            return StreamingResponse(gen(), media_type="text/event-stream")
        return JSONResponse(
            {
                "id": "e2e-mock",
                "object": "chat.completion",
                "choices": [
                    {"index": 0, "message": {"role": "assistant", "content": reply}, "finish_reason": "stop"}
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 8, "total_tokens": 9},
            }
        )

    return api


class MockLLMServer:
    """线程内 uvicorn；start/stop 可重入（每端一轮）。"""

    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._server: uvicorn.Server | None = None

    def start(self) -> None:
        config = uvicorn.Config(
            create_app(), host="127.0.0.1", port=MOCK_PORT, log_level="error"
        )
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(target=self._server.run, daemon=True)
        self._thread.start()
        for _ in range(50):
            if self._server.started:
                return
            threading.Event().wait(0.1)
        raise RuntimeError("mock LLM 5s 未就绪")

    def stop(self) -> None:
        if self._server is not None:
            self._server.should_exit = True
        if self._thread is not None:
            self._thread.join(timeout=5)
        self._thread = None
        self._server = None
