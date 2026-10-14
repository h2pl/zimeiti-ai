"""环境/模型配置读取与写入（core）。

原 app.py 的设置面板支撑层：env 读写、key 判定、模型规格、代理环境。
"""

from __future__ import annotations

import ipaddress
import os
import re
import socket
import urllib.parse

from fastapi import HTTPException
from model_registry import model_group

from .paths import PROJECT_ROOT


def _k(env, label, required=True, secret=True, aliases=None):
    return {
        "env": env,
        "label": label,
        "required": required,
        "secret": secret,
        "aliases": aliases or [],
    }


def _model_spec(group: str, label: str | None = None) -> dict:
    spec = model_group(group)
    return {
        "label": label or spec["label"],
        "settings": spec.get("settings", []),
        "providers": spec["providers"],
    }


def _short_drama_spec() -> dict:
    """Image is required; video and cloud voice settings remain optional enhancements."""
    image = model_group("image")
    optional: list[dict] = []
    for group_name in ("video", "voice"):
        group = model_group(group_name)
        optional.extend({**key, "required": False} for key in group.get("settings", []))
        for provider in group["providers"]:
            optional.extend({**key, "required": False} for key in provider["keys"])
    seen: set = set()
    dedup = []
    for key in optional:
        if key["env"] not in seen:
            seen.add(key["env"])
            dedup.append(key)
    optional = dedup
    return {
        "label": "AI 短剧（生图必需 + 生视频/云配音可选）",
        "settings": [],
        "providers": [
            {
                "id": "drama",
                "name": "关键帧生图（必需）+ 视频生成与闭源配音（可选）",
                "keys": [*image["providers"][0]["keys"], *optional],
            }
        ],
    }


SKILL_API_REQUIREMENTS: dict[str, dict] = {
    "ai-image-gen": _model_spec("image"),
    "ecom-details-image": _model_spec("image", "电商配图（AI 生图）"),
    "ai-video-gen": _model_spec("video"),
    "ai-music": _model_spec("music"),
    "voice-clone": _model_spec("voice", "声音克隆 / 云端 TTS"),
    # AI 短剧：编排 ai-image-gen(关键帧,必需) + ai-video-gen(生视频,可选,缺则退化图片短剧)。
    # 以生图为「已配置」基线（缺生图无法出关键帧）；生视频 key 同框可选填，
    # 也可在 ai-video-gen 卡片配。
    "short-drama": _short_drama_spec(),
    # 论文解读：MinerU 与生图均为可选（缺 MinerU 用 pdfplumber 兜底、缺生图用信息图/图表）。
    # 全 key 可选 → 不误报感叹号；但仍进注册表以便就地填 MINERU_API_TOKEN
    # （无其它叶子 skill 承载它）。
    "paper-explainer": {
        "label": "论文解读（MinerU / 生图 均可选）",
        "providers": [
            {
                "id": "paper",
                "name": "MinerU 解析(可选, 缺则 pdfplumber) + 封面/概念生图(可选)",
                "keys": [
                    _k(
                        "MINERU_API_TOKEN",
                        "MinerU API Token（可选，缺则用 pdfplumber 兜底）",
                        required=False,
                    ),
                    _k(
                        "IMG_API_KEY",
                        "生图 API Key（可选，用于封面/概念图）",
                        required=False,
                        aliases=["OPENAI_API_KEY", "API_KEY"],
                    ),
                    _k(
                        "IMG_BASE_URL",
                        "生图 API 根地址（可选）",
                        required=False,
                        secret=False,
                        aliases=["OPENAI_BASE_URL", "OPENAI_API_BASE", "BASE_URL"],
                    ),
                ],
            },
        ],
    },
}

_ENV_ALLOWLIST: set[str] = set()
for _spec in SKILL_API_REQUIREMENTS.values():
    for _key in _spec.get("settings", []):
        _ENV_ALLOWLIST.add(_key["env"])
        _ENV_ALLOWLIST.update(_key.get("aliases", []))
    for _prov in _spec["providers"]:
        for _key in _prov["keys"]:
            _ENV_ALLOWLIST.add(_key["env"])
            _ENV_ALLOWLIST.update(_key.get("aliases", []))

ENV_FILE = PROJECT_ROOT / ".env"
_PLACEHOLDER_RE = re.compile(r"replace_me|your[-_]?api[-_]?key|xxx|^\.{3}$|^<.*>$", re.I)


def _proxy_env() -> dict[str, str]:
    """返回带外网代理的环境变量（保护内网直连）。"""
    env = os.environ.copy()
    env.setdefault("EASEL_ROOT", str(PROJECT_ROOT))
    env.setdefault("http_proxy", os.environ.get("EASEL_PROXY", ""))
    env.setdefault("https_proxy", os.environ.get("EASEL_PROXY", ""))
    env.setdefault(
        "no_proxy",
        "localhost,127.0.0.1,10.*,*.xiaohongshu.com,*.devops.xiaohongshu.com,*.douyin.com,*.kuaishou.com,*.zhihu.com,*.bilibili.com,*.weixin.qq.com,*.qq.com",
    )
    return env


def _read_env() -> dict[str, str]:
    """宽松解析项目根 .env → {KEY: value}。跳过注释与非 KEY=value 行（容忍多行值残行）。"""
    result: dict[str, str] = {}
    if not ENV_FILE.is_file():
        return result
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        key, val = s.split("=", 1)
        key = key.strip()
        if key.isidentifier() or key.replace("-", "_").isidentifier():
            result[key] = val.strip()
    return result


def _is_set(val: str | None) -> bool:
    """非空且非占位符才算真正配置了。"""
    if not val or not val.strip():
        return False
    return not _PLACEHOLDER_RE.search(val.strip())


def _mask(val: str) -> str:
    """脱敏：只留尾 4 位（短值全遮）。"""
    v = val.strip()
    if len(v) <= 4:
        return "••••"
    return "••••" + v[-4:]


def _key_configured(key: dict, env: dict[str, str]) -> bool:
    "某个 key（含别名）是否已配置。"
    if _is_set(env.get(key["env"])):
        return True
    return any(_is_set(env.get(a)) for a in key.get("aliases", []))


def _skill_api_configured(skill: str, env: dict[str, str] | None = None) -> bool:
    "SKILL 是否已具备可用配置：任一 provider 的全部 required key 齐全。"
    spec = SKILL_API_REQUIREMENTS.get(skill)
    if not spec:
        return True
    env = _read_env() if env is None else env
    for prov in spec["providers"]:
        if all(_key_configured(k, env) for k in prov["keys"] if k["required"]):
            return True
    return False


# .env 的值是裸写 `KEY=value` 的，而 setup.sh:310/450 会 `source .env`。bash 在赋值右侧
# 不做分词和通配，但**照做**命令替换，且元字符会截断赋值另起一条命令 —— 所以 `$(…)`、反引号、
# `;`/`&`/`|`/`(`/`)`/`<`/`>`/空白 都等于任意命令执行。加引号写入不行：scripts/gateway.sh:63
# 用 `sed -n 's/^KEY=//p'` 裸取值，引号会跟着漏进端口号。只能在入口把值的字符集收死。
# 这里能写的全是 API Key / Base URL / 模型 id / 端口，没有一个需要空格或上面那些字符。
_ENV_VALUE_OK = re.compile(r"[A-Za-z0-9_.:/@+\-=~,%?#\[\]]*")


def _guard_env_values(updates: dict[str, str]) -> None:
    """集中拦截 .env 值注入：值里带换行能往 .env 追加任意行，带 `$(…)` 能直接执行命令
    —— 两者都等于任何能调到写 .env 接口的人都能拿到命令执行。键名同理。两个写入口都必须先过这道。"""
    for k, v in updates.items():
        if any(c in (k or "") for c in "\r\n=") or not re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_]*", k or ""
        ):
            raise HTTPException(400, f"非法的配置键名：{(k or '')[:40]!r}")
        v = v or ""
        if any(c in v for c in "\r\n\x00"):
            raise HTTPException(400, f"配置值不能包含换行符：{k}")
        if not _ENV_VALUE_OK.fullmatch(v):
            bad = "".join(sorted({c for c in v if not _ENV_VALUE_OK.fullmatch(c)}))
            raise HTTPException(400, f"配置值含不允许的字符（{bad!r}）：{k}")


# 设置面板里「改了 Base URL 就必须重填 Key」要比对的 .env 键位（槽位 → (base 键, key 键)）。
_SLOT_ENV_KEYS = {
    "openai": ("OPENAI_BASE_URL", "OPENAI_API_KEY"),
    "relay": ("EASEL_LLM_BASE_URL", "EASEL_LLM_API_KEY"),
    "anthropic": ("ANTHROPIC_BASE_URL", "ANTHROPIC_API_KEY"),
    "siliconflow": ("SILICONFLOW_BASE_URL", "SILICONFLOW_API_KEY"),
}


def _valid_base_url(u: str) -> bool:
    "整串校验（不是只看开头）：必须是 http(s)://host，且不带控制字符与 URL 内嵌凭据。"
    if any(c in u for c in "\r\n\t\x00") or "@" in u:
        return False
    try:
        p = urllib.parse.urlparse(u)
    except ValueError:
        return False
    return p.scheme in ("http", "https") and bool(p.hostname)


def _ssrf_safe(u: str) -> bool:
    """自测会带着真 Key 去打这个地址，所以不许指向本机/内网/云元数据——
    这些地址上的服务通常无鉴权，一旦被当成「模型端点」就成了打内网的跳板。"""
    try:
        host = urllib.parse.urlparse(u).hostname or ""
        infos = socket.getaddrinfo(host, None)
    except Exception:  # noqa: BLE001  解析不了就当不安全
        return False
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            return False
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False
    return True


def _write_env(updates: dict[str, str]) -> None:
    "就地更新命中的 KEY、其余行原样保留，未命中的追加末尾；空串则删除该行。原子写。"
    updates = {k: v for k, v in updates.items() if k in _ENV_ALLOWLIST}
    _guard_env_values(updates)
    if not updates:
        return
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
            val = updates[matched]
            if val.strip() == "":
                continue
            out.append(f"{matched}={val}")
            continue
        out.append(line)
    appended = [f"{k}={v}" for k, v in updates.items() if k not in seen and v.strip() != ""]
    if appended:
        if out and out[-1].strip() != "":
            out.append("")
        out.append("# ---- Easel API keys (added via Web) ----")
        out.extend(appended)
    tmp = ENV_FILE.with_suffix(".env.tmp")
    tmp.write_text("\n".join(out) + "\n", encoding="utf-8")
    tmp.replace(ENV_FILE)
