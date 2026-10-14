"""平台发布（platforms，异步发布 + 短信墙 + HITL 读回）。"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..core import pg
from ..core.paths import (
    IMAGE_EXTS,
    OUTPUTS_DIR,
    PROJECT_ROOT,
    PUBLISH_DIR,
    SHARED_SCRIPTS,
    VIDEO_EXTS,
    _safe_output_path,
)
from ..core.settings import _proxy_env
from .analytics import MEDIA_REQUIRED, VIDEO_ONLY_PUBLISH
from .common import LOGIN_RUNNERS
from .login import SmsCodeRequest
from .wechat import WECHAT_SKILL_SCRIPTS, _mp_login_status

router = APIRouter()


def _publish_env() -> dict[str, str]:
    """发布子进程 env：在 _proxy_env 基础上禁用脚本侧日历自动记录——
    发布页由 web 自己回流 _schedule.json，脚本再记一次会重复。对话页 Agent 直跑
    脚本时不经过这里，flag 未设 → 脚本自动记录（见 calendar_ops.record_publish）。"""
    env = _proxy_env()
    env["EASEL_CALENDAR_AUTORECORD"] = "0"
    return env


class PublishRequest(BaseModel):
    title: str = ""
    body: str = ""
    media: list[str] = []
    tags: str = ""


def _write_publish_status(status_file: Path, state: str, message: str = "") -> None:
    """写异步发布状态（与 login_state 同格式），原子写。"""
    try:
        status_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = status_file.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(
                {"state": state, "message": message, "ts": int(time.time())},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        os.replace(tmp, status_file)
    except Exception:
        pass


def _read_publish_status(platform: str) -> dict:
    st = PUBLISH_DIR / f"{platform}.json"
    if st.is_file():
        try:
            d = json.loads(st.read_text(encoding="utf-8"))
            return {"state": d.get("state", "unknown"), "message": d.get("message", "")}
        except Exception:
            pass
    return {"state": "unknown", "message": ""}


def _run_publish_bg(
    platform: str,
    cmd: list,
    title: str,
    body: str,
    cfg: dict,
    status_file: Path,
    code_file: Path,
) -> None:
    """后台线程跑发布脚本（脚本自身把 starting/sms_required/verifying/
    success/error 写进 status_file）。结束后兜底补写终态 + 记 _publish.log
    + 成功则回流排期。"""
    ok = False
    out = err = ""
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            env=_publish_env(),
            capture_output=True,
            text=True,
            timeout=900,
        )
        ok = proc.returncode == 0
        out, err = proc.stdout or "", proc.stderr or ""
    except subprocess.TimeoutExpired:
        err = "发布超时（>900s）"
    except Exception as e:  # noqa: BLE001
        err = f"发布进程异常：{e}"
    try:
        with (OUTPUTS_DIR / "_publish.log").open("a", encoding="utf-8") as lf:
            lf.write(
                f"\n===== {time.strftime('%Y-%m-%d %H:%M:%S')} {platform}(async) ok={ok} =====\n"
            )
            lf.write(
                "CMD: "
                + " ".join(cmd)
                + "\nSTDOUT:\n"
                + out[-2000:]
                + "\nSTDERR:\n"
                + err[-2000:]
                + "\n"
            )
    except Exception:
        pass
    # 脚本正常会写终态；异常/超时没写到时兜底补一个
    if _read_publish_status(platform)["state"] not in ("success", "error"):
        _write_publish_status(
            status_file,
            "success" if ok else "error",
            "发布成功" if ok else ("\n".join((err or out).strip().splitlines()[-4:]) or "发布失败"),
        )
    try:
        code_file.unlink()
    except OSError:
        pass
    if ok:
        try:
            items = pg.schedule_list()
            items.append(
                {
                    "id": uuid.uuid4().hex[:12],
                    "title": title,
                    "date": time.strftime("%Y-%m-%d"),
                    "platform": cfg["name"],
                    "time": time.strftime("%H:%M"),
                    "status": "published",
                    "note": body[:200],
                    "kind": "content",
                    "source": "publish-page",
                }
            )
            pg.schedule_replace_all(items)
        except Exception:
            pass


def _start_async_publish(
    platform: str,
    cmd: list,
    title: str,
    body: str,
    cfg: dict,
    status_file: Path,
    code_file: Path,
) -> dict:
    """启动异步发布：清旧码/状态 → 起后台线程 → 立即返回。前端轮询 /api/publish/{p}/status，
    遇 sms_required 弹输入框、提交到 /api/publish/{p}/sms。"""
    try:
        code_file.unlink()
    except OSError:
        pass
    _write_publish_status(status_file, "starting", "发布中…（若触发风控会要求短信验证）")
    threading.Thread(
        target=_run_publish_bg,
        args=(platform, cmd, title, body, cfg, status_file, code_file),
        daemon=True,
    ).start()
    # 关键：**不返回 ok:true**——这只是「已启动」的应答，真正结果要靠轮询 /status。
    # 若这里给 ok:true，旧前端会把它当「已发布」立刻显示成功（假成功 bug，真机踩过）。
    return {"async": True, "pending": True, "message": "发布已启动，请稍候…"}


@router.get("/api/publish/{platform}/status")
async def api_publish_status(platform: str):
    """轮询异步发布状态：starting/sms_required/verifying/success/error。"""
    if platform not in LOGIN_RUNNERS:
        raise HTTPException(404, "未知平台")
    return {"mode": "publish", **_read_publish_status(platform)}


@router.post("/api/publish/{platform}/sms")
async def api_publish_sms(platform: str, req: SmsCodeRequest):
    """发布触发短信墙时回填验证码（写发布 runner 轮询的一次性验证码文件）。"""
    if platform not in LOGIN_RUNNERS:
        raise HTTPException(404, "未知平台")
    code = "".join(ch for ch in (req.code or "") if ch.isdigit())
    if not (4 <= len(code) <= 8):
        raise HTTPException(400, "验证码应为 4-8 位数字")
    PUBLISH_DIR.mkdir(parents=True, exist_ok=True)
    (PUBLISH_DIR / f"{platform}.code").write_text(code, encoding="utf-8")
    return {"ok": True}


@router.post("/api/publish/{platform}")
async def api_publish(platform: str, req: PublishRequest):
    """一键发布：分发到对应 publisher 脚本真发（--exec）。二次确认在前端。"""
    cfg = LOGIN_RUNNERS.get(platform)
    if not cfg:
        raise HTTPException(404, "未知平台")
    backend = cfg["backend"]
    if backend == "unsupported":
        raise HTTPException(400, f"{cfg['name']} 暂不支持一键发布")
    if not req.title.strip() and not req.body.strip():
        raise HTTPException(400, "标题/正文不能为空")
    imgs, vids = [], []
    for rel in req.media or []:
        full = _safe_output_path(rel)
        ext = full.suffix.lower()
        if ext in VIDEO_EXTS:
            vids.append(str(full))
        elif ext in IMAGE_EXTS:
            imgs.append(str(full))
    if platform in MEDIA_REQUIRED and not imgs and not vids:
        raise HTTPException(400, f"{cfg['name']} 需附带图片或视频")
    if imgs and vids:
        raise HTTPException(400, "同一条内容不能同时发图片和视频，请二选一")
    if platform in VIDEO_ONLY_PUBLISH and not vids:
        raise HTTPException(400, f"{cfg['name']} 只能发视频，请附带一个视频文件")
    title = req.title.strip() or req.body.strip()[:20]
    tags = req.tags or ""
    py = sys.executable
    if platform == "xiaohongshu":
        base = [py, str(SHARED_SCRIPTS / "xhs_publish.py")]
        cmd = (
            base + ["publish-video", "--no-proxy", "--video", vids[0]]
            if vids
            else base + ["publish", "--no-proxy", "--images", ",".join(imgs)]
        )
        cmd += ["--title", title, "--content", req.body, "--tags", tags, "--exec"]
    elif platform == "bilibili":
        # B站投稿：直接调 biliup CLI（需 cookies.json，PATH 上有 biliup）。必须视频；
        # tid=36「知识」；B站投稿必须≥1 标签，无则兜底「日常」。
        bili_tag = tags.replace("#", "").replace("，", ",").strip().strip(",") or "日常"
        cmd = [
            "biliup",
            "-u",
            str(PROJECT_ROOT / "cookies.json"),
            "upload",
            vids[0],
            "--title",
            title[:80],
            "--tid",
            "36",
            "--copyright",
            "1",
            "--tag",
            bili_tag,
        ]
        if req.body.strip():
            cmd += ["--desc", req.body[:2000]]
    elif platform == "douyin":
        base = [py, str(SHARED_SCRIPTS / "douyin_publish.py")]
        cmd = (
            base + ["publish-video", "--no-proxy", "--video", vids[0]]
            if vids
            else base + ["publish", "--no-proxy", "--images", ",".join(imgs)]
        )
        cmd += ["--title", title, "--content", req.body, "--tags", tags, "--exec"]
        # 抖音发布可能触发风控短信墙——异步跑 + 状态/验证码文件，前端轮询到 sms_required 时弹输入框
        PUBLISH_DIR.mkdir(parents=True, exist_ok=True)
        status_file = PUBLISH_DIR / "douyin.json"
        code_file = PUBLISH_DIR / "douyin.code"
        cmd += ["--status-file", str(status_file), "--sms-code-file", str(code_file)]
        return _start_async_publish(platform, cmd, title, req.body, cfg, status_file, code_file)
    elif platform == "wechat-oa":
        # 微信公众号：走「后台会话」发布（免 AppID/AppSecret、免 IP 白名单）。
        # 正文 MD → 公众号 HTML（skill 排版器）→ 会话建草稿
        # （weixin_mp_stats.py publish，内嵌图传 mp CDN）。
        if _mp_login_status().get("state") != "success":
            raise HTTPException(400, "公众号后台未登录：请先在账号页点「登录公众号后台」扫码")
        if not imgs:
            raise HTTPException(400, "公众号文章需要一张封面图，请附带至少一张图片")
        if vids:
            raise HTTPException(400, "公众号发图文文章，请附带封面/正文图片而非视频")
        cover = imgs[0]
        PUBLISH_DIR.mkdir(parents=True, exist_ok=True)
        stamp = uuid.uuid4().hex[:12]
        md_path = PUBLISH_DIR / f"wechat-oa-{stamp}.md"
        html_path = PUBLISH_DIR / f"wechat-oa-{stamp}.html"
        body_md = req.body or ""
        extra_imgs = imgs[1:]
        if extra_imgs:
            body_md += "\n\n" + "\n\n".join(f"![]({p})" for p in extra_imgs)
        md_path.write_text(f"# {title}\n\n{body_md}\n", encoding="utf-8")
        conv = subprocess.run(
            [
                py,
                str(WECHAT_SKILL_SCRIPTS / "html_converter.py"),
                str(md_path),
                "-o",
                str(html_path),
            ],
            cwd=str(PROJECT_ROOT),
            env=_proxy_env(),
            capture_output=True,
            text=True,
            timeout=60,
        )
        if conv.returncode != 0 or not html_path.is_file():
            raise HTTPException(500, f"排版失败：{(conv.stderr or conv.stdout or '')[-200:]}")
        wx_proxy = os.environ.get("EASEL_PROXY") or os.environ.get("https_proxy") or ""
        cmd = [
            py,
            str(SHARED_SCRIPTS / "weixin_mp_stats.py"),
            "publish",
            "--proxy",
            wx_proxy,
            "--html",
            str(html_path),
            "--cover",
            cover,
            "--title",
            title,
            "--digest",
            (req.body or "").strip()[:100],
            "--author",
            "",
        ]
    else:
        cmd = [
            py,
            str(SHARED_SCRIPTS / "web_publisher.py"),
            "publish",
            "--platform",
            cfg["wp"],
            "--title",
            title,
            "--desc",
            req.body,
            "--tags",
            tags,
            "--exec",
        ]
        media = vids[0] if vids else (imgs[0] if imgs else None)
        if media:
            cmd += ["--media", media]
    # 公众号走后台会话（Playwright，脚本自带 --proxy，默认直连）；其余平台走 _publish_env
    pub_env = _proxy_env() if platform == "wechat-oa" else _publish_env()
    try:
        proc = await asyncio.to_thread(
            subprocess.run,
            cmd,
            cwd=str(PROJECT_ROOT),
            env=pub_env,
            capture_output=True,
            text=True,
            timeout=600,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "发布超时（媒体处理慢或流程卡住）") from None
    ok = proc.returncode == 0
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()
    detail = "\n".join(tail[-8:])
    try:
        with (OUTPUTS_DIR / "_publish.log").open("a", encoding="utf-8") as lf:
            lf.write(
                f"\n===== {time.strftime('%Y-%m-%d %H:%M:%S')} {platform} "
                f"rc={proc.returncode} ok={ok} =====\n"
            )
            lf.write("CMD: " + " ".join(cmd) + "\n")
            lf.write("STDOUT:\n" + (proc.stdout or "")[-2000:] + "\n")
            lf.write("STDERR:\n" + (proc.stderr or "")[-2000:] + "\n")
    except Exception:
        pass
    if ok:
        try:
            items = pg.schedule_list()
            items.append(
                {
                    "id": uuid.uuid4().hex[:12],
                    "title": title,
                    "date": time.strftime("%Y-%m-%d"),
                    "platform": cfg["name"],
                    "time": time.strftime("%H:%M"),
                    "status": "published",
                    "note": req.body[:200],
                    "kind": "content",
                    "source": "publish-page",
                }
            )
            pg.schedule_replace_all(items)
        except Exception:
            pass
    return {
        "ok": ok,
        "message": "发布成功" if ok else "发布失败（见 detail）",
        "detail": detail,
    }
