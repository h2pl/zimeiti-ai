"""Zimeiti AI — FastAPI 后端组装层（backend-restructure 变更）。

本文件只做组装：建 app、注册护栏中间件、include 各域 APIRouter、
静态资源路由。业务端点实现位于 zimeiti_api 各领域子包：

    core/       路径/env/代理/PG 数据层等基础设施
    governance/ 本机写守卫（护栏）
    platforms/  7 平台登录/发布/取数适配
    content/    画像/技能/选题/排期/产物/上传/趋势
    operations/ 环境面板/模型设置
    runtime/    对话链路/agent 运行时/服务状态

分层单向：runtime → {governance, platforms, content, operations, core}；
content/operations/platforms → core；core 不依赖业务包。
"""

from __future__ import annotations

import asyncio
import os
import sys

# psycopg 异步（checkpointer）不能用 Windows 默认 ProactorEventLoop，须 Selector
# 策略（pg-data-layer 变更）。`python -m uvicorn app:app` 先建 loop 再 import 本
# 文件、设置已晚——生产启动走 `python -m zimeiti_api`（建 loop 前设策略）；此处保留服务
# 「先 import app、后建 loop」的上下文（测试/脚本）。
if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from zimeiti_api import chat_router as _chat_router
from zimeiti_api import status_router as _status_router
from zimeiti_api import usage_router as _usage_router
from zimeiti_api.automations import router as _automations_router
from zimeiti_api.automations import scheduler as _auto_scheduler
from zimeiti_api.content import ideas as _ideas_router
from zimeiti_api.content import outputs as _outputs_router
from zimeiti_api.content import personas as _personas_router
from zimeiti_api.content import schedule as _schedule_router
from zimeiti_api.content import skills as _skills_router
from zimeiti_api.content import trends as _trends_router
from zimeiti_api.content import uploads as _uploads_router
from zimeiti_api.core import pg as _pg
from zimeiti_api.core.paths import ENV_FILE, REACT_DIR, STATIC_DIR
from zimeiti_api.governance import guard as _guard
from zimeiti_api.operations import env as _env_router
from zimeiti_api.operations import models as _models_router
from zimeiti_api.platforms import accounts as _accounts_router
from zimeiti_api.platforms import analytics as _analytics_router
from zimeiti_api.platforms import login as _login_router
from zimeiti_api.platforms import publish as _publish_router
from zimeiti_api.platforms import wechat as _wechat_router
from zimeiti_api.platforms.wechat import _stop_mp_login_on_shutdown
from zimeiti_autonomous import guardrails as _auto_guard
from zimeiti_autonomous import router as _flows_router
from zimeiti_autonomous import runner as _auto_runner
from zimeiti_harness import contract as _harness_contract
from zimeiti_harness.runtime import agent_runtime as _agent_runtime

# 依赖注入（组装层职责，分层单向）：业务侧不 import harness 的 agent 入口，
# 由本组装层统一注入——画像增强（personas）与定时任务 prompt 型（scheduler）。
# harness 的技能目录 provider 同理反向注入：harness 不知道 content 的存在。
_personas_router.set_enhance_runtime(_agent_runtime.ask_sync)
_auto_scheduler.set_ask_sync(_agent_runtime.ask_sync)
_harness_contract.register_skills_provider(_skills_router.get_skills)
_auto_runner.set_agent_entry(
    _agent_runtime.ask_sync
)  # 自主运营流程的 agent 入口（注入，非 import）


def _budget_provider() -> dict:
    """护栏的预算用量来源（注入，非 import——分层纪律）。"""
    from zimeiti_harness.usage import summary as _s

    u = _s()
    return {"spent_usd": u.get("cost_usd"), "partial": bool(u.get("cost_usd_partial"))}


_auto_guard.set_budget_provider(_budget_provider)

load_dotenv(ENV_FILE, override=False)  # 已存在环境变量优先（同原 _load_dotenv 语义）


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    """启动时校验并初始化 PostgreSQL（fail-fast，pg-data-layer 变更 D6）；
    关机时回收公众号扫码进程与 PG 连接池。"""
    ok, err = await asyncio.to_thread(_pg.verify)
    if not ok:
        print("\n[zimeiti] PostgreSQL 不可用，服务退出（fail-fast）。", file=sys.stderr)
        print(f"  DATABASE_URL = {_pg.database_url()}", file=sys.stderr)
        print(f"  错误: {err}", file=sys.stderr)
        print(
            "  排查: 1) PostgreSQL 是否在运行 2) .env 的 DATABASE_URL 是否正确 3) 目标库是否已创建",
            file=sys.stderr,
        )
        raise RuntimeError(f"PostgreSQL 不可用: {err}")
    await asyncio.to_thread(_pg.setup)  # 业务表（幂等）
    await _pg.setup_checkpointer()  # checkpoint 表 + 连接池
    _agent_runtime.set_main_loop(asyncio.get_running_loop())  # 线程侧 ask_sync 投回主循环
    from zimeiti_harness.runtime import fingerprint as _fp

    _fp.capture()  # 固化启动指纹：代码变更未重启时 chat 入口给出可行动错误（stale-process-guard）
    _trends_router.start_trends_warmup()  # 热点缓存后台保热（冷抓 12s+ 的空窗不该让用户等）
    try:
        from zimeiti_harness.memory import store as _mem

        await asyncio.to_thread(_mem.setup)  # 记忆表（幂等）
    except Exception as e:  # noqa: BLE001  记忆表不可用不阻断启动（对话降级无记忆）
        print(f"[memory] 表初始化失败（无碍，对话继续）：{e}")
    try:
        from zimeiti_autonomous import store as _flow_store

        await asyncio.to_thread(_flow_store.setup)  # 流程表（幂等）
        from zimeiti_harness import usage as _usage

        await asyncio.to_thread(_usage.setup)  # 用量表（幂等）
        from .automations import scheduler as _auto_sched
        from .automations import store as _auto_store

        await asyncio.to_thread(_auto_store.setup)  # 自动化表（幂等）
        _auto_sched.start()  # 定时任务调度循环（任务持久化在 PG，重启不丢）
    except Exception as e:  # noqa: BLE001  自动化不可用不阻断启动
        print(f"[automations] 初始化失败（无碍）：{e}")
    yield
    _stop_mp_login_on_shutdown()
    await _pg.close_checkpointer()


app = FastAPI(title="Zimeiti AI", docs_url=None, redoc_url=None, lifespan=_lifespan)

# 跨域 / Host 中间件（governance）：放行本机工作台回环来源（对齐旧 app.py 中间件层）
app.add_middleware(
    CORSMiddleware,
    allow_origins=_guard._LOCAL_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Host 校验（governance）：本机名单 + 本地代理转发识别（IDE 端口转发场景）
app.middleware("http")(_guard.trusted_host_guard)

# 护栏中间件（governance）：仅放行本机工作台发起的写请求
app.middleware("http")(_guard.local_write_guard)


# ---- 静态资源（app 级，非业务端点）----
@app.get("/")
async def index():
    no_cache = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
    }
    react_index = REACT_DIR / "index.html"
    if react_index.is_file():
        return FileResponse(react_index, media_type="text/html", headers=no_cache)
    return FileResponse(STATIC_DIR / "index.html", media_type="text/html", headers=no_cache)


@app.get("/onepage")
async def onepage():
    return FileResponse(STATIC_DIR / "onepage.html", media_type="text/html")


@app.get("/assets/{path:path}")
async def react_assets(path: str):
    base = (REACT_DIR / "assets").resolve()
    fp = (REACT_DIR / "assets" / path).resolve()
    if base != fp and base not in fp.parents:
        raise HTTPException(403, "非法路径")
    if not fp.is_file():
        raise HTTPException(404)
    return FileResponse(fp, headers={"Cache-Control": "public, max-age=31536000, immutable"})


@app.get("/static/{path:path}")
async def static_file(path: str):
    base = STATIC_DIR.resolve()
    fp = (STATIC_DIR / path).resolve()
    if base != fp and base not in fp.parents:
        raise HTTPException(403, "非法路径")
    if not fp.is_file():
        raise HTTPException(404)
    headers = (
        {"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache"}
        if fp.suffix.lower() in {".html", ".htm"}
        else {}
    )
    return FileResponse(fp, headers=headers)


# ---- 各域路由（注册序即匹配序：/api/analytics/platforms 先于 /api/analytics/{platform}）----
for _r in (
    _status_router.router,  # /api/status
    _personas_router.router,  # /api/personas, /api/persona/{name}...
    _skills_router.router,  # /api/skills, /api/skill/{name}
    _env_router.router,  # /api/env...
    _models_router.router,  # /api/settings/models...
    _chat_router.router,  # /api/chat..., /api/skill, /api/session/{key}
    _outputs_router.router,  # /api/outputs, /api/output/{path}, /api/media/{path}
    _uploads_router.router,  # /api/upload...
    _login_router.router,  # /api/accounts, /api/login/{platform}..., /api/logout/{platform}
    _accounts_router.router,  # /api/accounts, /api/accounts/{platform}/whoami
    _wechat_router.router,  # /api/accounts/{platform}/credentials|mp-login（wechat-oa 凭证/扫码）
    _analytics_router.router,  # /api/analytics...
    _publish_router.router,  # /api/publish...
    _ideas_router.router,  # /api/ideas...
    _schedule_router.router,  # /api/schedule...
    _trends_router.router,  # /api/trends
    _automations_router.router,  # /api/automations...（定时任务）
    _usage_router.router,  # /api/usage
    _flows_router.router,  # /api/flows（自主运营流程编排，autonomous-flow）
):
    app.include_router(_r)
