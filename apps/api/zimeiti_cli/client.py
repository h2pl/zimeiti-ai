"""zimeiti 命令行入口的 HTTP 客户端（stdlib urllib，零三方依赖）。

纯客户端：只调既有服务端 API，不持有任何模型凭据（key 轮换/fallback/门禁都
在服务端——cli-entry-point D3）。
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Iterator
from typing import Any, Protocol

DEFAULT_BASE = "http://127.0.0.1:8000"


class ApiError(RuntimeError):
    """API 错误（含连接失败）——消息为可行动的中文指引。"""


def _headers() -> dict[str, str]:
    return {"Content-Type": "application/json", "Origin": DEFAULT_BASE}


def _decode(raw: bytes) -> Any:
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:  # noqa: BLE001   非 JSON 响应（HTML 兜底等）如实透传
        return {"detail": raw[:200].decode("utf-8", "replace")}


def _raise_for_status(status: int, raw: bytes, method: str, path: str) -> None:
    if 200 <= status < 300:
        return
    body = _decode(raw)
    detail = ""
    if isinstance(body, dict):
        detail = str(body.get("detail") or body.get("message") or "")
    raise ApiError(f"{method} {path} 失败（HTTP {status}）：{detail[:200] or '服务端未给出原因'}")


def request(
    base: str,
    method: str,
    path: str,
    body: dict | None = None,
    timeout: float = 30.0,
) -> dict:
    """JSON 请求；连接失败时给出行动指引（D5 退出码契约的上游）。"""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{base}{path}", data=data, method=method, headers=_headers())
    try:
        # nosec B310：CLI 是本地开发者工具，连用户指定的后端（默认 127.0.0.1），
        # 非网络输入面——与仓库 pg.py/store.py 的 nosec 同范式。
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
            raw = resp.read()
            _raise_for_status(resp.status, raw, method, path)
            out = _decode(raw)
            return out if isinstance(out, dict) else {"data": out}
    except urllib.error.HTTPError as e:  # noqa: BLE001   HTTP 层错误已带状态码
        _raise_for_status(e.code, e.read() or b"", method, path)
        raise
    except ApiError:
        raise
    except Exception as e:  # noqa: BLE001   连接拒绝/超时/DNS——统一行动指引
        raise ApiError(
            f"无法连接后端 {base}（{type(e).__name__}）：请先启动服务"
            "（`make api` 或 `make dev`），或用 --base / ZIMEITI_API 指定地址"
        ) from e


def get(base: str, path: str, timeout: float = 30.0) -> dict:
    return request(base, "GET", path, timeout=timeout)


def post(base: str, path: str, body: dict | None = None, timeout: float = 60.0) -> dict:
    return request(base, "POST", path, body=body, timeout=timeout)


def delete(base: str, path: str, timeout: float = 30.0) -> dict:
    return request(base, "DELETE", path, timeout=timeout)


def _iter_sse(resp: _ReadLineLike) -> Iterator[tuple[str, str]]:
    """读 SSE 流：yield (event, data)；遇 [DONE] 结束。空/坏帧跳过。"""
    event = "message"
    while True:
        raw = resp.readline()
        if not raw:
            break
        line = raw.decode("utf-8", "replace").rstrip("\r\n")
        if not line:
            continue
        if line.startswith("event:"):
            event = line[6:].strip()
            continue
        if line.startswith("data:"):
            payload = line[5:].strip()
            if payload == "[DONE]":
                return
            text = payload[1:-1] if payload.startswith('"') and payload.endswith('"') else payload
            yield event, text
            event = "message"


class _ReadLineLike(Protocol):
    def readline(self) -> bytes:  # pragma: no cover - 协议定义
        ...


def sse_chat(
    base: str, message: str, session: str = "", timeout: float = 600.0
) -> Iterator[tuple[str, str]]:
    """POST /api/chat/stream，逐帧 yield (event, data)。"""
    body = {"message": message}
    if session:
        body["sessionId"] = session
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{base}/api/chat/stream", data=data, method="POST", headers=_headers()
    )
    # nosec B310：同上——本地 CLI 连用户指定的后端。
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
        if resp.status != 200:
            _raise_for_status(resp.status, resp.read(), "POST", "/api/chat/stream")
        yield from _iter_sse(resp)
