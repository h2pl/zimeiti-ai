"""记忆工具（agent-memory-system）：memory_record / memory_search。

使用纪律（docstring 即 agent 可见的契约）：
- record 只记可复用经验（偏好/红线/技巧/归因）；一次性规格不记；记录前须已向用户
  凝练并征得确认
- search 结果按 [记忆:origin] 标注使用；同一会话已注入的条目不重复返回
"""

from __future__ import annotations

from . import store


def make_memory_tools() -> list:
    from langchain_core.tools import tool

    @tool("memory_record")
    def memory_record(
        content: str, origin: str = "agent", importance: int = 5, tags: str = ""
    ) -> str:
        """记录一条可复用的运营经验到长期记忆。

        content：一句话经验（用户偏好/红线/制作技巧/效果归因）。
        origin：owner=用户明确陈述，agent=你凝练后经用户确认，system=系统事件。
        importance：1-10，≥7 才值得长期记住（偏好/红线/反复认可的方法）。
        tags：逗号分隔的标签。
        注意：一次性规格、临时参数、流水账不要记录；调用前必须已向用户提出并获确认。
        """
        try:
            eid = store.record(
                content,
                origin=origin,
                importance=importance,
                tags=[t.strip() for t in tags.split(",") if t.strip()],
            )
            return f"已记录（id={eid}）"
        except ValueError as e:
            return f"记录被拒绝：{e}"

    @tool("memory_search")
    def memory_search(query: str, limit: int = 8) -> str:
        """检索长期记忆中的相关经验。query 为关键词（子串匹配）。

        返回结果带 origin 溯源；同一会话已注入过的条目不重复返回。
        检索不到就如实说没有相关记忆，不要编造。
        """
        hits = store.search(query, session_key=None, limit=limit)
        if not hits:
            return "（无相关记忆）"
        lines = [f"- [记忆:{h['origin']}|重要度{h['importance']}] {h['content']}" for h in hits]
        return "\n".join(lines)

    return [memory_record, memory_search]
