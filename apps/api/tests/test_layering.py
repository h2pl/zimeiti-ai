"""分层守卫（harness-business-split）：机械验证 harness 对业务域零 import。

规则（zimeiti_harness/contract.py 模块注释与设计文档同步）：
- 禁止：import zimeiti_api 的业务域（content/automations/platforms/operations/
  governance/routers 及 runtime/chat/status 等路由残骸）
- 允许：zimeiti_api.core（共享 infra：路径/PG/设置/超时，无业务逻辑）
- 业务侧不守卫 import（业务 → harness 单向合法），但守卫 scheduler 的
  agent 入口注入纪律（tasks 2.1：set_ask_sync 范式）
"""

from __future__ import annotations

import re
from pathlib import Path

HARNESS_DIR = Path(__file__).resolve().parent.parent / "zimeiti_harness"

# 业务域包名（zimeiti_api.X 中 X 的黑名单）；core 白名单放行
FORBIDDEN = re.compile(
    r"^[ \t]*(from[ \t]+|import[ \t]+)zimeiti_api\.(content|automations|platforms|"
    r"operations|governance|chat_router|status_router|usage_router|app)\b",
    re.M,
)
# 任何 zimeiti_api 主包/子包 import 必须显式以 zimeiti_api.core 开头（白名单）
# [ \t] 而非 \s：防止 ^ 锚点跨行吞噬空行导致行定位错乱（实测踩到）
ANY_ZIMEITI_API = re.compile(r"^[ \t]*(from[ \t]+|import[ \t]+)zimeiti_api(\.|[ \t]|$)", re.M)


def test_harness_exists_and_shaped():
    """harness 包落位：runtime/memory/usage/contract 在位，zimeiti_api/runtime 已消失。"""
    import zimeiti_harness  # noqa: F401

    assert (HARNESS_DIR / "contract.py").is_file()
    assert (HARNESS_DIR / "runtime" / "agent_runtime.py").is_file()
    assert (HARNESS_DIR / "memory" / "store.py").is_file()
    assert (HARNESS_DIR / "usage.py").is_file()
    api_dir = HARNESS_DIR.parent / "zimeiti_api"
    assert not (api_dir / "runtime").is_dir(), "zimeiti_api/runtime 应已迁出"
    assert (api_dir / "chat_router.py").is_file()
    assert (api_dir / "status_router.py").is_file()


def test_harness_never_imports_business_domains():
    """扫描 harness 全部源码：业务域 import 一票否决（含函数级延迟 import）。"""
    violations: list[str] = []
    for py in HARNESS_DIR.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        for m in FORBIDDEN.finditer(text):
            lineno = text[: m.start()].count("\n") + 1
            violations.append(
                f"{py.relative_to(HARNESS_DIR.parent)}:{lineno}: {m.group(0).strip()}"
            )
    assert not violations, "harness 出现业务域 import（分层回潮）：\n" + "\n".join(violations)


def test_harness_only_touched_core_of_zimeiti_api():
    """对 zimeiti_api 的引用只允许共享 infra（zimeiti_api.core.*）。"""
    violations: list[str] = []
    for py in HARNESS_DIR.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        for m in ANY_ZIMEITI_API.finditer(text):
            line = text[m.start() :].splitlines()[0].strip()  # 取完整行（match 只是前缀）
            if line.startswith(("from zimeiti_api.core", "import zimeiti_api.core")):
                continue
            lineno = text[: m.start()].count("\n") + 1
            violations.append(f"{py.relative_to(HARNESS_DIR.parent)}:{lineno}: {line}")
    assert not violations, "harness 只允许 import zimeiti_api.core（共享 infra）：\n" + "\n".join(
        violations
    )


def test_scheduler_agent_entry_injected_not_imported():
    """scheduler 的 agent 入口必须是注入（set_ask_sync），不得 import harness 入口。"""
    src = (HARNESS_DIR.parent / "zimeiti_api" / "automations" / "scheduler.py").read_text(
        encoding="utf-8"
    )
    assert "def set_ask_sync" in src, "缺少注入 setter"
    assert not re.search(
        r"from (\.\.runtime|zimeiti_harness)[.\w]* import (ask_sync|agent_runtime)", src
    ), "scheduler 不得 import agent 入口（必须走组装层注入）"


def test_contract_skills_provider_roundtrip():
    """contract 注入点行为：注册后可取、异常降级空表。"""
    from zimeiti_harness import contract

    sentinel = [{"name": "x", "layer": "other", "description": "d"}]
    contract.register_skills_provider(lambda: sentinel)
    assert contract.get_skills() == sentinel

    def _boom():
        raise RuntimeError("业务侧不可用")

    contract.register_skills_provider(_boom)
    assert contract.get_skills() == [], "provider 异常应降级为空目录"

    contract.register_skills_provider(list)  # 还原为空表，避免污染其他用例
