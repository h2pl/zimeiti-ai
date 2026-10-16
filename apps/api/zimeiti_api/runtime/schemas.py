"""结构化输出 schema（agent-subagents-output）。

首个场景：选题评估评分表。后续场景（如质检报告、复盘结论）同样在此扩展。
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TopicEvaluation(BaseModel):
    """选题评估结果：各维度评分 + 综合结论 + 建议。"""

    dimensions: dict[str, int] = Field(
        default_factory=dict,
        description="维度分（0-10），如 赛道匹配/差异化/时效/变现/成本/合规",
    )
    overall: int = Field(description="综合评分 0-100")
    verdict: str = Field(description="结论：做 / 不做 / 改角度后做")
    advice: list[str] = Field(default_factory=list, description="给作者的具体建议要点")
