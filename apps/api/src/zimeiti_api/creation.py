"""图文创作（Task 5.1/5.2）：基于 deepagents 引擎的双平台草稿生成。

创作 prompt 内嵌账号画像五维（隔离由调用方保证单画像传入）；
输出约定为 JSON（xhs/gzh 两平台），解析失败视为创作失败。
"""

import json
from dataclasses import dataclass, field
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel

from zimeiti_api.profiles import build_profile_context
from zimeiti_api.topics import SelectedTopic


@dataclass
class XhsDraft:
    title: str
    body: str
    tags: list[str] = field(default_factory=list)
    cover_copy: str = ""


@dataclass
class GzhDraft:
    title: str
    body: str
    summary: str = ""


@dataclass
class DraftSet:
    xhs: XhsDraft
    gzh: GzhDraft


def build_creation_prompt(topic: SelectedTopic, profile: dict[str, Any]) -> str:
    """组装创作 prompt：画像上下文（+风格 DNA，P1⑩） + 选题 + 输出格式约定。"""
    from zimeiti_api.dna import inject_dna

    context = inject_dna(build_profile_context(profile), profile["account"])
    return (
        f"{context}\n\n"
        f"选题：{topic.title}\n方向：{topic.direction}\n\n"
        "请基于以上信息创作两个平台的图文草稿，"
        "严格遵守画像中的风格、平台规则与偏好红线。\n"
        "合规硬约束（出站闸门按关键词 fail-closed 拦截，误杀不修正）："
        "正文中不得出现「稳赚不赔、百分百、保本、躺赚、必涨、月入十万」等词——"
        "即使用于否定（如「没到躺赚的程度」）也会被拦截，"
        "请改用「远未到不劳而获的程度」等不含违禁词的表达。\n"
        "以 JSON 输出，结构："
        '{"xhs": {"title","body","tags":[],"cover_copy"},'
        ' "gzh": {"title","body","summary"}}'
    )


def _parse_drafts(text: str) -> DraftSet:
    """从模型输出解析 DraftSet；容忍 ```json 围栏。"""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1].removeprefix("json").strip()
    data = json.loads(text)
    return DraftSet(
        xhs=XhsDraft(**data["xhs"]),
        gzh=GzhDraft(**data["gzh"]),
    )


def create_drafts(model: BaseChatModel, topic: SelectedTopic, profile: dict[str, Any]) -> DraftSet:
    """调用模型产出双平台草稿并解析。"""
    result = model.invoke(build_creation_prompt(topic, profile))
    content = result.content
    if not isinstance(content, str):
        raise TypeError(f"模型返回了非文本内容: {type(content).__name__}")
    return _parse_drafts(content)
