"""本机写守卫（governance 护栏）。

local_write_guard：仅放行本机工作台发起的写请求（同源/回环），
挡浏览器跨站攻击。原 app.py 中间件层，行为零变化。
"""

from __future__ import annotations

import ipaddress
import os
import re
import urllib.parse

from fastapi import Request
from fastapi.responses import JSONResponse


def _local_ports(env_port: str) -> set[str]:
    """本机写守卫放行的端口集合：固定的 7860/7870/5173，加上 `--port`/EASEL_PORT
    实际配置的端口——否则自定义端口跑 Easel 时，前端自己发的写请求（包括发消息
    的 /api/chat/stream）会被 local_write_guard 当跨站请求 403 掉。"""
    return {"7860", "7870", "5173", (env_port or "").strip() or "7860"}


_LOCAL_PORTS = _local_ports(os.environ.get("EASEL_PORT", ""))
_LOCAL_ORIGINS = [
    f"http://{host}:{port}" for host in ("127.0.0.1", "localhost") for port in _LOCAL_PORTS
]
_LOCAL_ORIGINS += [
    o.strip() for o in os.environ.get("EASEL_EXTRA_ORIGINS", "").split(",") if o.strip()
]
_EXTRA_HOSTS = [h.strip() for h in os.environ.get("EASEL_EXTRA_HOSTS", "").split(",") if h.strip()]


# VSCode/code-server 等远程开发环境常通过 VSCODE_PROXY_URI 这个反代域名访问 Easel
# （真实连接仍是本机回环，代理在同一台机器上转发）；不识别这个域名会让通过代理
# 打开的页面从第一个请求起就被下面的 TrustedHostMiddleware/CORS 拒绝——收紧前
def _proxy_uri_origin(uri: str) -> tuple[str, str] | None:
    """从 VSCODE_PROXY_URI 里取反代域名，返回 (host, origin)；解析不出 host 则 None。"""
    if not uri:
        return None
    parsed = urllib.parse.urlparse(uri)
    if not parsed.hostname:
        return None
    return parsed.hostname, f"{parsed.scheme}://{parsed.hostname}"


_proxy_origin = _proxy_uri_origin(os.environ.get("VSCODE_PROXY_URI", ""))
if _proxy_origin:
    _EXTRA_HOSTS.append(_proxy_origin[0])
    _LOCAL_ORIGINS.append(_proxy_origin[1])


def _loopback_peer(request: Request) -> bool:
    """对端是否来自回环地址。只有「没有 Origin 可判」时才用作判据。"""
    client = request.client
    if client is None:
        return False
    host = client.host or ""
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


async def local_write_guard(request: Request, call_next):
    """拦住「别的网站让浏览器替我改本机状态」的写请求，同时不误伤本机调用。

    两条判据，按请求实际形态二选一：
    ① 带 Origin（浏览器跨站发起）：Origin 必须在 _LOCAL_ORIGINS 里，否则 403。
    ② 不带 Origin（curl / 本机脚本 / 测试客户端）：要求对端来自回环地址。

    局限（重要）：这套防护假定 Origin/Host 头不可伪造——对浏览器成立，对裸
    HTTP 客户端不成立。本进程仍监听 0.0.0.0（见文件底部 uvicorn.run，未随
    此中间件收紧，兼容 Docker/远程容器端口转发场景），因此局域网内能直连到
    这个端口的攻击者，只要手写 curl 一起伪造 `Origin`/`Host` 头就能绕过本
    中间件与下面的 TrustedHostMiddleware。这里防的是「浏览器打开恶意网页」
    这一类跨站攻击，不是「网络可达即视为可信」的边界——不要把本服务暴露在
    不受信任的网络（公共 WiFi、无防火墙的公网主机）上。
    """
    origin = request.headers.get("origin")
    if (
        request.url.path == "/api/clipper"
        and origin
        and re.fullmatch(r"chrome-extension://[a-p]{32}", origin)
    ):
        headers = {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": "POST",
            "Access-Control-Allow-Headers": "Authorization, Content-Type",
            "Vary": "Origin",
        }
        if request.method == "OPTIONS":
            return JSONResponse({}, headers=headers)
        response = await call_next(request)
        response.headers.update(headers)
        return response
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        allowed = False
        if origin:
            if origin in _LOCAL_ORIGINS:
                allowed = True
            else:
                # 同源放行：页面由本服务托管（如 :8000 直开）时，浏览器对 POST 也会带
                # 自身 Origin（http://127.0.0.1:8000）——与请求 Host 头一致即同源，
                # 属于本机工作台自己的页面。Host 头不可被跨站 JS 伪造，判据与 ① 同级。
                host = request.headers.get("host", "").strip().lower()
                origin_n = origin.strip().lower().rstrip("/")
                allowed = bool(host) and origin_n in (
                    f"http://{host}",
                    f"https://{host}",
                )
        else:
            allowed = _loopback_peer(request)
        if not allowed:
            return JSONResponse({"detail": "仅允许从本机工作台操作。"}, status_code=403)
    return await call_next(request)
