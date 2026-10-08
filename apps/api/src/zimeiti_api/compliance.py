"""内容合规出站闸门（Task 5.3，宪法原则 IV：fail-closed 系统级强制）。

规则命中即阻断；审查器自身异常时同样阻断（不能因闸门坏了而放行）。
规则清单可持续扩充，属于产品级护栏（宪法 III/IV 的落地）。
"""

import re

# 凭证泄露：API key 形态（sk-/Bearer 等）
_KEY_PATTERNS = [re.compile(r"sk-[A-Za-z0-9]{8,}"), re.compile(r"(?i)bearer\s+[a-z0-9._-]{16,}")]
# AI 自曝
_AI_SELF = re.compile(r"作为(一个)?(AI|人工智能|语言模型)")
# 夸大收益（平台违禁 + 广告法风险）
_EXAGGERATE = re.compile(r"稳赚不赔|百分百|保本|躺赚|必涨|月入十万")
# 内部地址
_INTERNAL_URL = re.compile(r"(?i)(内网|internal\.|\.local\b|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+)")

_RULES: list[tuple[str, re.Pattern]] = [
    ("凭证泄露", _KEY_PATTERNS[0]),
    ("凭证泄露", _KEY_PATTERNS[1]),
    ("AI 自曝", _AI_SELF),
    ("夸大收益", _EXAGGERATE),
    ("内部地址泄露", _INTERNAL_URL),
]


class ComplianceGate:
    """出站内容审查器。review() 返回 {passed, violations}；fail-closed。"""

    def review(self, text: str) -> dict:
        try:
            violations = self._check_rules(text)
        except Exception as exc:  # noqa: BLE001 - fail-closed：审查器故障必须阻断
            return {"passed": False, "violations": [f"审查器异常，内容已阻断: {exc}"]}
        return {"passed": not violations, "violations": violations}

    def _check_rules(self, text: str) -> list[str]:
        violations: list[str] = []
        for name, pattern in _RULES:
            if pattern.search(text):
                violations.append(f"{name}: 命中合规规则")
        return violations
