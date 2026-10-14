"""内容库产物（content）：树/内容/媒体/删除 + 路径安全。"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..core.paths import (
    IMAGE_EXTS,
    OUTPUTS_DIR,
    SYSTEM_TOPLEVEL_DIRS,
    VIDEO_EXTS,
    _safe_output_path,
    _safe_output_target,
)

router = APIRouter()

TEXT_EXTS = {
    ".txt",
    ".md",
    ".json",
    ".csv",
    ".log",
    ".py",
    ".js",
    ".ts",
    ".html",
    ".htm",
    ".css",
    ".xml",
    ".yaml",
    ".yml",
    ".srt",
    ".vtt",
}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}


def _file_kind(name: str) -> str:
    ext = Path(name).suffix.lower()
    if ext in IMAGE_EXTS:
        return "image"
    if ext in VIDEO_EXTS:
        return "video"
    if ext in AUDIO_EXTS:
        return "audio"
    if ext in TEXT_EXTS:
        return "text"
    return "binary"


def _file_meta(f: Path, rel: str) -> dict:
    try:
        st = f.stat()
        mtime, size = int(st.st_mtime), st.st_size
    except OSError:
        mtime, size = 0, 0
    return {
        "name": f.name,
        "path": rel,
        "kind": _file_kind(f.name),
        "mtime": mtime,
        "size": size,
    }


def _build_output_node(path: Path, rel: str) -> dict:
    """递归构建产物树节点：文件→file 节点；目录→dir 节点带 children + 递归 fileCount。"""
    if path.is_dir():
        children = []
        for c in sorted(path.iterdir()):
            if c.name.startswith("."):  # 嵌套层只跳隐藏文件；_base.mp4 等以 _ 开头的产物要保留
                continue
            children.append(_build_output_node(c, f"{rel}/{c.name}"))
        mtime = max((x["mtime"] for x in children), default=int(path.stat().st_mtime))
        file_count = sum(x.get("fileCount", 1) if x["type"] == "dir" else 1 for x in children)
        return {
            "name": path.name,
            "type": "dir",
            "path": rel,
            "mtime": mtime,
            "children": children,
            "fileCount": file_count,
        }
    m = _file_meta(path, rel)
    m["type"] = "file"
    return m


def _read_project_meta(proj: Path) -> dict:
    """读项目目录的 .easel.json 展示头，附封面/成品的解析路径供前端富展示。

    只取展示相关字段（不含编排 steps）。cover 解析优先级：
    展示头声明的 cover → 首个成品媒体 → 目录内首张图/视频（兜底）。
    """
    mf = proj / ".easel.json"
    if not mf.is_file():
        return {}
    try:
        data = json.loads(mf.read_text(encoding="utf-8"))
    except Exception:
        return {}
    meta = {
        k: data.get(k)
        for k in (
            "title",
            "summary",
            "platform",
            "kind",
            "status",
            "tags",
            "deliverables",
        )
        if data.get(k) not in (None, "", [])
    }
    if not meta:
        return {}

    def _rel_if_exists(name: str) -> str:
        return f"{proj.name}/{name}" if name and (proj / name).is_file() else ""

    # 封面解析
    cover_rel = ""
    declared = data.get("cover")
    if declared and (proj / declared).is_file():
        cover_rel = f"{proj.name}/{declared}"
    if not cover_rel:
        for d in data.get("deliverables") or []:
            if _file_kind(d) in ("image", "video") and (proj / d).is_file():
                cover_rel = f"{proj.name}/{d}"
                break
    if cover_rel:
        meta["cover"] = cover_rel
    # 成品路径（前端「成品区」高亮用）：解析为 outputs 相对路径，只留真实存在的
    meta["deliverablePaths"] = [
        f"{proj.name}/{d}" for d in (data.get("deliverables") or []) if (proj / d).is_file()
    ]
    return meta


def get_output_tree() -> list[dict]:
    if not OUTPUTS_DIR.is_dir():
        return []
    items = []
    for e in sorted(OUTPUTS_DIR.iterdir()):
        # 内容库只展示「项目目录」：跳过系统目录(_login/_publish/...)、隐藏项、
        # 以及根目录散文件（按新规约产物必在项目目录内，根散文件=系统状态/残渣）。
        if e.name.startswith(".") or e.name.startswith("_"):
            continue
        if not e.is_dir() or e.name in SYSTEM_TOPLEVEL_DIRS:
            continue
        node = _build_output_node(e, e.name)
        meta = _read_project_meta(e)
        if meta:
            node["meta"] = meta
        items.append(node)
    # 按最后修改时间倒序：最近产物排最前（供工作台「最近产物」与内容库时间排序）
    return sorted(items, key=lambda x: x.get("mtime", 0), reverse=True)


@router.get("/api/outputs")
def api_outputs():
    # 产物树是全量递归扫描（文件量大时单次可达数十秒）。必须是同步 handler：
    # FastAPI 会自动放入线程池执行；若写成 async def 直调，扫描期间会阻塞事件循环，
    # 全站所有请求（含 /api/status）一起挂起等它。
    return get_output_tree()


@router.get("/api/output/{path:path}")
async def api_output(path: str):
    """文本产物内容。二进制/媒体返回 isBinary=true，前端改用 /api/media。"""
    full = _safe_output_path(path)
    kind = _file_kind(full.name)
    if kind not in ("text",):
        return {"path": path, "content": "", "kind": kind, "isBinary": True}
    try:
        return {
            "path": path,
            "content": full.read_text(encoding="utf-8"),
            "kind": "text",
            "isBinary": False,
        }
    except UnicodeDecodeError:
        return {"path": path, "content": "", "kind": "binary", "isBinary": True}


@router.get("/api/media/{path:path}")
async def api_media(path: str):
    """原样输出媒体文件（图片/视频/音频/HTML/PDF），供 <img>/<video>/iframe/下载。"""
    full = _safe_output_path(path)
    # HTML 预览会在本地被就地重新生成（如 gzh-design 重排/内联图片），必须禁缓存，
    # 否则浏览器/代理按启发式缓存旧版 → 内容库 iframe 打开的是过期预览（复制粘贴带旧图 URL）。
    headers = (
        {"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache"}
        if full.suffix.lower() in {".html", ".htm"}
        else {}
    )
    return FileResponse(full, headers=headers)


# 系统数据目录/文件——不允许从内容库删除（删了会丢登录态/日历/发布记录）
PROTECTED_OUTPUTS = {"_login", "_analytics", "_schedule.json", "_ideas.json"}


def _is_protected(full: Path) -> bool:
    """路径的顶层段是否属于受保护的系统项。"""
    try:
        rel = full.relative_to(OUTPUTS_DIR.resolve())
    except ValueError:
        return True
    if not rel.parts:
        return True
    first = rel.parts[0]
    return (
        first.startswith("_")
        or first.startswith(".")
        or first in PROTECTED_OUTPUTS
        or first.lower() in {"analytics", "wechat"}
    )


@router.delete("/api/output/{path:path}")
async def api_output_delete(path: str):
    """删除内容库里的单个文件或整个项目目录。系统数据（_login/_analytics/日历/发布记录）受保护。"""
    full = _safe_output_target(path)
    if _is_protected(full):
        raise HTTPException(403, "系统数据受保护，不可从内容库删除")
    is_dir = full.is_dir()
    try:
        if is_dir:
            shutil.rmtree(full)
        else:
            full.unlink()
    except OSError as e:
        raise HTTPException(500, f"删除失败：{e}") from e
    return {"ok": True, "deleted": path, "kind": "dir" if is_dir else "file"}
