"""发布前约束校验（P0⑥，参考: Easel skill-cross-platform-publish publish_dispatch.py
的「约束前置校验 + LLM 适配」职责分离）。

纪律：字数/标签等平台硬约束在**派发前**由本确定性脚本校验，命中即 fail-closed
拒绝（返回违规清单，未调用平台）——取代下游静默截断（截断会静默改变内容语义，
且读回对账会因标题不一致而误判）。
"""

from typing import Any

# 平台硬约束（xiaobei/AiToEarn 实测对齐；xiaohongshu-mcp 服务端亦校验）
XHS_TITLE_LIMIT = 20
XHS_DESC_LIMIT = 1000
XHS_TAGS_LIMIT = 10
GZH_TITLE_LIMIT = 64
GZH_SUMMARY_LIMIT = 120


def preflight(account: str, draft: dict[str, Any]) -> list[str]:
    """校验单平台草稿，返回违规清单（空 = 通过）。draft 统一 dict 形态。"""
    violations: list[str] = []
    title = str(draft.get("title", "")).strip()
    body = str(draft.get("body", "")).strip()
    if not title:
        violations.append("标题为空")
    if not body:
        violations.append("正文为空")
    if account.startswith("xhs"):
        if len(title) > XHS_TITLE_LIMIT:
            violations.append(f"标题超限（{len(title)} > {XHS_TITLE_LIMIT}）")
        if len(body) > XHS_DESC_LIMIT:
            violations.append(f"正文超限（{len(body)} > {XHS_DESC_LIMIT}）")
        tags = draft.get("tags") or []
        if len(tags) > XHS_TAGS_LIMIT:
            violations.append(f"标签超限（{len(tags)} > {XHS_TAGS_LIMIT}）")
    elif account.startswith("gzh"):
        if len(title) > GZH_TITLE_LIMIT:
            violations.append(f"标题超限（{len(title)} > {GZH_TITLE_LIMIT}）")
        summary = str(draft.get("summary", "")).strip()
        if len(summary) > GZH_SUMMARY_LIMIT:
            violations.append(f"摘要超限（{len(summary)} > {GZH_SUMMARY_LIMIT}）")
    return violations
