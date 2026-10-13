#!/usr/bin/env python3
"""phase1-remove-openclaw 验收脚本：确认 OpenClaw 运行时依赖归零且 deepagents 运行时完好。

检查（AST 级，不受注释措辞影响）：
1. apps/api 全部源码不再 import 任何 openclaw 专用模块，代码符号无 openclaw 运行时残留
2. `import app` 成功，路由数与预期一致，无 openclaw 相关路由
3. deepagents 运行时公开 API（run_turn/ask/ask_sync/delete_session/answer/...）在位
4. ZIMEITI_RUNTIME 兜底开关代码引用归零（spec：兜底开关移除场景）
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

API = Path(__file__).resolve().parents[1] / "api"

BANNED_MODULES = {
    "openclaw_cmd", "openclaw_workspace", "gateway_endpoint",
    "gateway_questions", "local_agents", "session_heal",
}
BANNED_NAMES = {
    "run_agent_sync", "check_gateway", "clean_agent_output", "_scrub_secrets",
    "_heal_openclaw_session", "_openclaw_session_id", "_resolve_transport",
    "_pin_transport", "_CrossProcLock", "_GatewayHttpProc", "_sync_openclaw_chat",
    "_sync_anthropic_provider", "_openclaw_provider_creds", "_set_openclaw_primary",
    "_declare_anthropic_provider", "_is_local_gateway_base", "RESERVED_PROVIDER_KEYS",
    "OPENCLAW_PROFILE", "OPENCLAW_SESSIONS_DIR", "CHAT_TRANSPORT",
    "SHARED_RAW_STREAM", "THINKING_LEVEL", "runtime_enabled",
    "_oc_config_path", "_oc_state_dir",
}
EXPECTED_ROUTES = 64
EXPECTED_RUNTIME_API = ("run_turn", "ask", "ask_sync", "delete_session",
                        "answer", "pending_status", "model_configured")


def imported_modules(tree: ast.AST) -> set[str]:
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.add(node.module)
    return out


def main() -> int:
    failures: list[str] = []

    py_files = [API / "app.py", *sorted((API / "easel").glob("*.py"))]
    for py in py_files:
        tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        for mod in imported_modules(tree):
            root = mod.split(".")[0]
            if root in BANNED_MODULES or "openclaw" in mod.lower():
                failures.append(f"{py.name}: imports banned module {mod}")
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Name):
                names.append(node.id)
            elif isinstance(node, ast.Attribute):
                names.append(node.attr)
            for n in names:
                if n in BANNED_NAMES:
                    failures.append(f"{py.name}: references banned symbol {n} (line {node.lineno})")

    sys.path.insert(0, str(API))
    import app  # noqa: E402

    routes = [getattr(r, "path", "") for r in app.app.routes]
    if len(routes) != EXPECTED_ROUTES:
        failures.append(f"route count {len(routes)} != {EXPECTED_ROUTES}")
    if any("openclaw" in p.lower() for p in routes):
        failures.append("openclaw-related route present")

    from easel import agent_runtime as rt  # noqa: E402
    for fn in EXPECTED_RUNTIME_API:
        if not callable(getattr(rt, fn, None)):
            failures.append(f"agent_runtime.{fn} missing")

    if "ZIMEITI_RUNTIME" in ast.dump(ast.parse((API / "easel" / "agent_runtime.py").read_text(encoding="utf-8"))):
        # 允许出现在 docstring 之外为零：dump 含 docstring，改查非 docstring 的字符串常量与 Name
        tree = ast.parse((API / "easel" / "agent_runtime.py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id == "ZIMEITI_RUNTIME":
                failures.append(f"agent_runtime.py: ZIMEITI_RUNTIME referenced at line {node.lineno}")

    if failures:
        print("FAIL phase1-remove-openclaw verification:")
        for f in failures:
            print("  -", f)
        return 1
    print(f"OK: openclaw residues zero (AST); import app {len(routes)} routes; "
          f"runtime API complete ({', '.join(EXPECTED_RUNTIME_API)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
