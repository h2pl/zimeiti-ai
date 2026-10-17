"""harness 注入点（harness-business-split D1）。

harness 需要的业务输入只有一类：提示词装配期的目录数据（技能清单）。
业务侧在组装层（app.py）启动时注册 provider，harness 不 import 业务域——
依赖方向永远是 app.py → 两侧，harness 与业务解耦。

分层规则（tests/test_layering.py 机械守卫）：
  zimeiti_harness 禁止 import zimeiti_api.{content,automations,platforms,
  operations,governance,routers}；允许 import 共享 infra zimeiti_api.core。
"""

from __future__ import annotations

from collections.abc import Callable

SkillsProvider = Callable[[], list[dict]]

_skills_provider: SkillsProvider = list


def register_skills_provider(fn: SkillsProvider) -> None:
    """注册技能目录 provider（业务侧启动时调用一次；幂等，后注册覆盖）。

    provider 返回 [{name, description, layer, ...}]，失败允许抛异常——
    harness 侧统一降级为空目录（契约其余部分不依赖目录存在）。
    """
    global _skills_provider
    _skills_provider = fn


def get_skills() -> list[dict]:
    """取技能目录；未注册或业务侧异常时返回空列表（harness 自行降级）。"""
    try:
        return _skills_provider() or []
    except Exception:  # noqa: BLE001   目录数据不可用不阻断 agent 装配
        return []
