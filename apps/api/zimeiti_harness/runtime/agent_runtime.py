"""deepagents 运行时（phase1-deepagents-runtime）。

用 deepagents（LangGraph）替代 OpenClaw 网关承载对话链路：
- 会话历史与 HITL pending 存 PostgreSQL（zimeiti_api/core/pg.py，pg-data-layer 变更）；
  checkpoint 经 AsyncPostgresSaver 持久化，重启后从 PG 恢复（thread_id 带
  租户命名空间，本地版为 '<local>:<session_key>'）
- `create_deep_agent` 构建 agent，`ask_human` 工具触发 HITL 中断（问题卡内联，
  SSE 连接保持打开，答案经 Command(resume) 注入后同连接续流）
- 流式输出按 Easel 前端 SSE 契约发帧：token / activity / question / error / done
- 模型经环境变量配置：ZIMEITI_MODEL / OPENAI_API_KEY / OPENAI_BASE_URL；
  未配置时返回明确错误帧（服务本身正常）

评审修复记录（2026-10-13 独立评审 C1-C4/I1-I5/W1-W6）：
- resume 决策格式 `{"type":"respond","message":<str>}`（RespondDecision）
- interrupt 载荷从 `action_requests[0].args` 取 question/options；options 按「|」拆分
- question 帧载荷形状对齐前端 ChatQuestion：{"id","questions":[{questionId,question,options}]}
- answer() 把前端 `{questionId:[label]}` 格式化为「问题 → 选项」文本注入
- token 流按 AIMessageChunk 过滤（排除 ToolMessage/合成消息）
- checkpoint 已有消息时不重复注入落盘历史（防上下文成倍膨胀）
- resume 失败补 done 帧 + end()（原连接不再悬挂）
- pending_status 返回 {qid:{"status":...}}（对齐前端）
- session 级 asyncio.Lock 串行化；_LIVE_INTERRUPTS/pending 条目 30 分钟 TTL 惰性清理
- 死代码清理（_LOOP/_ensure_loop/threading/无效 info 查询）；删除与 to_client 双写的 _append_event
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # 仅供类型检查（deepagents 的 SubAgent 规格类型）
    from deepagents.middleware.subagents import SubAgent

from langchain_core.messages import AIMessageChunk

from zimeiti_api.core import pg
from zimeiti_api.core.paths import PROJECT_ROOT

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
TTL_SECONDS = 30 * 60

# ---------- 操作契约（agent-operating-contract：对齐 OpenClaw AGENTS.md/SOUL.md） ----------
#
# 结构分两半：静态契约（人格/执行偏向/follow-through/风险分级/编排纪律——照 OpenClaw
# 「prompt 不预拒绝、风险下沉运行时」的精神中文化）+ 动态事实（技能目录，组装时渲染）。
# 静态段在前（稳定前缀），动态段在后（易变后缀）——OpenClaw provider 缓存边界工程的简化版。

_CONTRACT_HEAD = (
    "你是 Zimeiti AI 自媒体运营 agent，创作者的运营搭子——既是懂策略的操盘手，"
    "也是能上手干活的制作伙伴。从一个热点、一句灵感，到成稿、上传草稿、回头看数据，"
    "你都陪着一起把它做成。"
    "\n\n"
    "【人格与沟通】遇事先想「怎么帮他做成」，而不是「这个我做不了」。清晰坦诚，"
    "卡住时说明原因和可行的替代路径。聚焦自媒体运营场景，不做无关通用闲聊。"
    "注意：你的人设风格管的是**你和用户的沟通方式**；产出的内容风格以当前画像为准。"
    "\n\n"
    "【执行偏向】用户提出的请求，只要你有对应工具能力即为已授权——风险由工具策略、"
    "权限门禁和 ask_human 确认在运行时把关，你不要在提示层预拒绝、不主动警告、"
    "不索求额外许可。"
    "\n\n"
    "【Follow-through】说「我在查/我在做」是进度更新，不是完成答复。回合结束前必须"
    "安排完成路径或观察路径；不得以计划、空壳文件、中途文件冒充成品。禁止回复「已完成」"
    "而交付物并不真实存在。"
    "\n\n"
    "【风险分级 ask-first】清晰且可逆的任务（读取、草稿、本地可撤销修改）直接执行；"
    "以下情形先经 ask_human 说明范围和影响、获得确认后再做：①不可逆或外部可见的操作"
    "（发布、上传、发消息）；②破坏性操作（删除、覆盖）；③涉及隐私或凭据；"
    "④产生费用的操作（生图/生视频/音乐/TTS——给出调用范围与可得的费用预估，"
    "没有单价数据就说明将调用的次数与规格，不要编造金额）。"
    "\n\n"
    "【编排纪律】跨层任务用 glue 脚本传递，不靠口头转述："
    "①排期/内容规划前先读日历上下文 `calendar_ops.py context --days 14`（exec_script 或"
    "bash 不可用时读 outputs/_schedule.json）；②跨层产物经 `manifest.py record/read`"
    "登记「路径+一句结论」，下游从 manifest 读上游，不重新推导；③写入产物路径前用"
    "`output_paths.py` 校验（主题用人类可读的项目名，禁止 xhs/test/tmp 泛名，"
    "禁止在 outputs/ 根目录散落内容文件）。"
    "\n\n"
    "【运营五层流程】运营任务按五层推进，各层有路由 skill（ops-* 指向详细技能）：\n"
    "- ops-discover 发现：找热点/筛选题（触发：找选题、今天写什么、追热点）\n"
    "- ops-plan 策划：赛道判断/选角度（触发：能不能做、选哪个角度、定选题）\n"
    "- ops-create 制作：写成稿+质检（触发：写文章、出初稿、做内容）\n"
    "- ops-publish 发布：上传公众号草稿，只建草稿绝不发布（触发：发这篇、上传草稿）\n"
    "- ops-review 归因：发布记录复盘（触发：复盘、数据怎么样、下期写什么）\n"
    "回复中明示当前所处流程层。"
    "\n\n"
    "【文件系统】你有真实文件系统访问（ls/glob/grep/read_file/write_file 均有效），"
    "根目录即数据根：\n"
    "- skills/：技能库（各技能含 SKILL.md，做任务前先读其流程与数据源说明）\n"
    "- profiles/<画像名>/：画像六维文件（identity/audience/style/preferences 等）\n"
    "- outputs/：内容库，**唯一可写目录**——生成的文章/脚本一律 write_file 到这里\n"
    "账号登录状态与数据统计存在数据库，不在文件系统；查不到就明说，不要反复枚举目录。"
    "\n\n"
    "【白名单脚本】已注册的质检/渲染脚本经 exec_script 工具调用（如 ai_score 文章质检、"
    "content_guard 出站安全扫描、render_card 卡片渲染）；只能调用注册表内的脚本，"
    "调用前先读对应 SKILL.md 了解参数。"
    "\n\n"
    "【记忆】跨会话经验用 memory_record/memory_search：一轮结束出现真正可复用的偏好、"
    "红线、制作技巧或效果归因时，凝练 1-3 条先向用户提出，确认后记录（一次性规格/临时"
    "参数/流水账不记）。检索结果按 [记忆:origin] 标注使用，检索不到就如实说。"
    "边界：画像 memory.md 是画像域长期记忆，记忆库是运营经验域，两者互不写入；"
    "画像更新只经用户确认的画像管理流程。"
    "\n\n"
    "【语言硬约束】无论用户使用什么语言提问，你的全部回复必须使用简体中文；"
    "仅以下内容保留原文：专有名词、平台名、工具/命令/代码、文件路径、以及用户"
    "明确要求保留原文的内容。不要用英文回答中文问题。"
)

_SKILL_CATALOG_HEAD = (
    "\n\n【技能目录】以下是可用技能（name → 一句话说明）。路由纪律：先找与任务**精确匹配**"
    "的技能；没有精确匹配就复用**最接近**的技能；都没有才用通用能力。确定目标后，"
    "**必须先 read_file 它的 SKILL.md 再执行**（路径见括号）。不要凭记忆跳过 SKILL.md，"
    "也不要虚构目录里不存在的技能。"
)


def _skills_catalog() -> str:
    """渲染技能目录段（按 layer 分组，name + description 首句 + 路径）。

    复用 content.skills.get_skills（300s TTL 缓存）；渲染失败时返回空串——
    契约的其余部分不依赖目录存在。
    """
    try:
        from ..contract import get_skills

        groups: dict[str, list[str]] = {}
        for s in get_skills():
            desc = (s.get("description") or "").strip().splitlines()[0][:80]
            groups.setdefault(s.get("layer") or "other", []).append(
                f"- {s['name']}（skills/builtin/{s['name']}/SKILL.md）：{desc}"
            )
        order = ["discover", "plan", "produce", "publish", "attribute", "other"]
        lines = [_SKILL_CATALOG_HEAD]
        for layer in order:
            if groups.get(layer):
                lines.append(f"\n[{layer}]")
                lines.extend(sorted(groups[layer]))
        return "\n".join(lines)
    except Exception:
        return ""


def build_system_prompt() -> str:
    """组装系统提示词：静态契约 + 动态技能目录（agent 构建时调用一次）。"""
    return _CONTRACT_HEAD + _skills_catalog()


# 兼容旧引用的静态视图（不含动态目录）
SYSTEM_PROMPT = _CONTRACT_HEAD


# ---------- 会话历史 / HITL pending（PostgreSQL，见 zimeiti_api/core/pg.py） ----------


def _load_messages(session_key: str) -> list[dict]:
    return pg.messages_load(session_key)


def _save_messages(session_key: str, messages: list[dict]) -> None:
    pg.messages_save(session_key, messages)


def _load_pending() -> dict:
    return pg.pending_load()


def _save_pending(data: dict) -> None:
    raise NotImplementedError("pending 已改 PG 粒度操作，请用 pg.pending_set/pending_del")


async def delete_session(session_key: str, user_id: str = pg.DEFAULT_USER) -> bool:
    """删除会话的全部状态：PG 消息/会话行 + PG checkpoint + HITL pending + 活跃中断登记。

    供 web 端 DELETE /api/session/{key} 调用。四类状态都删净，同 key 再聊
    才不会「复活」旧上下文。返回是否有任何状态被删除。
    """
    deleted = pg.session_delete(session_key, user_id=user_id)
    deleted = bool(pg.pending_delete_by_session(session_key, user_id=user_id)) or deleted
    try:
        saver = pg.get_checkpointer()
        if saver is not None:
            await saver.adelete_thread(pg.thread_id(session_key, user_id))
            deleted = True
    except Exception:  # noqa: BLE001   checkpoint 清理失败不阻断消息删除
        pass
    _LIVE_INTERRUPTS.pop(session_key, None)
    _LOCKS.pop(session_key, None)
    try:
        from ..memory import store as _mem

        _mem.delete_session_injections(session_key)  # 记忆注入日志随会话级联清
    except Exception:  # noqa: BLE001   记忆表未就绪不阻断会话删除
        pass
    return deleted


# ---------- HITL pending TTL 常量（与 pg.PENDING_TTL_SECONDS 同源） ----------

_LOCKS: dict[str, asyncio.Lock] = {}


def _session_lock(session_key: str) -> asyncio.Lock:
    if session_key not in _LOCKS:
        _LOCKS[session_key] = asyncio.Lock()
    return _LOCKS[session_key]


def get_pending(question_id: str) -> dict | None:
    return _load_pending().get(question_id)


def pending_status(question_ids: list[str]) -> dict[str, dict]:
    pend = _load_pending()
    return {qid: {"status": "pending" if qid in pend else "not_found"} for qid in question_ids}


# ---------- 模型与 agent ----------


def _build_base_tools() -> list:
    """非会话绑定的工具集（exec_script + 记忆工具）。

    ask_human 绑定会话上下文（内嵌在 _build_agent 中），故不在此列；
    结构化 graph 是不打断用户的一次性调用，正好只需要这些。
    """
    from ..memory.tools import make_memory_tools
    from .exec_tool import make_exec_tool

    tools = make_exec_tool()
    return [*([tools] if not isinstance(tools, (list, tuple)) else tools), *make_memory_tools()]


def _build_subagents() -> list:
    """专属子代理（agent-subagents-output，design D1/D2）。

    - research：只读探索（无写工具），可用便宜模型（ZIMEITI_SUBAGENT_MODEL）
    - draft：写作（有写工具），但两者都不含 ask_human / exec_script
      ——子代理不打断用户、不跑脚本（越权面在装配处收死）
    - ZIMEITI_SUBAGENT_ENABLED=false → 退回 deepagents 默认通用子代理
    """
    if os.environ.get("ZIMEITI_SUBAGENT_ENABLED", "").strip().lower() == "false":
        return []

    from deepagents.middleware.filesystem import FilesystemPermission

    # 工具面：不传 tools → 继承主 agent 的默认工具（文件六件套，由 FilesystemMiddleware
    # 提供），拿不到 ask_human / exec_script / memory_*（那些是主 agent 的私有工具）。
    # 越权面用 permissions 收死：写操作按角色放行或全拒。
    deny_all_write = [FilesystemPermission(operations=["write"], paths=["/**"], mode="deny")]
    allow_outputs = [
        FilesystemPermission(operations=["write"], paths=["/outputs", "/outputs/**"], mode="allow"),
        FilesystemPermission(operations=["write"], paths=["/**"], mode="deny"),
    ]

    # spec 必须含 model（deepagents 校验），缺省用主模型
    cheap = os.environ.get("ZIMEITI_SUBAGENT_MODEL", "").strip()
    model = cheap or _build_model()
    if model is None:
        return []  # 无模型可用时不派子代理，退回默认通用子代理

    research: dict = {
        "name": "research",
        "description": (
            "只读探索子代理：大范围检索技能库/内容库/历史产物。只查不写，"
            "回报事实与路径，不做判断与创作。"
        ),
        "system_prompt": (
            "你是只读探索子代理。职责：用只读工具查清事实并回报——技能库有哪些技能、"
            "内容库有哪些历史产物、画像文件写了什么。回报格式：结论 + 证据路径列表。"
            "禁止写文件、禁止向用户提问、禁止执行脚本、禁止替主 agent 做创作决策。"
        ),
        "permissions": deny_all_write,  # 只读：任何写操作都被拒
        "model": model,
    }

    draft: dict = {
        "name": "draft",
        "description": (
            "写作子代理：把已定的主题与规格写成稿，落到 outputs/。写完回报路径与字数，"
            "不做发布动作。"
        ),
        "system_prompt": (
            "你是写作子代理。职责：按主 agent 给的主题/规格/风格/红线写成稿，"
            "写入 outputs/（唯一可写目录）。回报格式：文件路径 + 字数 + 自检结论。"
            "禁止向用户提问、禁止执行脚本、禁止任何发布动作。"
        ),
        "permissions": allow_outputs,  # 只能写内容库，其余全拒
        "model": model,
    }
    from typing import cast

    return [cast("SubAgent", research), cast("SubAgent", draft)]


def _build_model():
    from langchain_openai import ChatOpenAI

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    base: dict[str, Any] = {
        "api_key": api_key,
        "streaming": True,
    }
    base_url = os.environ.get("OPENAI_BASE_URL")
    if base_url:
        base["base_url"] = base_url

    def _mk(model_name: str) -> ChatOpenAI:
        # 支持 "模型名@base_url"：跨厂商 fallback（缺省 base_url 则与主模型同凭据）
        kw = dict(base)
        if "@" in model_name:
            name, _, url = model_name.partition("@")
            kw["base_url"] = url
            return ChatOpenAI(model=name, **kw)
        return ChatOpenAI(model=model_name, **kw)

    primary = os.environ.get("OPENAI_MODEL") or os.environ.get("ZIMEITI_MODEL", "gpt-4o-mini")

    # 多 key 轮换（model-cost-rotation）：ZIMEITI_API_KEYS 逗号分隔；
    # 「主模型 × 各 key」作为链上最前置节点——key 限流先换 key，key 用尽才切备用模型
    # （对齐 OpenClaw auth-profile 轮换先于模型 fallback）。未配置时行为不变。
    keys = [k.strip() for k in os.environ.get("ZIMEITI_API_KEYS", "").split(",") if k.strip()]
    primary_variants: list[ChatOpenAI] = []
    if len(keys) > 1:
        for k in keys:
            kw = dict(base)
            kw["api_key"] = k
            primary_variants.append(ChatOpenAI(model=primary, **kw))
    else:
        primary_variants = [_mk(primary)]
    main = primary_variants[0]

    # fallback 链（model-resilience-cron）：ZIMEITI_FALLBACK_MODELS 逗号分隔；
    # 用户在设置里显式选择的模型（ZIMEITI_EXPLICIT_MODEL）严格不 fallback。
    if os.environ.get("ZIMEITI_EXPLICIT_MODEL"):
        return main
    _fb_env = os.environ.get("ZIMEITI_FALLBACK_MODELS", "")
    chain_names = [m.strip() for m in _fb_env.split(",") if m.strip()]
    if not chain_names and len(primary_variants) == 1:
        return main

    from .model_fallback import FallbackChatModel

    n_keys = len(primary_variants)

    def _on_switch(idx: int, exc: Exception) -> None:
        if idx < n_keys - 1:
            print(
                f"[key-rotation] 主模型 {primary} 在 key#{idx + 1} 失败"
                f"（{type(exc).__name__}），换 key#{idx + 2} 重试"
            )
        else:
            fb_idx = idx - (n_keys - 1)
            print(
                f"[model-fallback] 主模型 {primary} 失败（{type(exc).__name__}），"
                f"切换第 {fb_idx + 1} 个备用模型"
            )

    # 备用模型沿用第一个 key（design D3：备用计费 key 需独立时调整 ZIMEITI_API_KEYS 顺序）
    fb_models = []
    for n in chain_names:
        fb = _mk(n)
        if len(keys) > 1 and hasattr(fb, "openai_api_key"):
            from pydantic import SecretStr

            fb.openai_api_key = SecretStr(keys[0])
        fb_models.append(fb)

    return FallbackChatModel(models=[*primary_variants, *fb_models], on_switch=_on_switch)


_AGENT = None


async def _build_agent():
    """构建 deepagents agent（进程内缓存；ask_human 触发 HITL 中断）。

    checkpointer 用 PG（AsyncPostgresSaver，见 zimeiti_api/core/pg.py）：异步图必须配
    异步 saver；实例由 lifespan 经 pg.setup_checkpointer() 预先建好，此处取
    缓存；若未初始化（如测试直连）则当场建。
    """
    global _AGENT
    if _AGENT is not None:
        return _AGENT
    from deepagents import create_deep_agent
    from langchain_core.tools import tool

    @tool
    def ask_human(question: str, options: str = "") -> str:
        """向用户提问并等待回答。question 为问题文本；options 用「|」分隔候选答案（可留空）。"""
        return "已提交问题，等待人工回答。"

    def _build_tools() -> list:
        return [ask_human, *_build_base_tools()]

    checkpointer = await pg.setup_checkpointer()
    _patch_deepagents_subprocess_encoding()
    backend, permissions = _fs_backend()
    _AGENT = create_deep_agent(
        model=_build_model(),
        tools=_build_tools(),
        system_prompt=build_system_prompt(),
        subagents=_build_subagents() or None,  # 空表→退回默认通用子代理
        backend=backend,
        permissions=permissions,
        interrupt_on={"ask_human": True},
        checkpointer=checkpointer,
        # response_format 故意不设：图级配置会约束所有输出，普通对话不应被强制结构化
    )
    return _AGENT


_STRUCTURED_AGENTS: dict[str, object] = {}


async def _build_structured_agent(schema_name: str, schema: type):
    """按 schema 建一个独立 graph（进程内缓存，按 schema 名）。

    response_format 是**图级**配置，设在主 agent 上会约束所有输出（普通对话也被
    强制结构化），故结构化场景单独建图——共用 backend/permissions/工具，不共用
    会话历史（checkpointer=None，一次性调用）。
    """
    if schema_name in _STRUCTURED_AGENTS:
        return _STRUCTURED_AGENTS[schema_name]
    from deepagents import create_deep_agent

    _patch_deepagents_subprocess_encoding()
    backend, permissions = _fs_backend()
    agent = create_deep_agent(
        model=_build_model(),
        tools=_build_base_tools(),
        system_prompt=build_system_prompt(),
        subagents=_build_subagents() or None,
        backend=backend,
        permissions=permissions,
        response_format=schema,
    )
    _STRUCTURED_AGENTS[schema_name] = agent
    return agent


async def chat_structured(schema_name: str, message: str, session_key: str = "") -> dict:
    """结构化对话：返回 schema 实例（dict 形式）。首个场景 topic_evaluation。"""
    from .schemas import TopicEvaluation

    schemas = {"topic_evaluation": TopicEvaluation}
    if schema_name not in schemas:
        raise ValueError(f"未注册的 schema：{schema_name}")
    agent = await _build_structured_agent(schema_name, schemas[schema_name])
    config = {"configurable": {"thread_id": session_key or f"structured-{schema_name}"}}
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": message}]}, config=config
    )
    structured = result.get("structured_response") if isinstance(result, dict) else None
    if structured is None:
        raise RuntimeError("未拿到结构化响应（模型可能未按 schema 产出）")
    return structured.model_dump() if hasattr(structured, "model_dump") else dict(structured)


def _patch_deepagents_subprocess_encoding() -> None:
    """deepagents 的 ripgrep 子进程用 text=True 未指定 encoding——Windows 默认
    GBK 解码 UTF-8 输出必炸（技能库/画像路径含中文）。在其模块命名空间注入
    默认 UTF-8 的 Popen 薄壳（只影响该模块，不动全局 subprocess）。
    服务进程若以 PYTHONUTF8=1 启动（Makefile）本就不受影响，此补丁兜底裸启动。"""
    import subprocess as _sp

    import deepagents.backends.filesystem as fs

    if getattr(fs, "_zimeiti_encoding_patched", False):
        return

    class _SubprocessShim:
        def __getattr__(self, name):
            return getattr(_sp, name)

        @staticmethod
        def Popen(*args, **kwargs):
            if kwargs.get("text") and "encoding" not in kwargs:
                kwargs["encoding"] = "utf-8"
                kwargs.setdefault("errors", "replace")
            return _sp.Popen(*args, **kwargs)

    fs.subprocess = _SubprocessShim()  # type: ignore[assignment]
    fs._zimeiti_encoding_patched = True  # type: ignore[attr-defined]


def _fs_backend():
    """真实文件系统 backend（修复：默认 StateBackend 是图内虚拟 FS，agent 的
    ls/glob/grep/write 全部碰不到真实文件——读不了技能库/画像，产物也落不了盘）。

    根目录锚在数据根 apps/：skills/（技能库，读）、profiles/（画像，读）、
    outputs/（内容库，唯一可写区）。写权限用 FilesystemPermission 收口到 outputs/。
    """
    from deepagents.backends import FilesystemBackend
    from deepagents.middleware.filesystem import FilesystemPermission

    backend = FilesystemBackend(root_dir=str(PROJECT_ROOT), virtual_mode=True)
    permissions = [
        FilesystemPermission(operations=["write"], paths=["/outputs", "/outputs/**"], mode="allow"),
        FilesystemPermission(operations=["write"], paths=["/**"], mode="deny"),
    ]
    return backend, permissions


# ---------- 中断等待中的会话（带 TTL 惰性清理）----------

_LIVE_INTERRUPTS: dict[str, dict] = {}


def _gc_live() -> None:
    now = time.monotonic()
    stale = [k for k, v in _LIVE_INTERRUPTS.items() if now - v.get("ts", now) > TTL_SECONDS]
    for k in stale:
        _LIVE_INTERRUPTS.pop(k, None)


def _extract_interrupt(snapshot) -> dict | None:
    """从 langgraph 快照提取 HITL 中断载荷。

    deepagents 0.7 的中断 value 形如 HITLRequest：
    {"action_requests": [{"name", "args", "description"}], "review_configs": [...]}
    question/options 在 action_requests[0].args 里（ask_human 工具入参）。
    """
    try:
        for t in snapshot.tasks or []:
            for it in getattr(t, "interrupts", None) or []:
                value = getattr(it, "value", None)
                if isinstance(value, dict):
                    reqs = value.get("action_requests") or []
                    if reqs:
                        args = reqs[0].get("args") or {}
                        q = args.get("question") or reqs[0].get("name") or "agent 需要你的输入"
                        opts = args.get("options") or ""
                        if isinstance(opts, str):
                            opts = [o for o in opts.split("|") if o] if opts else []
                        return {"question": str(q), "options": [str(o) for o in opts]}
                if isinstance(value, str):
                    return {"question": value, "options": []}
    except Exception:
        return None
    return None


def _to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(p.get("text", "") for p in content if isinstance(p, dict))
    return ""


async def _checkpoint_has_messages(agent, config) -> bool:
    """checkpoint 是否已有消息（决定是否注入落盘历史，防重复膨胀）。"""
    try:
        state = await agent.aget_state(config)
        msgs = (state.values or {}).get("messages") if isinstance(state.values, dict) else None
        return bool(msgs)
    except Exception:
        return False


async def run_turn(
    session_key: str,
    message: str,
    pk: str,
    turn_id: str,
    event_path: Path,
    emit: Callable,
    end: Callable,
    save_turn: Callable | None = None,
) -> None:
    """跑一轮 deepagents 对话，按 Easel SSE 契约发帧；结束负责落盘与 done 帧。"""
    async with _session_lock(session_key):
        _gc_live()
        model = _build_model()
        if model is None:
            emit(
                "error",
                "❌ 未配置模型：请设置 OPENAI_API_KEY（可选 OPENAI_BASE_URL / ZIMEITI_MODEL）",
            )
            if save_turn:
                save_turn(pk, "error", "", {"turn_id": turn_id})
            emit("done", sessionKey=session_key)
            end()
            return
        try:
            agent = await _build_agent()
        except Exception as e:  # noqa: BLE001
            emit("error", f"❌ 运行时初始化失败：{str(e)[:180]}")
            emit("done", sessionKey=session_key)
            end()
            return

        config = {"configurable": {"thread_id": pg.thread_id(session_key)}}
        from langchain_core.messages import AIMessage, HumanMessage

        lc_messages: list = []
        if not await _checkpoint_has_messages(agent, config):
            # 仅 checkpoint 为空（新线程 / 重启后首轮）才注入落盘历史，
            # 否则 langgraph 追加语义会让上下文成倍膨胀。
            for m in _load_messages(session_key):
                if m.get("content"):
                    lc_messages.append(
                        HumanMessage(content=m["content"])
                        if m["role"] == "user"
                        else AIMessage(content=m["content"])
                    )
        lc_messages.append(HumanMessage(content=message))

        full_text: list[str] = []
        usage_acc: dict = {"prompt": 0, "completion": 0, "model": ""}
        tool_names: set[str] = set()
        interrupted: dict | None = None
        try:
            async for chunk, _meta in agent.astream(
                {"messages": lc_messages}, config=config, stream_mode="messages"
            ):
                if not isinstance(chunk, AIMessageChunk):
                    continue  # 排除 ToolMessage / 状态回放，防止把用户回答当助手输出
                text = _to_text(getattr(chunk, "content", None))
                if text:
                    full_text.append(text)
                    emit("token", text)
                for tc in getattr(chunk, "tool_call_chunks", None) or []:
                    name = tc.get("name")
                    if name and name not in tool_names:
                        tool_names.add(name)
                        emit("activity", f"🔧 {name}…")
                # 用量累计（model-resilience-cron）：末 chunk 带 usage_metadata
                um = getattr(chunk, "usage_metadata", None)
                if isinstance(um, dict):
                    usage_acc["prompt"] = max(usage_acc["prompt"], int(um.get("input_tokens") or 0))
                    usage_acc["completion"] = max(
                        usage_acc["completion"], int(um.get("output_tokens") or 0)
                    )
                    rm = getattr(chunk, "response_metadata", None) or {}
                    if isinstance(rm, dict) and rm.get("model"):
                        usage_acc["model"] = rm["model"]
            snapshot = await agent.aget_state(config)
            interrupted = _extract_interrupt(snapshot)
            # 用量落账（model-resilience-cron）：中断轮次也记（token 已花）
            try:
                from ..usage import record as _usage_record

                # 部分端点不回 model 名 → 退回主模型名（环境变量）
                _model_name = usage_acc["model"] or (
                    os.environ.get("OPENAI_MODEL") or os.environ.get("ZIMEITI_MODEL", "")
                )
                _usage_record(
                    session_key,
                    turn_id,
                    _model_name,
                    usage_acc["prompt"],
                    usage_acc["completion"],
                )
            except Exception:  # noqa: BLE001   用量表不可用不阻断对话
                pass
        except Exception as e:  # noqa: BLE001
            if save_turn:
                save_turn(pk, "error", "", {"turn_id": turn_id})
            emit("error", f"❌ agent 运行失败：{str(e)[:180]}")
            emit("done", sessionKey=session_key)
            end()
            return

        if interrupted:
            qid = uuid.uuid4().hex
            payload = {
                "id": qid,
                "thread_id": session_key,
                "turn_id": turn_id,
                "created_at": time.time(),
                "questions": [
                    {
                        "questionId": qid,
                        "question": interrupted["question"],
                        "options": interrupted["options"],
                    }
                ],
            }
            _LIVE_INTERRUPTS[session_key] = {
                "emit": emit,
                "end": end,
                "pk": pk,
                "ts": time.monotonic(),
                "full_text": full_text,
                "config": config,
                "save_turn": save_turn,
                "pending_ids": [qid],
            }
            pg.pending_set(
                qid,
                session_key,
                {"id": qid, "thread_id": session_key, "created_at": time.time()},
            )
            # 前端 ChatQuestion 契约：{"id", "questions":[{questionId,question,options}]}
            emit("question", json.dumps(payload, ensure_ascii=False))
            emit("activity", "⏸ 等待人工回答（回答后将自动继续）…")
            return  # 不发 done：SSE 保持打开，resume 后在同一连接续流

        text = "".join(full_text)
        _save_messages(
            session_key,
            _load_messages(session_key)
            + [
                {"role": "user", "content": message},
                {"role": "assistant", "content": text},
            ],
        )
        if save_turn:
            save_turn(pk, "done", text, {"turn_id": turn_id})
        emit("done", sessionKey=session_key)
        end()


def _finish_turn(
    session_key: str,
    pk: str,
    text: str,
    emit: Callable,
    end: Callable,
    save_turn: Callable | None = None,
) -> None:
    history = _load_messages(session_key)
    _save_messages(session_key, history + [{"role": "assistant", "content": text}])
    if save_turn:
        try:
            save_turn(pk, "done", text, {})
        except Exception:
            pass
    emit("done", sessionKey=session_key)
    end()


async def answer(question_id: str, answers: Any, resolved_by: str = "web") -> dict:
    """恢复被 ask_human 中断的 agent：注入人工回答，续流输出到原 SSE 连接。"""
    payload = pg.pending_get(question_id)
    if payload is None:
        return {"ok": False, "error": "question not found"}
    sk = payload["thread_id"]
    live = _LIVE_INTERRUPTS.pop(sk, None)
    pg.pending_del(question_id)

    # 前端 QuestionCards 提交形如 {questionId: [选中的 label]}；格式化为可读文本注入
    if isinstance(answers, dict):
        parts = []
        for qid, sel in answers.items():
            sel_text = "、".join(sel) if isinstance(sel, list) else str(sel)
            parts.append(f"{qid} → {sel_text}")
        answer_text = "；".join(parts) if parts else json.dumps(answers, ensure_ascii=False)
    else:
        answer_text = str(answers)

    agent = await _build_agent()
    config = payload.get("config") or {"configurable": {"thread_id": pg.thread_id(sk)}}
    emit = (live or {}).get("emit")
    end = (live or {}).get("end")
    save_turn = (live or {}).get("save_turn")
    pk = (live or {}).get("pk")
    full_text: list[str] = (live or {}).get("full_text", [])
    live_stream = live is not None

    from langgraph.types import Command

    try:
        async for chunk, _meta in agent.astream(
            Command(resume={"decisions": [{"type": "respond", "message": answer_text}]}),
            config=config,
            stream_mode="messages",
        ):
            if not isinstance(chunk, AIMessageChunk):
                continue
            text = _to_text(getattr(chunk, "content", None))
            if text:
                full_text.append(text)
                if emit:
                    emit("token", text)
    except Exception as e:  # noqa: BLE001
        if emit:
            emit("error", f"❌ 续跑失败：{str(e)[:180]}")
        if live_stream and end:
            end()  # 修复 I3：resume 失败也要结束原连接，避免前端永久等待
        return {"ok": False, "error": str(e)}

    text = "".join(full_text)
    if live_stream and emit and end:
        _finish_turn(sk, pk, text, emit, end, save_turn)  # type: ignore[arg-type]  # 上游行为：live 无 pk 时传 None，_finish_turn 内部容忍
    else:
        _save_messages(sk, _load_messages(sk) + [{"role": "assistant", "content": text}])
    return {"ok": True, "last_message": text}


def model_configured() -> bool:
    """模型是否已配置（OPENAI_API_KEY 存在）。供状态面板展示，替代原 OpenClaw 网关探活。"""
    return _build_model() is not None


async def ask(session_key: str, message: str) -> str:
    """非流式执行一轮，返回最终文本。

    被 ask_human 中断时不续答（非流式无法交互），返回提示文本让调用方改走流式对话。
    复用与 run_turn 相同的落盘历史 / checkpoint 注入逻辑。
    """
    async with _session_lock(session_key):
        _gc_live()
        model = _build_model()
        if model is None:
            return "❌ 未配置模型：请设置 OPENAI_API_KEY（可选 OPENAI_BASE_URL / ZIMEITI_MODEL）"
        try:
            agent = await _build_agent()
        except Exception as e:  # noqa: BLE001
            return f"❌ 运行时初始化失败：{str(e)[:180]}"

        # compaction 前 episodic flush（design D3 替代挂点）：消息超阈值先落保险记忆
        try:
            from ..memory.flush import flush_if_long

            history = pg.messages_load(session_key)
            if flush_if_long(session_key, history):
                print(f"[memory] 会话 {session_key} 历史 {len(history)} 条，已 flush episodic")
        except Exception:  # noqa: BLE001   记忆模块不可用不阻断对话
            pass

        config = {"configurable": {"thread_id": pg.thread_id(session_key)}}
        from langchain_core.messages import AIMessage, HumanMessage

        lc_messages: list = []
        if not await _checkpoint_has_messages(agent, config):
            for m in _load_messages(session_key):
                if m.get("content"):
                    lc_messages.append(
                        HumanMessage(content=m["content"])
                        if m["role"] == "user"
                        else AIMessage(content=m["content"])
                    )
        lc_messages.append(HumanMessage(content=message))

        full_text: list[str] = []
        try:
            async for chunk, _meta in agent.astream(
                {"messages": lc_messages}, config=config, stream_mode="messages"
            ):
                if not isinstance(chunk, AIMessageChunk):
                    continue
                text = _to_text(getattr(chunk, "content", None))
                if text:
                    full_text.append(text)
            snapshot = await agent.aget_state(config)
            interrupted = _extract_interrupt(snapshot)
        except Exception as e:  # noqa: BLE001
            return f"❌ agent 运行失败：{str(e)[:180]}"

        if interrupted:
            return f"⏸ 该问题需要人工决策：{interrupted['question']}（请使用流式对话回答）"
        text = "".join(full_text)
        _save_messages(
            session_key,
            _load_messages(session_key)
            + [
                {"role": "user", "content": message},
                {"role": "assistant", "content": text},
            ],
        )
        return text


# 主事件循环（lifespan 时登记）：线程里的 ask_sync 必须把协程投回主循环执行——
# 修复「Lock is bound to a different event loop」：此前线程内 asyncio.run 自建
# 循环，把全局 _AGENT/checkpointer/_LOCKS 的 asyncio 原语绑到线程循环，之后
# 主循环的 chat 全部报错（画像后台增强一跑，chat 就挂）。
_MAIN_LOOP: asyncio.AbstractEventLoop | None = None


def set_main_loop(loop: asyncio.AbstractEventLoop) -> None:
    """组装层 lifespan 启动时登记 uvicorn 主循环。"""
    global _MAIN_LOOP
    _MAIN_LOOP = loop


def ask_sync(session_key: str, message: str) -> str:
    """同步包装 ask（供线程池 / 同步上下文调用）。

    主循环已登记时投回主循环执行（跨线程安全）；否则退回本地自建循环
    （独立进程/脚本场景，无共享 loop 冲突）。
    """
    if _MAIN_LOOP is not None and _MAIN_LOOP.is_running():
        fut = asyncio.run_coroutine_threadsafe(ask(session_key, message), _MAIN_LOOP)
        return fut.result(timeout=900)
    return asyncio.run(ask(session_key, message))
