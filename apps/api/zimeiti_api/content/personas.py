"""账号画像（content）：CRUD + 异步构建 + prompt 注入拼接。"""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..core.paths import PROFILE_BUILD_DIR, PROFILES_DIR
from .persona_core import (  # noqa: F401 —— chat_turn_message 供 runtime.chat 复用（再导出）
    _FILE_ORDER,
    chat_turn_message,
    load_profile_text,
    persona_prefix,
    profile_exists,
)

router = APIRouter()

# 画像增强的 agent 运行时（依赖注入，app.py 组装层经 set_enhance_runtime 接线）。
# 分层单向：content 不得 import runtime（runtime → content 才合法），故由组装层注入。
_enhance_runtime = None


def set_enhance_runtime(ask_sync) -> None:
    """注入 agent 运行时的 ask_sync（组装层 app.py 启动时调用一次）。"""
    global _enhance_runtime
    _enhance_runtime = ask_sync


def list_personas() -> list[dict]:
    if not PROFILES_DIR.is_dir():
        return []
    result = []
    for d in sorted(PROFILES_DIR.iterdir()):
        if d.is_dir() and d.name.startswith("_"):
            continue
        desc = ""
        identity = d / "identity.md"
        if identity.is_file():
            for line in identity.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith("<!--"):
                    desc = line[:80]
                    break
        result.append({"name": d.name, "description": desc})
    return result


def _persona_prefix(persona: str | None) -> str:
    """把画像作为消息前缀内联（复用 zimeiti_api.content.personas，与 CLI/skill 同源）。"""
    return persona_prefix(persona)


@router.get("/api/personas")
async def api_personas():
    return list_personas()


@router.get("/api/persona/{name}")
async def api_persona(name: str):
    text = load_profile_text(name)
    if not text:
        raise HTTPException(404, "画像不存在")
    return {"name": name, "content": text}


def _valid_persona_name(name: str) -> bool:
    return bool(name) and "/" not in name and "\\" not in name and not name.startswith((".", "_"))


def _persona_file_path(name: str, filename: str) -> Path:
    """校验画像名/文件名，返回 profiles/<name>/<filename> 的安全路径。"""
    if not _valid_persona_name(name):
        raise HTTPException(400, "画像名非法")
    if (
        not filename.endswith(".md")
        or "/" in filename
        or "\\" in filename
        or filename.startswith(".")
    ):
        raise HTTPException(400, "文件名非法")
    pd = (PROFILES_DIR / name).resolve()
    fp = (pd / filename).resolve()
    if pd != fp.parent or PROFILES_DIR.resolve() not in pd.parents:
        raise HTTPException(403, "非法路径")
    return fp


@router.get("/api/persona/{name}/files")
async def api_persona_files(name: str):
    """返回画像六维文件原文（按固定顺序 + 其余 .md），供在线编辑。"""
    if not profile_exists(name):
        raise HTTPException(404, "画像不存在")
    pd = PROFILES_DIR / name
    ordered = list(_FILE_ORDER) + sorted(
        f.name for f in pd.glob("*.md") if f.name not in _FILE_ORDER
    )
    files = []
    for fn in ordered:
        fp = pd / fn
        files.append(
            {
                "filename": fn,
                "content": fp.read_text(encoding="utf-8") if fp.is_file() else "",
            }
        )
    return {"name": name, "files": files}


class PersonaFileRequest(BaseModel):
    filename: str
    content: str


@router.put("/api/persona/{name}/file")
async def api_persona_file_save(name: str, req: PersonaFileRequest):
    """保存画像单个维度文件（原子写）。"""
    if not profile_exists(name):
        raise HTTPException(404, "画像不存在")
    fp = _persona_file_path(name, req.filename)
    tmp = fp.with_suffix(".md.tmp")
    tmp.write_text(req.content, encoding="utf-8")
    tmp.replace(fp)
    return {"ok": True, "filename": req.filename}


@router.delete("/api/persona/{name}")
async def api_persona_delete(name: str):
    """删除整个画像目录。"""
    if not _valid_persona_name(name):
        raise HTTPException(400, "画像名非法")
    pd = (PROFILES_DIR / name).resolve()
    if PROFILES_DIR.resolve() not in pd.parents or not pd.is_dir():
        raise HTTPException(404, "画像不存在")
    import shutil

    shutil.rmtree(pd)
    return {"ok": True, "deleted": name}


class ProfileBuildRequest(BaseModel):
    name: str
    form: dict


@router.post("/api/profile/build")
async def api_profile_build(req: ProfileBuildRequest):
    """首次引导：表单 → 写基线画像（确定性，秒可用）→ **后台**跑 agent 分析社媒链接增强。

    改异步：立即返回（基线已写、画像即可用），避免 agent 增强(~2min)阻塞请求被 code-server
    代理超时掐断（前端曾因此报 API 400）。前端轮询 /api/profile/build/status/{name} 看增强进度。
    """
    name = (req.name or "").strip()  # 自动去掉首尾空格
    if not name:
        raise HTTPException(400, "画像名不能为空（去掉首尾空格后为空，请输入有效名称）")
    if "/" in name or "\\" in name:
        raise HTTPException(400, "画像名不能包含 / 或 \\ 字符，请改掉后重试")
    if name.startswith((".", "_")):
        raise HTTPException(400, "画像名不能以 . 或 _ 开头，请换个开头")
    pd = PROFILES_DIR / name
    if pd.exists():
        raise HTTPException(409, f"画像「{name}」已存在，请换一个名字")
    _write_baseline_profile(name, req.form or {})
    instruction = _form_to_instruction(name, req.form or {})
    msg = (
        f"请执行 /skill-profile-builder 完善已存在的画像「{name}」。"
        f"/ 的基线六维文件。请：①尽力抓取用户给的社媒链接分析已发内容/风格/受众"
        f"（抓不到就降级，标注[待补充]，勿臆造）②据分析结果润色/补全各维度文件 "
        f"③给出一句话完成度摘要。表单信息如下：\n\n{instruction}"
    )

    _write_profile_status(name, "running", "AI 正在分析并增强画像…")

    def _enhance() -> None:
        try:
            if _enhance_runtime is None:
                raise RuntimeError("agent 运行时未接线（组装层未调用 set_enhance_runtime）")
            log = _enhance_runtime(f"enhance:{name}", msg)
            _write_profile_status(name, "done", log)
        except Exception as e:  # noqa: BLE001
            _write_profile_status(name, "failed", f"AI 增强失败（基线画像已可用）：{e}")

    threading.Thread(target=_enhance, daemon=True).start()
    # 基线已写、画像立即可用；增强在后台，前端轮询状态
    return {"created": pd.is_dir(), "name": name, "async": True, "status": "running"}


def _profile_status_file(name: str) -> Path:
    return PROFILE_BUILD_DIR / f"{name}.json"


def _write_profile_status(name: str, state: str, log: str = "") -> None:
    """原子写画像增强状态。"""
    try:
        PROFILE_BUILD_DIR.mkdir(parents=True, exist_ok=True)
        f = _profile_status_file(name)
        tmp = f.with_suffix(".tmp")
        tmp.write_text(
            json.dumps({"state": state, "log": log, "ts": int(time.time())}, ensure_ascii=False),
            encoding="utf-8",
        )
        # Windows：前端/测试高频轮询读该文件时 os.replace 偶发 PermissionError（共享读句柄
        # 冲突），短暂重试避免状态卡在上一帧（并发测试暴露的真实竞态）。
        for _ in range(5):
            try:
                os.replace(tmp, f)
                break
            except OSError:
                time.sleep(0.01)
    except Exception:
        pass


@router.get("/api/profile/build/status/{name}")
async def api_profile_build_status(name: str):
    """查画像增强进度：running / done / failed / unknown。"""
    f = _profile_status_file(name)
    if f.is_file():
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            return {"state": d.get("state", "unknown"), "log": d.get("log", "")}
        except Exception:
            pass
    return {"state": "unknown", "log": ""}


def _form_to_instruction(name: str, form: dict) -> str:
    def g(k: str, default: str = "（未填）") -> str:
        v = form.get(k)
        if isinstance(v, list):
            return "、".join(str(x) for x in v) if v else default
        return str(v).strip() if v not in (None, "") else default

    links = form.get("links") or {}
    links_txt = "\n".join(f"  - {p}: {u}" for p, u in links.items() if u) or "  （未提供）"
    return (
        f"画像名：{name}\n运营平台：{g('platforms')}\n起号状态：{g('accountStage')}"
        f"\n社媒主页链接：\n{links_txt}\n想做的方向：{g('direction')}"
        f"\n为什么做/我的优势：{g('reason')}\n运营目标：{g('goal')}"
        f"\n想产出的形式：{g('formats')}\n喜欢看的内容/对标账号：{g('likes')}"
        f"\n期望调性：{g('tone')}\n不做的内容/红线：{g('avoid')}\n"
    )


def _write_baseline_profile(name: str, form: dict) -> None:
    """从表单确定性生成六维基线文件。链接派生字段标 [待 AI 分析]。"""
    pd = PROFILES_DIR / name
    pd.mkdir(parents=True, exist_ok=True)

    def g(k: str, default: str = "") -> str:
        v = form.get(k)
        if isinstance(v, list):
            return "、".join(str(x) for x in v)
        return str(v).strip() if v not in (None, "") else default

    direction = g("direction") or "[待补充]"
    reason = g("reason") or "[待补充]"
    goal = g("goal")
    formats = g("formats")
    tone = g("tone") or "[待分析]"
    likes = g("likes")
    avoid = g("avoid")
    platforms = form.get("platforms") or []
    links = form.get("links") or {}
    (pd / "identity.md").write_text(
        f"# 身份定位\n\n## 我是谁\n\n{direction}\n\n"
        f"## 差异化\n\n{reason}\n\n## 内容方向\n\n{direction}"
        f"{'（形式：' + formats + '）' if formats else ''}\n"
        f"{'运营目标：' + goal if goal else ''}\n",
        encoding="utf-8",
    )
    (pd / "style.md").write_text(
        f"# 内容风格\n\n## 语气\n\n{tone}\n\n## 开头结构\n\n[待 AI 分析已发内容]\n\n"
        f"## 视觉风格\n\n[待 AI 分析]\n\n## 内容节奏\n\n{formats or '[待补充]'}\n\n"
        f"## 标志性元素\n\n[待 AI 分析]\n",
        encoding="utf-8",
    )
    (pd / "audience.md").write_text(
        "# 目标受众\n\n## 核心人群\n\n[待 AI 分析/待补充]\n\n## 兴趣标签\n\n[待补充]\n\n"
        "# 痛点\n\n[待补充]\n\n## 互动特征\n\n[待 AI 分析已发内容]\n",
        encoding="utf-8",
    )
    plat_lines = []
    for p in platforms:
        url = links.get(p, "")
        plat_lines.append(f"## {p}\n\n主页：{url or '[待补充]'}\n粉丝量级 / 内容形式：[待补充]\n")
    (pd / "platforms.md").write_text(
        "# 平台运营\n\n" + ("\n".join(plat_lines) if plat_lines else "[待补充]\n"),
        encoding="utf-8",
    )
    (pd / "preferences.md").write_text(
        f"# 偏好与红线\n\n## 要做的\n\n{direction}\n\n## 不做的\n\n"
        f"{avoid or '[待补充]'}\n\n## 合规底线\n\n{avoid or '[待补充]'}\n",
        encoding="utf-8",
    )
    (pd / "memory.md").write_text(
        f"# 经验沉淀\n\n## 内容洞察\n\n"
        f"{'喜欢的内容/对标：' + likes if likes else '[待 AI 分析已收藏/点赞]'}\n\n"
        f"## 踩过的坑\n\n[待积累]\n",
        encoding="utf-8",
    )
