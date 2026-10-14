"""微信公众号（wechat-oa）凭证式接入（platforms）。

凭证存 skill 配置（Fernet 加密由 seal 侧负责，此处只读写配置）。
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..core.paths import LOGIN_DIR, PROJECT_ROOT, SHARED_SCRIPTS
from ..core.settings import _proxy_env
from .common import _WHOAMI_CACHE, _WHOAMI_LOCK, LOGIN_PROCESSES, LOGIN_RUNNERS

router = APIRouter()

WECHAT_SKILL_DIR = PROJECT_ROOT / "skills" / "builtin" / "skill-wechat-publisher"
WECHAT_SKILL_SCRIPTS = WECHAT_SKILL_DIR / "scripts"
WECHAT_PUBLISH_SCRIPT = WECHAT_SKILL_SCRIPTS / "publish.py"
WECHAT_CONFIG_YAML = WECHAT_SKILL_DIR / "wechat-publisher.yaml"
WECHAT_WEB_ACCOUNT = "web"  # web 端配置写入/读取的账号 key


def _wechat_load_yaml() -> dict:
    """读 wechat-publisher.yaml（不存在或损坏则返回空 dict）。"""
    if not WECHAT_CONFIG_YAML.is_file():
        return {}
    try:
        import yaml

        data = yaml.safe_load(WECHAT_CONFIG_YAML.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _wechat_web_account() -> dict:
    """返回 web 端配置的公众号账号（accounts.web），无则空 dict。"""
    cfg = _wechat_load_yaml()
    raw = cfg.get("accounts") if cfg else None
    accts = raw if isinstance(raw, dict) else {}
    acc = accts.get(WECHAT_WEB_ACCOUNT)
    return acc if isinstance(acc, dict) else {}


def _wechat_has_credentials() -> bool:
    acc = _wechat_web_account()
    return bool(acc.get("app_id") and acc.get("app_secret"))


def _wechat_save_credentials(
    app_id: str, app_secret: str, name: str = "", author: str = ""
) -> None:
    """把 AppID/AppSecret 写入 wechat-publisher.yaml 的 accounts.web（原子写，保留其它账号）。"""
    import yaml

    cfg = _wechat_load_yaml()
    if not isinstance(cfg.get("accounts"), dict):
        cfg["accounts"] = {}
    acc = cfg["accounts"].get(WECHAT_WEB_ACCOUNT)
    if not isinstance(acc, dict):
        acc = {}
    acc["name"] = name or acc.get("name") or "微信公众号"
    acc["app_id"] = app_id
    acc["app_secret"] = app_secret
    if author:
        acc["author"] = author
    acc.setdefault("author", "")
    cfg["accounts"][WECHAT_WEB_ACCOUNT] = acc
    # web 账号存在即设为默认，方便 CLI 直接用
    cfg.setdefault("default", WECHAT_WEB_ACCOUNT)
    WECHAT_CONFIG_YAML.parent.mkdir(parents=True, exist_ok=True)
    tmp = WECHAT_CONFIG_YAML.with_suffix(".yaml.tmp")
    tmp.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")
    os.replace(tmp, WECHAT_CONFIG_YAML)


def _wechat_clear_credentials() -> None:
    """删除 accounts.web 及其 token 缓存。"""
    import yaml

    cfg = _wechat_load_yaml()
    accts = cfg.get("accounts")
    if isinstance(accts, dict) and WECHAT_WEB_ACCOUNT in accts:
        accts.pop(WECHAT_WEB_ACCOUNT, None)
        if cfg.get("default") == WECHAT_WEB_ACCOUNT:
            cfg["default"] = next(iter(accts), "") if accts else ""
        try:
            tmp = WECHAT_CONFIG_YAML.with_suffix(".yaml.tmp")
            tmp.write_text(
                yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            os.replace(tmp, WECHAT_CONFIG_YAML)
        except Exception:
            pass
    for cache in (
        WECHAT_SKILL_SCRIPTS / f".token_cache_{WECHAT_WEB_ACCOUNT}.json",
        WECHAT_SKILL_SCRIPTS / ".token_cache.json",
    ):
        try:
            cache.unlink()
        except OSError:
            pass


def _wechat_env() -> dict[str, str]:
    """公众号 API 子进程 env，决定微信 API 从哪个 IP 出网（公众号白名单要求固定出口 IP）。

    两种模式：
    - 设了 WECHAT_EGRESS_PROXY（如反向隧道到你本机/固定 IP 中转）→ 让微信 API **走这个代理**出网，
      微信看到的是该代理的公网 IP，白名单加它即可。其它外网仍走公司代理。
    - 未设 → 微信 API 走**直连**（api.weixin.qq.com 进 no_proxy）。注意本机直连出口也是共享 NAT
      轮询池（见 WECHAT_OA_INTEGRATION.md §4），直连仅在出口 IP 恰好固定的机器上可靠。
    """
    from .publish import _publish_env  # 局部导入避免与 publish→wechat 顶层循环

    env = _publish_env()
    wx_hosts = ("api.weixin.qq.com", "mp.weixin.qq.com")
    egress = os.environ.get("WECHAT_EGRESS_PROXY", "").strip()
    if egress:
        # 微信 API 走指定固定出口代理；从 no_proxy 里去掉微信域名，确保不被旁路成直连。
        env["http_proxy"] = env["https_proxy"] = egress
        env["HTTP_PROXY"] = env["HTTPS_PROXY"] = egress
        kept = [
            h for h in env.get("no_proxy", "").split(",") if h and not any(w in h for w in wx_hosts)
        ]
        env["no_proxy"] = ",".join(kept)
        env["NO_PROXY"] = env["no_proxy"]
    else:
        existing = env.get("no_proxy", "")
        env["no_proxy"] = (existing + "," + ",".join(wx_hosts)) if existing else ",".join(wx_hosts)
        env["NO_PROXY"] = env["no_proxy"]
    return env


def _wechat_verify_token() -> tuple[bool, str]:
    """用当前 accounts.web 凭证调官方 token 接口验证。返回 (ok, message)。
    在子进程里跑，避免把 skill 的 import 副作用带进 web 进程。"""
    code = (  # noqa: UP031 —— 构造子进程源码含 %r，%s/%r 占位改 f-string 需转义花括号，得不偿失
        "import sys; sys.path.insert(0, %r)\n"
        "from config import set_account\n"
        "from wechat_token import get_access_token\n"
        "set_account(%r)\n"
        "try:\n"
        "    t = get_access_token(force_refresh=True)\n"
        "    print('OK' if t else 'EMPTY')\n"
        "except Exception as e:\n"
        "    print('ERR:' + str(e))\n"
    ) % (str(WECHAT_SKILL_SCRIPTS), WECHAT_WEB_ACCOUNT)  # noqa: UP031 —— 构造子进程源码含 %r，改 f-string 需转义全部花括号，得不偿失
    try:
        proc = subprocess.run(
            [sys.executable, "-c", code],
            cwd=str(WECHAT_SKILL_SCRIPTS),
            env=_wechat_env(),
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return False, "验证超时（网络或 IP 白名单问题）"
    out = (proc.stdout or "").strip().splitlines()
    last = out[-1] if out else ""
    if last == "OK":
        return True, ""
    if last.startswith("ERR:"):
        return False, last[4:].strip()[:200]
    err = (proc.stderr or "").strip().splitlines()[-1:] or ["验证失败"]
    return False, err[0][:200]


class WechatCredentials(BaseModel):
    appId: str = ""
    appSecret: str = ""
    name: str = ""
    author: str = ""


@router.get("/api/accounts/{platform}/credentials")
async def api_get_credentials(platform: str):
    """读取凭证式平台（目前仅公众号）的已配置状态（AppID 脱敏，AppSecret 不回传）。"""
    cfg = LOGIN_RUNNERS.get(platform)
    if not cfg or cfg.get("backend") != "wechat-oa":
        raise HTTPException(404, "该平台不使用凭证登录")
    acc = _wechat_web_account()
    app_id = acc.get("app_id", "") or ""
    return {
        "configured": bool(app_id and acc.get("app_secret")),
        "appIdMasked": (app_id[:6] + "***" + app_id[-4:])
        if len(app_id) > 10
        else ("***" if app_id else ""),
        "name": acc.get("name", "") or "",
        "author": acc.get("author", "") or "",
    }


@router.post("/api/accounts/{platform}/credentials")
async def api_save_credentials(platform: str, req: WechatCredentials):
    """保存凭证式平台（公众号）的 AppID/AppSecret，写入 skill 配置并调官方接口验证。"""
    cfg = LOGIN_RUNNERS.get(platform)
    if not cfg or cfg.get("backend") != "wechat-oa":
        raise HTTPException(404, "该平台不使用凭证登录")
    app_id = (req.appId or "").strip()
    app_secret = (req.appSecret or "").strip()
    if not app_id or not app_secret:
        raise HTTPException(400, "AppID 和 AppSecret 都不能为空")
    _wechat_save_credentials(app_id, app_secret, name=req.name.strip(), author=req.author.strip())
    ok, msg = _wechat_verify_token()
    with _WHOAMI_LOCK:
        _WHOAMI_CACHE.pop(platform, None)
    if ok:
        from .login import _write_login_marker  # 局部导入避免 login↔wechat 循环

        _write_login_marker(platform, "success", req.name.strip() or "微信公众号")
        return {"ok": True, "message": "公众号凭证已保存并验证通过"}
    # 校验失败：凭证已存（下次改正后可直接重试），
    # 但明确告知失败原因（常见 40164 IP 白名单 / 40125 密钥错误）
    return {"ok": False, "message": f"凭证已保存但验证未通过：{msg}。"}


def _mp_login_status() -> dict:
    """读公众号后台(mp)登录状态 + 二维码（文件由 weixin_mp_stats.py login 写）。"""
    st = LOGIN_DIR / "wechat-oa-mp.json"
    data: dict[str, Any] = {"state": "unknown", "message": ""}
    if st.is_file():
        try:
            d = json.loads(st.read_text(encoding="utf-8"))
            data = {"state": d.get("state", "unknown"), "message": d.get("message", "")}
        except Exception:
            pass
    proc = LOGIN_PROCESSES.get("wechat-oa-mp")
    if data["state"] in ("unknown", "starting") and proc is not None and proc.poll() is not None:
        data = {
            "state": "error",
            "message": f"登录程序退出（码 {proc.poll()}），见 outputs/_login/wechat-oa-mp.log",
        }
    qr = LOGIN_DIR / "wechat-oa-mp.png"
    if qr.is_file():
        data["qr"] = "_login/wechat-oa-mp.png"
        try:
            data["qrTs"] = int(qr.stat().st_mtime)
        except OSError:
            data["qrTs"] = 0
    else:
        data["qr"] = ""
        data["qrTs"] = 0
    return data


def _stop_mp_login_on_shutdown() -> None:
    """正常重启 Web 时回收扫码进程，避免它继续写入下一次登录的状态。"""
    proc = LOGIN_PROCESSES.pop("wechat-oa-mp", None)
    if proc is not None and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
        from .login import _write_login_marker  # 局部导入避免 login↔wechat 循环

        _write_login_marker("wechat-oa-mp", "expired", "服务已重启，请重新扫码登录")


@router.post("/api/accounts/{platform}/mp-login")
async def api_mp_login_start(platform: str):
    """启动「公众号后台」扫码登录（数据中心取数用，管理员级会话，独立于 AppID 凭证）。
    默认直连起 Playwright 出二维码；受限网络可设 EASEL_PROXY / https_proxy 走正向代理。"""
    cfg = LOGIN_RUNNERS.get(platform)
    if not cfg or cfg.get("backend") != "wechat-oa":
        raise HTTPException(404, "该平台不使用公众号后台登录")
    # 重复点击复用正在进行的登录，不能删除其二维码或启动第二个 Chromium。
    proc = LOGIN_PROCESSES.get("wechat-oa-mp")
    if proc is not None and proc.poll() is None:
        return {"mode": "qr", **_mp_login_status()}
    LOGIN_DIR.mkdir(parents=True, exist_ok=True)
    for f in (LOGIN_DIR / "wechat-oa-mp.png", LOGIN_DIR / "wechat-oa-mp.json"):
        try:
            f.unlink()
        except OSError:
            pass
    wx_proxy = os.environ.get("EASEL_PROXY") or os.environ.get("https_proxy") or ""
    cmd = [
        sys.executable,
        str(SHARED_SCRIPTS / "weixin_mp_stats.py"),
        "login",
        "--proxy",
        wx_proxy,
        "--qr-out",
        str(LOGIN_DIR / "wechat-oa-mp.png"),
        "--status-file",
        str(LOGIN_DIR / "wechat-oa-mp.json"),
        "--timeout",
        "240",
    ]
    log_file = (LOGIN_DIR / "wechat-oa-mp.log").open("a", encoding="utf-8")
    proc = subprocess.Popen(
        cmd,
        cwd=str(PROJECT_ROOT),
        env=_proxy_env(),
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )
    log_file.close()
    LOGIN_PROCESSES["wechat-oa-mp"] = proc
    for _ in range(60):
        await asyncio.sleep(0.5)
        s = _mp_login_status()
        if s["qr"] or s["state"] in ("qr_ready", "success", "error", "expired"):
            return {"mode": "qr", **s}
    return {"mode": "qr", **_mp_login_status()}


@router.get("/api/accounts/{platform}/mp-login/status")
async def api_mp_login_status(platform: str):
    cfg = LOGIN_RUNNERS.get(platform)
    if not cfg or cfg.get("backend") != "wechat-oa":
        raise HTTPException(404, "该平台不使用公众号后台登录")
    return {"mode": "qr", **_mp_login_status()}
