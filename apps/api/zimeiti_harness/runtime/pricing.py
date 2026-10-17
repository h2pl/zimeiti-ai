"""模型单价表与金额折算（model-cost-rotation，design D1）。

MODEL_PRICING：模型名 → (输入 $/1M token, 输出 $/1M token)。
手工维护——价目更新日期见下；过期是文档问题不是代码问题。
未知模型返回 None：没有单价数据就不编造金额（与操作契约一致）。
"""

from __future__ import annotations

# 价目更新日期：2026-10-17（来源：各厂商官网公示价，USD / 1M tokens）
MODEL_PRICING: dict[str, tuple[float, float]] = {
    # DeepSeek（api.deepseek.com）
    "deepseek-chat": (0.27, 1.10),
    "deepseek-reasoner": (0.55, 2.19),
    # OpenAI（参考价，用于备用链上的常见模型）
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
}


def cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float | None:
    """折算一次调用的 USD 成本；模型未知（含空名）返回 None。

    容错：fallback 链节点形如 "模型名@base_url"，取 @ 前段匹配；大小写不敏感。
    """
    if not model:
        return None
    name = model.split("@", 1)[0].strip().lower()
    prices = MODEL_PRICING.get(name)
    if prices is None:
        return None
    return (prompt_tokens / 1_000_000) * prices[0] + (completion_tokens / 1_000_000) * prices[1]
