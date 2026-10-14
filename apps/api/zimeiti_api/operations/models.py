"""模型设置面板（operations）：渠道展示/拉取/自测。"""

from __future__ import annotations

import asyncio
import json
import time
import urllib.request

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..core.paths import ENV_FILE
from ..core.settings import (
    _SLOT_ENV_KEYS,
    _guard_env_values,
    _is_set,
    _read_env,
    _ssrf_safe,
    _valid_base_url,
)

router = APIRouter()

# ═══════════════════════════════════════════════════════════════════════
# 设置面板 · 模型配置（按真实 .env 只读展示 + 真自测；openclaw.json 已移除）
# ═══════════════════════════════════════════════════════════════════════


def _mask_key(v: str) -> str:
    v = (v or "").strip()
    if not v:
        return ""
    return f"«{v[:5]}…{v[-4:]}»" if len(v) > 14 else "«已配置»"


def _model_channels() -> dict:
    env = _read_env()
    om_env = (env.get("OPENAI_MODEL") or "").strip()
    primary = f"openai/{om_env}" if om_env else ""

    chat_rows = []
    ob = (env.get("OPENAI_BASE_URL") or "").strip()
    om = (env.get("OPENAI_MODEL") or "").strip()
    ok_key = bool((env.get("OPENAI_API_KEY") or "").strip())
    if ob or ok_key:
        chat_rows.append(
            {
                "slot": "openai",
                "order": 1,
                "name": "deepseek",
                "sub": "官方直连",
                "type": "openai",
                "model": om or "deepseek-chat",
                "baseUrl": ob,
                "keyMasked": _mask_key(env.get("OPENAI_API_KEY", "")),
                "role": "主" if primary.startswith("openai/") else "备",
                "result": "已配置" if ok_key else "缺 key",
            }
        )
    ab = (env.get("ANTHROPIC_BASE_URL") or "").strip()
    ak = (env.get("ANTHROPIC_API_KEY") or "").strip()
    if ab or ak:
        chat_rows.append(
            {
                "slot": "anthropic",
                "order": len(chat_rows) + 1,
                "name": "anthropic",
                "sub": "官方直连",
                "type": "anthropic",
                "model": (env.get("CLAUDE_MODEL") or "claude-sonnet-4-6").strip(),
                "baseUrl": ab or "官方",
                "keyMasked": _mask_key(ak),
                "role": "备",
                "result": "已配置" if ak else "缺 key",
            }
        )
    lb = (env.get("EASEL_LLM_BASE_URL") or "").strip()
    lk = (env.get("EASEL_LLM_API_KEY") or "").strip()
    if lb or lk:
        chat_rows.append(
            {
                "slot": "relay",
                "order": len(chat_rows) + 1,
                "name": "relay",
                "sub": "中转站",
                "type": "openai",
                "model": (env.get("CLAUDE_MODEL") or "deepseek-chat").strip(),
                "baseUrl": lb or "（未配置）",
                "keyMasked": _mask_key(lk),
                "role": "备",
                "result": "已配置" if lk else "缺 key",
            }
        )

    sf = bool((env.get("SILICONFLOW_API_KEY") or "").strip())
    trans_rows = [
        {
            "order": 0,
            "name": "自带字幕",
            "sub": "视频自带 SRT/VTT 时直接读",
            "type": "脚本层",
            "model": "—",
            "baseUrl": "—",
            "keyMasked": "—",
            "role": "免配",
            "result": "优先",
        },
        {
            "slot": "siliconflow",
            "order": 1,
            "name": "siliconflow",
            "sub": "硅基流动",
            "type": "openai",
            "model": "SenseVoiceSmall",
            "baseUrl": "https://api.siliconflow.cn/v1",
            "keyMasked": _mask_key(env.get("SILICONFLOW_API_KEY", "")),
            "role": "主",
            "result": "已配置" if sf else "缺 key",
        },
    ]
    channels: dict = {"chat": {"rows": chat_rows}, "transcribe": {"rows": trans_rows}}
    try:
        import model_registry as _mr  # skills/shared/scripts 已在 sys.path 上

        _setting_env = {
            "video": "VIDEO_PROVIDER",
            "music": "MUSIC_PROVIDER",
            "voice": "VOICE_PROVIDER",
        }
        for _gid, _ch in (
            ("image", "image"),
            ("video", "video"),
            ("music", "music"),
            ("voice", "speech"),
        ):
            _spec = _mr.MODEL_GROUPS[_gid]
            _chosen = (env.get(_setting_env.get(_gid, ""), "") or "").strip()
            _rows = []
            for _p in _spec["providers"]:
                _req = [k for k in _p["keys"] if k["required"]]
                _bk = next(
                    (
                        k
                        for k in _p["keys"]
                        if not k["secret"] and ("BASE" in k["env"] or "URL" in k["env"])
                    ),
                    None,
                )
                _mk = next(
                    (k for k in _p["keys"] if not k["secret"] and "MODEL" in k["env"]),
                    None,
                )
                _edit_keys = [k for k in _req if k is not _bk and k is not _mk]
                _k1 = _edit_keys[0] if _edit_keys else None
                _k2 = _edit_keys[1] if len(_edit_keys) > 1 else None
                _ok = all(
                    _is_set(env.get(k["env"]))
                    or any(_is_set(env.get(a)) for a in k.get("aliases", []))
                    for k in _req
                )
                _masked = ""
                if _k1:
                    _raw = env.get(_k1["env"], "")
                    if not _raw:
                        for _a in _k1.get("aliases", []):
                            if env.get(_a):
                                _raw = env[_a]
                                break
                    _masked = _mask_key(_raw)
                _rows.append(
                    {
                        "slot": _p["id"],
                        "order": 0,
                        "name": _p["name"],
                        "sub": _gid,
                        "type": _p["id"],
                        "model": (env.get(_mk["env"]) or "").strip() if _mk else "",
                        "baseUrl": (env.get(_bk["env"]) or "").strip() if _bk else "",
                        "keyMasked": _masked,
                        "role": "主" if (_gid == "image" or _chosen == _p["id"]) else "备",
                        "result": "已配置" if _ok else "未配置",
                        "key2Label": _k2["label"] if _k2 else "",
                        "key2Masked": _mask_key(env.get(_k2["env"], ""))
                        if _k2 and _k2["secret"]
                        else "",
                        "modelEditable": _mk is not None,
                        "baseEditable": _bk is not None,
                        "baseOptional": (_bk is None) or (not _bk["required"]),
                    }
                )
            channels[_ch] = {"rows": _rows}
    except Exception:  # noqa: BLE001
        pass
    return {"channels": channels, "primary": primary}


@router.get("/api/settings/models")
async def api_settings_models():
    """模型通道：chat / transcribe（含可编辑的原值；key 只回脱敏）。"""
    return _model_channels()


def _write_env_direct(updates: dict[str, str]) -> None:
    """后端受控键位专用：就地更新/追加 .env（不做 allowlist 过滤，
    仅服务端固定映射调用）。原子写。"""
    updates = {k: v for k, v in updates.items() if k and v.strip() != ""}
    if not updates:
        return
    _guard_env_values(updates)
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines() if ENV_FILE.is_file() else []
    seen = set()
    out = []
    for line in lines:
        s = line.strip()
        matched = None
        if s and not s.startswith("#") and "=" in s:
            k = s.split("=", 1)[0].strip()
            if k in updates:
                matched = k
        if matched is not None:
            seen.add(matched)
            out.append(f"{matched}={updates[matched]}")
            continue
        out.append(line)
    appended = [f"{k}={v}" for k, v in updates.items() if k not in seen]
    if appended:
        if out and out[-1].strip() != "":
            out.append("")
        out.append("# ---- Easel 模型配置（Web 设置面板写入）----")
        out.extend(appended)
    tmp = ENV_FILE.with_suffix(".env.tmp")
    tmp.write_text("\n".join(out) + "\n", encoding="utf-8")
    tmp.replace(ENV_FILE)


class ModelSaveRow(BaseModel):
    slot: str = ""
    name: str = ""
    model: str = ""
    baseUrl: str = ""
    key: str = ""
    key2: str = ""
    primary: bool = False
    # 自定义供应商的上游协议：openai（默认，/chat/completions）或 anthropic
    # （原生 /v1/messages；中转站卖原生 Claude 格式时选它）。
    protocol: str = ""


class ModelSaveRequest(BaseModel):
    channel: str = "chat"
    rows: list[ModelSaveRow] = Field(default_factory=list)


@router.post("/api/settings/models/save")
async def api_settings_models_save(req: ModelSaveRequest):
    """保存模型通道：.env 就地更新（key 留空=不改）；媒体通道写 provider 配置。"""
    ch0 = (req.channel or "").strip()
    if ch0 in ("speech", "image", "video", "music"):
        import model_registry as _mr2

        _gid0 = {
            "speech": "voice",
            "image": "image",
            "video": "video",
            "music": "music",
        }[ch0]
        _spec0 = _mr2.MODEL_GROUPS[_gid0]
        _by_id = {p["id"]: p for p in _spec0["providers"]}
        _setting0 = {
            "video": "VIDEO_PROVIDER",
            "music": "MUSIC_PROVIDER",
            "voice": "VOICE_PROVIDER",
        }.get(_gid0)
        _mupd: dict[str, str] = {}
        _primary0 = ""
        _env0 = _read_env()
        for _row in req.rows:
            _pid = (_row.slot or "").strip()
            _p0 = _by_id.get(_pid)
            if not _p0:
                raise HTTPException(400, f"不认识的服务商：{_pid or '（空）'}")
            _base0 = (_row.baseUrl or "").strip().rstrip("/")
            _key0 = (_row.key or "").strip()
            _key20 = (_row.key2 or "").strip()
            _model0 = (_row.model or "").strip()
            if _base0 and not _valid_base_url(_base0):
                raise HTTPException(400, f"{_p0['name']} 的根地址需是合法的 http(s):// 地址")
            if (_key0 and any(x.isspace() for x in _key0)) or (
                _key20 and any(x.isspace() for x in _key20)
            ):
                raise HTTPException(400, f"{_p0['name']} 的 Key 不能包含空白字符")
            _bk0 = next(
                (
                    k
                    for k in _p0["keys"]
                    if not k["secret"] and ("BASE" in k["env"] or "URL" in k["env"])
                ),
                None,
            )
            _mk0 = next(
                (k for k in _p0["keys"] if not k["secret"] and "MODEL" in k["env"]),
                None,
            )
            _req0 = [k for k in _p0["keys"] if k["required"] and k is not _bk0 and k is not _mk0]
            # 与对话通道同一条规矩：只改根地址、Key 留空（留空=沿用旧 Key），等于把已存的真 Key
            # 指到新地址去——SILICONFLOW 这类通道还有「连通性自测」会把它当 Bearer 发过去。
            if (
                _base0
                and _bk0
                and not _key0
                and _base0 != (_env0.get(_bk0["env"], "") or "").strip().rstrip("/")
                and _req0
                and (_env0.get(_req0[0]["env"], "") or "").strip()
            ):
                raise HTTPException(400, f"更换{_p0['name']}的根地址时必须重新填写 Key")
            if _key0 and _req0:
                _mupd[_req0[0]["env"]] = _key0
            if _key20 and len(_req0) > 1:
                _mupd[_req0[1]["env"]] = _key20
            if _model0 and _mk0:
                _mupd[_mk0["env"]] = _model0
            if _base0 and _bk0:
                _mupd[_bk0["env"]] = _base0
            if getattr(_row, "primary", False):
                _primary0 = _pid
        if _primary0 and _setting0:
            _mupd[_setting0] = _primary0
        if not _mupd:
            raise HTTPException(400, "没有可保存的改动（key 留空表示不改）")
        _write_env_direct(_mupd)
        _resp0 = {"ok": True, "note": ""}
        _resp0.update(_model_channels())
        return _resp0

    updates: dict[str, str] = {}
    _cur_env = _read_env()
    for row in req.rows:
        slot = (row.slot or "").strip()
        model = (row.model or "").strip()
        base = (row.baseUrl or "").strip().rstrip("/")
        key = (row.key or "").strip()
        if base and not _valid_base_url(base):
            raise HTTPException(400, f"Base URL 需是合法的 http(s):// 地址：{base[:60]}")
        if key and any(ch.isspace() for ch in key):
            raise HTTPException(400, "API Key 不能包含空白字符")
        if len(model) > 120 or len(base) > 300 or len(key) > 400:
            raise HTTPException(400, "字段过长，请检查")
        # 改 Base URL 但把 Key 留空（留空=沿用旧 Key）＝ 把已存的真 Key 指向新地址，
        # 之后一次「连通性自测」就会把它当 Bearer 送到新地址去。换地址必须重填 Key。
        _be, _ke = _SLOT_ENV_KEYS.get(slot, ("", ""))
        if (
            base
            and _be
            and not key
            and base != (_cur_env.get(_be, "") or "").strip().rstrip("/")
            and (_cur_env.get(_ke, "") or "").strip()
        ):
            raise HTTPException(400, f"更换 Base URL 时必须重新填写 API Key（{slot}）")
        if slot == "openai":
            if model:
                updates["OPENAI_MODEL"] = model
            if base:
                updates["OPENAI_BASE_URL"] = base
            if key:
                updates["OPENAI_API_KEY"] = key
        elif slot == "relay":
            if base:
                updates["EASEL_LLM_BASE_URL"] = base
            if model:
                updates["CLAUDE_MODEL"] = model
            if key:
                updates["EASEL_LLM_API_KEY"] = key
        elif slot == "anthropic":
            if model:
                updates["CLAUDE_MODEL"] = model
            if key:
                updates["ANTHROPIC_API_KEY"] = key
            if base:
                updates["ANTHROPIC_BASE_URL"] = base
        elif slot == "siliconflow":
            if base:
                updates["SILICONFLOW_BASE_URL"] = base
            if key:
                updates["SILICONFLOW_API_KEY"] = key
    if not updates:
        raise HTTPException(400, "没有可保存的改动（key 留空表示不改）")
    _write_env_direct(updates)
    resp = {"ok": True, "note": ""}
    resp.update(_model_channels())
    return resp


class SelftestRequest(BaseModel):
    channel: str = "chat"


class ModelsFetchRequest(BaseModel):
    """「拉取模型列表」请求。

    key 优先用前端传来的草稿值（供应商还没落盘时也能拉）；留空则按 slot 从已存配置里取
    —— 用户已经存过 Key，不该为了拉一次列表再贴一遍明文。服务端全程不落盘、不写日志。

    baseUrl 允许留空由 slot 回落，否则「只用已存配置拉列表」这条路径就进不来。
    """

    baseUrl: str = ""
    key: str = ""
    protocol: str = "openai"  # openai | anthropic
    slot: str = ""
    name: str = ""  # 自定义供应商的 provider 名（slot='custom' 时用它查已存凭据）


# slot → (base 键, key 键)；与 _SLOT_ENV_KEYS 同源，外加自定义供应商。
_FETCH_KEY_BY_SLOT = {
    "openai": ("OPENAI_BASE_URL", "OPENAI_API_KEY"),
    "relay": ("EASEL_LLM_BASE_URL", "EASEL_LLM_API_KEY"),
    "anthropic": ("ANTHROPIC_BASE_URL", "ANTHROPIC_API_KEY"),
    "siliconflow": ("SILICONFLOW_BASE_URL", "SILICONFLOW_API_KEY"),
}


@router.post("/api/settings/models/available")
async def api_models_available(req: ModelsFetchRequest):
    """代前端拉一次 GET {base}/models，返回模型 id 列表（自定义供应商不用再手打模型名）。

    与 selftest 同一条安全线：带着用户 Key 出去的请求，目标必须过 _valid_base_url +
    _ssrf_safe；不落盘、不写日志。
    """
    base = (req.baseUrl or "").strip().rstrip("/")
    key = (req.key or "").strip()
    slot = (req.slot or "").strip()
    # 草稿没填 key 时，回落到该槽位已存的值（只在内存里用，不回显、不记日志）。
    if not key and slot:
        _env = _read_env()
        _bk, _kk = _FETCH_KEY_BY_SLOT.get(slot, ("", ""))
        _b, _k = _env.get(_bk, ""), _env.get(_kk, "")
        key = (_k or "").strip()
        if not base and _b:
            base = _b.strip().rstrip("/")
    if not base:
        raise HTTPException(400, "Base URL 不能为空")
    if not _valid_base_url(base):
        raise HTTPException(400, "Base URL 不合法")
    if not _ssrf_safe(base):
        raise HTTPException(400, "目标指向本机/内网地址，已拒绝（避免把 API Key 发给内网服务）")

    anthropic = (req.protocol or "").strip().lower() == "anthropic"
    if anthropic:
        url = base + "/v1/models"
        headers = {
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "Authorization": f"Bearer {key}",
        }
    else:
        url = base + "/models"
        headers = {"Authorization": f"Bearer {key}"}

    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *_a, **_kw):
            return None

    _opener = urllib.request.build_opener(_NoRedirect)

    def _fetch() -> list[str]:
        rq = urllib.request.Request(url, headers=headers)
        with _opener.open(rq, timeout=15) as resp:
            payload = json.loads(resp.read().decode("utf-8", "replace"))
        # OpenAI / Anthropic 形状都是 {"data":[{"id":...}]}；有的网关直接给 ["id",...]。
        if isinstance(payload, dict):
            items = payload.get("data") or payload.get("models") or []
        elif isinstance(payload, list):
            items = payload
        else:
            items = []
        ids = []
        for it in items:
            mid = it.get("id") if isinstance(it, dict) else it
            if isinstance(mid, str) and mid.strip():
                ids.append(mid.strip())
        return sorted(set(ids))

    try:
        models = await asyncio.to_thread(_fetch)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"拉取失败：{type(e).__name__}: {e}"[:180]) from e
    return {"baseUrl": base, "models": models, "fetchedAt": int(time.time())}


@router.post("/api/settings/models/selftest")
async def api_models_selftest(req: SelftestRequest):
    """真自测：对已配置的 OpenAI 兼容通道发 GET {base}/models 并计耗时。"""
    channel = (req.channel or "all").strip()
    env = _read_env()
    # (base, key, 是否为 Anthropic Messages 协议)。协议决定探测用的鉴权头与路径：
    # Anthropic 是 x-api-key + /v1/models，OpenAI 兼容是 Bearer + /models。
    targets: list[tuple[str, str, bool]] = []
    if channel in ("chat", "all"):
        for base, key, is_anthropic in (
            (env.get("ANTHROPIC_BASE_URL", ""), env.get("ANTHROPIC_API_KEY", ""), True),
            (env.get("OPENAI_BASE_URL", ""), env.get("OPENAI_API_KEY", ""), False),
            (
                env.get("EASEL_LLM_BASE_URL", ""),
                env.get("EASEL_LLM_API_KEY", ""),
                False,
            ),
        ):
            if base.strip() and key.strip():
                targets.append((base.strip().rstrip("/"), key.strip(), is_anthropic))
    if channel in ("transcribe", "all") and (env.get("SILICONFLOW_API_KEY") or "").strip():
        targets.append(
            (
                (env.get("SILICONFLOW_BASE_URL") or "https://api.siliconflow.cn/v1")
                .strip()
                .rstrip("/"),
                env["SILICONFLOW_API_KEY"].strip(),
                False,
            )
        )

    # 这里会把真实 API Key 当 Bearer 发出去，所以目标地址必须先过闸：
    # 合法 http(s)、且不指向本机/内网/云元数据；跳转也不跟（跟了等于绕过前面的判断）。
    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *_a, **_kw):
            return None

    _opener = urllib.request.build_opener(_NoRedirect)

    def _probe(base: str, key: str, *, anthropic: bool = False) -> dict:
        t0 = time.time()
        if not _valid_base_url(base):
            return {
                "baseUrl": base,
                "ok": False,
                "ms": 0,
                "detail": "Base URL 不合法，未发起请求",
            }
        if not _ssrf_safe(base):
            return {
                "baseUrl": base,
                "ok": False,
                "ms": 0,
                "detail": "目标指向本机/内网地址，已拒绝（避免把 API Key 发给内网服务）",
            }
        try:
            if anthropic:
                # Anthropic Messages 协议的鉴权头是 x-api-key（不是 Authorization: Bearer），
                # 且模型列表在 /v1/models。按 OpenAI 兼容方式探测只会得到 401/404，
                # 让用户误以为 Key 无效。同时带上两种头：兼容把 /v1/models 反代成
                # OpenAI 风格的中转站（它们只认 Bearer）。
                url = base + "/v1/models"
                rq = urllib.request.Request(
                    url,
                    headers={
                        "x-api-key": key,
                        "anthropic-version": "2023-06-01",
                        "Authorization": f"Bearer {key}",
                    },
                )
            else:
                rq = urllib.request.Request(
                    base + "/models", headers={"Authorization": f"Bearer {key}"}
                )
            with _opener.open(rq, timeout=15) as resp:
                return {
                    "baseUrl": base,
                    "ok": resp.status == 200,
                    "ms": int((time.time() - t0) * 1000),
                }
        except Exception as e:  # noqa: BLE001
            return {
                "baseUrl": base,
                "ok": False,
                "ms": int((time.time() - t0) * 1000),
                "detail": f"{type(e).__name__}: {e}"[:140],
            }

    def _run_probes() -> list[dict]:
        out: list[dict] = []
        for base, key, is_anthropic in targets:
            out.append(_probe(base, key, anthropic=is_anthropic))
        return out

    results = await asyncio.to_thread(_run_probes)
    return {"channel": channel, "results": results, "testedAt": int(time.time())}
