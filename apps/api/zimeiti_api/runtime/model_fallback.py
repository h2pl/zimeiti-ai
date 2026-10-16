"""模型 fallback 链（model-resilience-cron，design D1）。

只对基础设施类失败切换（APIConnectionError / RateLimitError / 5xx
APIStatusError）；4xx（参数/鉴权错误）直接抛——鉴权失败切备用模型只会把
真实配置问题藏起来。用户显式选择的模型不走本包装（_build_model 处判断）。

必须是 BaseChatModel 子类：deepagents 的 resolve_model 按 isinstance 分发，
非子类会被当作 "provider:model" 字符串 spec 走 init_chat_model 而炸。
"""

from __future__ import annotations

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import ConfigDict


def _is_infra_failure(exc: BaseException) -> bool:
    """连接错误 / 限流 / 服务端 5xx → 可切换；其余（含 4xx）→ 不切换。"""
    name = type(exc).__name__
    if "Connection" in name or "Timeout" in name:
        return True
    if "RateLimit" in name:
        return True
    status = getattr(exc, "status_code", None)
    if isinstance(status, int) and (status >= 500 or status == 429):
        return True
    return "ServerError" in name


class FallbackChatModel(BaseChatModel):
    """透明包装多个模型：invoke 失败时按链切下一个；bind_tools 整链绑定。

    单模型时行为等价直通（不包装任何额外语义）。
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    models: Any  # list[BaseChatModel]
    on_switch: Any = None  # callable(index, exc)：切换时回调（活动行提示用）

    # ---- 属性透传（deepagents/langchain 内省 model_name 等）----
    def __getattr__(self, name: str) -> Any:
        try:
            return getattr(self.models[0], name)
        except AttributeError:
            raise AttributeError(
                f"{type(self).__name__!r} object has no attribute {name!r}"
            ) from None

    # ---- 同步 ----
    def invoke(self, *args, **kwargs) -> Any:
        last: BaseException | None = None
        for i, m in enumerate(self.models):
            try:
                return m.invoke(*args, **kwargs)
            except Exception as e:  # noqa: BLE001  按类型分流后重抛/切换
                last = e
                if not _is_infra_failure(e) or i == len(self.models) - 1:
                    raise
                if self.on_switch:
                    self.on_switch(i, e)
        raise last if last else RuntimeError("no model")  # pragma: no cover

    # ---- 异步 ----
    async def astream(self, *args, **kwargs):
        last: BaseException | None = None
        for i, m in enumerate(self.models):
            try:
                async for chunk in m.astream(*args, **kwargs):
                    yield chunk
                return
            except Exception as e:  # noqa: BLE001
                last = e
                if not _is_infra_failure(e) or i == len(self.models) - 1:
                    raise
                if self.on_switch:
                    self.on_switch(i, e)
        raise last if last else RuntimeError("no model")  # pragma: no cover

    def bind_tools(self, tools: Any, **kwargs: Any) -> FallbackChatModel:
        """整链绑定工具，返回新链（fallback 语义不丢）。"""
        return FallbackChatModel(
            models=[m.bind_tools(tools, **kwargs) for m in self.models],
            on_switch=self.on_switch,
        )

    # ---- BaseChatModel private impl：deepagents/langchain 的 astream/invoke
    # 实际走这两条（公开 astream/invoke 覆写只在直调时生效），故 fallback 在此实现。
    # models[i] 可能是 RunnableBinding（bind_tools 后），统一用公开 invoke/astream。----
    def _generate(
        self, messages: Any, stop: Any = None, run_manager: Any = None, **kwargs: Any
    ) -> Any:
        last: BaseException | None = None
        for i, m in enumerate(self.models):
            try:
                return m.invoke(messages, stop=stop, **kwargs)
            except Exception as e:  # noqa: BLE001
                last = e
                if not _is_infra_failure(e) or i == len(self.models) - 1:
                    raise
                if self.on_switch:
                    self.on_switch(i, e)
        raise last if last else RuntimeError("no model")  # pragma: no cover

    async def _agenerate(
        self, messages: Any, stop: Any = None, run_manager: Any = None, **kwargs: Any
    ) -> Any:
        from langchain_core.outputs import ChatGeneration, ChatResult

        last: BaseException | None = None
        for i, m in enumerate(self.models):
            try:
                msg = await m.ainvoke(messages, stop=stop, **kwargs)
                # 子类 ainvoke 返回 AIMessage；本层契约要求 ChatResult
                if isinstance(msg, ChatResult):
                    return msg
                return ChatResult(generations=[ChatGeneration(message=msg)])
            except Exception as e:  # noqa: BLE001
                last = e
                if not _is_infra_failure(e) or i == len(self.models) - 1:
                    raise
                if self.on_switch:
                    self.on_switch(i, e)
        raise last if last else RuntimeError("no model")  # pragma: no cover

    async def _astream(
        self, messages: Any, stop: Any = None, run_manager: Any = None, **kwargs: Any
    ):
        from langchain_core.outputs import ChatGenerationChunk

        last: BaseException | None = None
        for i, m in enumerate(self.models):
            try:
                async for item in m.astream(messages, stop=stop, **kwargs):
                    # 本层契约要求 ChatGenerationChunk；子模型公开 astream 给的是
                    # AIMessageChunk（bind_tools 后是 RunnableBinding，同样如此）→ 归一
                    if isinstance(item, ChatGenerationChunk):
                        yield item
                    else:
                        yield ChatGenerationChunk(message=item)
                return
            except Exception as e:  # noqa: BLE001
                last = e
                if not _is_infra_failure(e) or i == len(self.models) - 1:
                    raise
                if self.on_switch:
                    self.on_switch(i, e)
        raise last if last else RuntimeError("no model")  # pragma: no cover

    @property
    def _llm_type(self) -> str:
        return "fallback-chat-model"
