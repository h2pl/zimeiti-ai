"""全局路径锚点（core）。

原 app.py 顶层的目录/路径常量集中于此——所有域共用同一路径真相源。
"""

from __future__ import annotations

import sys
from pathlib import Path

# paths.py 位于 apps/api/zimeiti_api/core/paths.py
#   parents[0]=core, [1]=zimeiti_api, [2]=api, [3]=apps
_API_DIR = Path(__file__).resolve().parents[2]  # apps/api（.env / 启动入口所在）
REPO_ROOT = Path(__file__).resolve().parents[3]  # apps（数据目录与 skills 实际所在）

PROJECT_ROOT = REPO_ROOT  # 数据根：outputs/profiles/skills
PROFILES_DIR = PROJECT_ROOT / "profiles"
SKILLS_DIR = PROJECT_ROOT / "skills"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
ENV_FILE = _API_DIR / ".env"  # .env 随 API 包（app.py 同源加载）

# 前端资产归位 apps/web（backend-restructure）：api 目录不再存放任何前端/静态资产。
# STATIC_DIR = Easel 落地页静态资产（onepage 等，随前端项目走）；
# REACT_DIR = apps/web 的 Vite 构建产物（单一事实源，不再复制进 api）。
STATIC_DIR = REPO_ROOT / "web" / "static"
REACT_DIR = REPO_ROOT / "web" / "dist"


# 制作层/直接执行层/chat 超时统一走 zimeiti_api/core/timeouts.py（CLI/Web/skill 三入口单一真相源）

SHARED_SCRIPTS = SKILLS_DIR / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))


BROWSER_PROFILES = Path.home() / ".easel-browser-profiles"
LOGIN_DIR = OUTPUTS_DIR / "_login"
PUBLISH_DIR = OUTPUTS_DIR / "_publish"  # 异步发布的状态/验证码文件（抖音发布可能触发短信墙）
PROFILE_BUILD_DIR = OUTPUTS_DIR / "_profile_build"  # 异步画像构建的状态文件（避免长请求被代理超时）
DEBUG_DIR = OUTPUTS_DIR / "_debug"  # 诊断日志（对话流收尾情况等），_ 前缀不进内容库
SESSIONS_DIR = OUTPUTS_DIR / "_sessions"  # 每会话最近一轮的完整结果，供 SSE 连接中断后前端取回
SYSTEM_TOPLEVEL_DIRS = {"analytics"}

# ---- 媒体扩展名与 outputs 路径安全（自 content/outputs.py 下沉）----
# platforms(publish)/runtime(chat)/content(outputs,uploads) 三层共用；
# 分层单向（runtime → content/platforms → core）要求共用件放 core。
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"}
VIDEO_EXTS = {".mp4", ".mov", ".webm", ".m4v"}


def _safe_output_target(rel: str, *, must_exist: bool = True) -> Path:
    """解析到 outputs/ 内的文件或目录（防穿越）。与 _safe_output_path 不同：允许目录、
    可要求不必已存在（上传新文件时）。永远拒绝 outputs/ 根本身。"""
    from fastapi import HTTPException  # 局部导入：core 保持无框架顶层依赖

    full = (OUTPUTS_DIR / rel).resolve()
    root = OUTPUTS_DIR.resolve()
    if full == root or root not in full.parents:
        raise HTTPException(403, "非法路径")
    if must_exist and not full.exists():
        raise HTTPException(404, "不存在")
    return full


def _safe_output_path(rel: str) -> Path:
    "把相对路径解析到 outputs/ 内，防路径穿越。"
    from fastapi import HTTPException  # 局部导入：core 保持无框架顶层依赖

    full = (OUTPUTS_DIR / rel).resolve()
    root = OUTPUTS_DIR.resolve()
    if root != full and root not in full.parents:
        raise HTTPException(403, "非法路径")
    if not full.is_file():
        raise HTTPException(404, "文件不存在")
    return full
