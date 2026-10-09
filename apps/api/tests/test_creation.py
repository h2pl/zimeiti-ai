"""Task 5.1/5.2 验收：图文草稿生成（fake 模型单测 + 真 key 集成测试跳过逻辑）。"""

import json
import os

import pytest

from zimeiti_api.creation import DraftSet, build_creation_prompt, create_drafts
from zimeiti_api.topics import select_topic

FAKE_OUTPUT = json.dumps(
    {
        "xhs": {
            "title": "AI 提效 3 招",
            "body": "正文…" * 5,
            "tags": ["AI", "提效"],
            "cover_copy": "效率翻倍",
        },
        "gzh": {
            "title": "深度：AI 如何改变工作流",
            "body": "长文…" * 20,
            "summary": "本文聊聊 AI 提效",
        },
    },
    ensure_ascii=False,
)


def _fake_model():
    from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
    from langchain_core.messages import AIMessage

    class FakeToolModel(FakeMessagesListChatModel):
        def bind_tools(self, tools, **kwargs):
            return self

    return FakeToolModel(responses=[AIMessage(content=FAKE_OUTPUT)])


def test_prompt_contains_profile_and_topic():
    topic = select_topic({"title": "AI 提效", "reason": "热点", "direction": "教程"})
    prompt = build_creation_prompt(
        topic,
        {
            "account": "xhs-main",
            "positioning": "职场干货",
            "style": "轻松",
            "audience": "互联网人",
            "platform_rules": "标题≤20字",
            "preferences": "不夸大",
        },
    )
    assert "AI 提效" in prompt
    assert "职场干货" in prompt
    assert "不夸大" in prompt


def test_create_drafts_parses_fake_output():
    topic = select_topic({"title": "AI 提效", "reason": "热点", "direction": "教程"})
    profile = {
        "account": "xhs-main",
        "positioning": "职场",
        "style": "轻松",
        "audience": "互联网人",
        "platform_rules": "标题≤20字",
        "preferences": "不夸大",
    }
    drafts = create_drafts(_fake_model(), topic, profile)
    assert isinstance(drafts, DraftSet)
    assert drafts.xhs.title == "AI 提效 3 招"
    assert drafts.gzh.summary == "本文聊聊 AI 提效"


def test_real_model_integration_skipped_without_key():
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not key or key.startswith("在这里"):
        pytest.skip("未配置 DEEPSEEK_API_KEY")
    from dotenv import load_dotenv

    load_dotenv()
    from langchain.chat_models import init_chat_model

    topic = select_topic({"title": "AI 工具提效", "reason": "需求", "direction": "实战清单"})
    profile = {
        "account": "xhs-main",
        "positioning": "职场干货",
        "style": "轻松",
        "audience": "互联网人",
        "platform_rules": "标题≤20字",
        "preferences": "不夸大",
    }
    drafts = create_drafts(init_chat_model("deepseek:deepseek-chat"), topic, profile)
    assert len(drafts.xhs.body) > 50
