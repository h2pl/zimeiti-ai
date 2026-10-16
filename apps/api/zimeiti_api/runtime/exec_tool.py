"""ExecTool：白名单脚本执行器（agent-shell-exec）。

安全边界（用户拍板，design D1）：不做任意 shell——只允许执行注册表中的脚本。
agent 跑不了白名单外的任何东西。

- 注册表 SCRIPT_REGISTRY：name → {path, params, desc}
- 校验链：注册表查名 → args key 全在 schema → value 拒路径穿越/绝对路径/命令替换
- 执行：subprocess.run（cwd=数据根、timeout、PYTHONUTF8=1、输出尾部截断）
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

from ..core.paths import PROJECT_ROOT

DEFAULT_TIMEOUT = 120
_MAX_STDOUT = 8 * 1024
_MAX_STDERR = 2 * 1024

# 注册表：name → (脚本相对路径, 参数 schema {flag: 类型}, 说明)
# 路径相对 PROJECT_ROOT（数据根）。首批静态登记（design D4）。
SCRIPT_REGISTRY: dict[str, dict] = {
    "content_guard": {
        "path": "skills/shared/scripts/content_guard.py",
        "params": {"sub": "pos", "--text": "str", "--file": "str", "--out": "str"},
        "desc": "出站内容安全闸门（子命令 scan/redact）：敏感信息扫描（BLOCK 级命中退出码 7）",
    },
    "ai_score": {
        "path": "skills/builtin/skill-wechat-publisher/scripts/ai_score.py",
        "params": {"article": "pos", "--json": "flag", "--threshold": "int"},
        "desc": "文章 AI 味/质量评分（0-100，高于阈值 exit 1）",
    },
    "render_card": {
        "path": "skills/shared/scripts/render_card.py",
        "params": {
            "--html": "str",
            "--out": "str",
            "--selector": "str",
            "--all": "str",
            "--out-dir": "str",
            "--prefix": "str",
            "--full-page": "flag",
            "--width": "int",
            "--height": "int",
        },
        "desc": "HTML → 图片渲染（playwright + chromium，卡片/海报截图）",
    },
}

_DANGEROUS = re.compile(r"[`$|;&<>]")


def _bad_value(v: str) -> bool:
    """值安全校验：拒绝对路径、路径穿越、命令替换字符、过长。"""
    s = str(v)
    if _DANGEROUS.search(s):
        return True
    if s.startswith("/") or s.startswith("\\") or re.match(r"^[A-Za-z]:", s):
        return True
    if ".." in s.replace("\\", "/").split("/"):
        return True
    if len(s) > 512:
        return True
    return False


def _resolve_script(name: str) -> Path | None:
    entry = SCRIPT_REGISTRY.get(name)
    if not entry:
        return None
    p = Path(entry["path"])
    if p.is_absolute():
        # 注册表路径由代码拥有（可信）；绝对路径直用（测试/显式登记场景）
        return p if p.is_file() else None
    # 相对路径锚数据根，且解析后必须在数据根内（防相对路径注册项被符号链接指飞）
    resolved = (PROJECT_ROOT / p).resolve()
    if not str(resolved).startswith(str(PROJECT_ROOT.resolve())):
        return None
    return resolved if resolved.is_file() else None


def available_scripts() -> list[dict]:
    return [
        {"name": k, "desc": v.get("desc", ""), "params": sorted(v.get("params", {}))}
        for k, v in SCRIPT_REGISTRY.items()
    ]


def exec_script(name: str, args: dict | None = None) -> dict:
    """执行注册脚本。返回 {exit_code, stdout, stderr, truncated}；拒绝时 exit_code!=0。"""
    args = args or {}
    script = _resolve_script(name)
    if script is None:
        return {
            "exit_code": 2,
            "stdout": "",
            "stderr": f"未注册或不可用的脚本: {name!r}。白名单机制：仅可执行注册脚本。"
            f"可用：{', '.join(sorted(SCRIPT_REGISTRY))}",
            "truncated": False,
        }

    params = SCRIPT_REGISTRY[name].get("params", {})
    argv: list[str] = []
    for k, v in args.items():
        if k not in params:
            return {
                "exit_code": 2,
                "stdout": "",
                "stderr": f"参数 {k!r} 不在 {name} 的白名单参数内（允许: {sorted(params)}）",
                "truncated": False,
            }
        if _bad_value(v):
            return {
                "exit_code": 2,
                "stdout": "",
                "stderr": f"参数值被拒绝（路径穿越/绝对路径/命令替换字符）: {k}={v!r}",
                "truncated": False,
            }
        if params[k] == "pos":
            argv.append(str(v))  # 位置参数：只传值，不带 flag
        else:
            argv.extend([k, str(v)])

    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    try:
        proc = subprocess.run(  # noqa: S603  注册表路径 + argv 白名单双重收口
            [sys.executable, str(script), *argv],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=DEFAULT_TIMEOUT,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return {
            "exit_code": 124,
            "stdout": "",
            "stderr": f"执行超时（>{DEFAULT_TIMEOUT}s），进程已终止",
            "truncated": False,
        }

    out, err = proc.stdout or "", proc.stderr or ""
    truncated = False
    if len(out) > _MAX_STDOUT:
        out, truncated = out[-_MAX_STDOUT:], True
    if len(err) > _MAX_STDERR:
        err, truncated = err[-_MAX_STDERR:], True
    return {"exit_code": proc.returncode, "stdout": out, "stderr": err, "truncated": truncated}


def make_exec_tool():
    """装配为 LangChain 工具（供 _build_agent 注册）。"""
    from langchain_core.tools import tool

    @tool("exec_script")
    def exec_script_tool(name: str, args_json: str = "{}") -> str:
        """执行白名单注册脚本（质检/渲染等）。仅可调用注册表中的脚本名；
        参数为 JSON 对象（键=脚本 flag，值=str/int）。返回 exit_code/stdout/stderr。"""
        import json

        try:
            args = json.loads(args_json)
        except Exception:
            args = {}
        if not isinstance(args, dict):
            args = {}
        r = exec_script(name, args)
        return json.dumps(r, ensure_ascii=False)

    return exec_script_tool
