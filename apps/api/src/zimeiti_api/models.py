"""模型解析：按环境变量选择 provider（Task 7.2 前置）。"""

from langchain_core.language_models.chat_models import BaseChatModel


def get_model() -> BaseChatModel:
    """返回创作/恢复用的 chat 模型。

    配置了 DEEPSEEK_API_KEY 时用 DeepSeek；
    百炼走 DASHSCOPE_API_KEY + 兼容 base_url；
    都没有时抛错（测试请 monkeypatch 本函数）。
    """
    import os

    from pydantic import SecretStr

    deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if deepseek_key and not deepseek_key.startswith("在这里"):
        from langchain_deepseek import ChatDeepSeek

        return ChatDeepSeek(model="deepseek-chat", api_key=SecretStr(deepseek_key))

    dashscope_key = os.environ.get("DASHSCOPE_API_KEY", "")
    if dashscope_key:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model="qwen-plus",
            api_key=SecretStr(dashscope_key),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )

    raise RuntimeError("未配置模型 key：请在 .env 设置 DEEPSEEK_API_KEY 或 DASHSCOPE_API_KEY")
