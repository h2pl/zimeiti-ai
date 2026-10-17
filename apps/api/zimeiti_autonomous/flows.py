"""运营流程定义（autonomous-flow D1）：五层步骤的固定枚举 + 有序子集裁剪。

不做通用 DAG 引擎——运营链路就是这五层，配置面只需「勾哪些步骤、按什么顺序」。
"""

from __future__ import annotations

# 五层运营流程（与既有五层技能一一对应）
STEPS: tuple[str, ...] = ("discover", "plan", "produce", "publish", "review")

STEP_LABELS = {
    "discover": "发现（找热点/选题线索）",
    "plan": "选题（评估与定题）",
    "produce": "创作（成稿/素材）",
    "publish": "发布（上传草稿/发布）",
    "review": "复盘（数据与归因）",
}

# 每层步骤的执行指令（交给 agent 的 prompt 主体）
STEP_INSTRUCTION = {
    "discover": "执行发现层流程：检索与筛选出值得写的热点与选题线索，给出候选清单。",
    "plan": "执行选题层流程：对上一步候选做评估，选出本期要做的题并给出切入角度。",
    "produce": "执行创作层流程：按选题与画像出成稿（含必要的素材与质检）。",
    "publish": "执行发布层流程：排版并推进发布通道（注意付费/发布类动作需人工确认）。",
    "review": "执行复盘层流程：基于发布与互动数据做归因，给出下一轮建议。",
}

_SUMMARY_LIMIT = 1200


def validate_steps(steps: list[str] | tuple[str, ...] | None) -> list[str]:
    """校验步骤集：非空、全部属于五层枚举；保留用户给定顺序。

    非法即 ValueError——配置面早失败，别让错误配置混进调度。
    """
    if not steps:
        raise ValueError("步骤集不能为空")
    got = [str(s).strip() for s in steps]
    unknown = [s for s in got if s not in STEPS]
    if unknown:
        raise ValueError(f"未知步骤：{unknown}（可选：{list(STEPS)}）")
    return got


def build_step_prompt(step: str, config: dict, prev_summary: str) -> str:
    """组装单步 prompt：层指令 + 全局配置 + 上一步摘要（D2）。

    完整产出不进 prompt（只落文件），摘要截断防上下文膨胀。
    """
    parts = [STEP_INSTRUCTION[step]]
    topic = (config or {}).get("topic") or ""
    if topic:
        parts.append(f"本期主题/方向：{topic}")
    platform = (config or {}).get("platform") or ""
    if platform:
        parts.append(f"目标平台：{platform}")
    if (config or {}).get("draft_only"):
        parts.append("只产出草稿，不要执行真实发布动作。")
    if prev_summary:
        parts.append("上一步产出摘要：\n" + prev_summary[:_SUMMARY_LIMIT])
    return "\n".join(parts)


def summarize(text: str, limit: int = _SUMMARY_LIMIT) -> str:
    """产出摘要（供下一步作为输入）：截断到上限，宁短勿滥。"""
    t = (text or "").strip()
    return t[:limit]
