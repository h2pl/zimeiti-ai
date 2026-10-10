"""业务工具集工厂（评审 C1-C4 修复：把合规/执行器/草稿/选题闸门接进 agent 链路）。

设计要点（对应 design.md 评审修复记录）：
- 会话状态外置为 cycle_dir/state.json——工作台与托管跨进程共享（发布审批在另一进程 resume）
- create_drafts 闸门：未挑选选题不得创作（topics.select_topic 唯一入口）
- 合规闸门：草稿落盘前强制过审（fail-closed），未过审不可发布
- publish 走 PublishExecutor（频控/白名单/凭证前置），并在审计留工具级痕迹
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_core.tools import tool

from zimeiti_api.content.creation import create_drafts as _create_drafts
from zimeiti_api.content.topics import discover_topics as _discover_topics
from zimeiti_api.content.topics import select_topic as _select_topic
from zimeiti_api.core import audit
from zimeiti_api.governance.compliance import ComplianceGate
from zimeiti_api.governance.publisher import PublishExecutor
from zimeiti_api.operations.metrics import MetricsDB

logger = logging.getLogger(__name__)

publish_calls: list[str] = []  # 兼容观测口（真实发布时记录）


def real_platform_router(
    account: str, draft: Any, cover_image_path: str | None = None
) -> dict[str, Any]:
    """真实平台路由器（Task 1.1，D1）：按账号前缀路由到真实平台调用并读回。

    返回 {"platform_result": ..., "readback": ...}；未知账号 fail-closed 拒绝。
    """
    title = draft["title"] if isinstance(draft, dict) else draft.title
    if account.startswith("gzh"):
        from zimeiti_api.core.credentials import load_account_credentials
        from zimeiti_api.platforms.gzh import GzhClient, publish_gzh_draft, readback_gzh_draft

        creds = load_account_credentials(account)  # 宪法 II：Fernet 解密注入，不走明文 env
        client = GzhClient(creds["app_id"], creds["app_secret"])
        outcome = publish_gzh_draft(client, draft, cover_image_path=cover_image_path)
        outcome["readback"] = readback_gzh_draft(client, title)
        from zimeiti_api.core import notify

        notify.send(
            "publish_result", f"[{account}] 草稿箱上传 outcome={outcome['readback']}：{title}"
        )
        return outcome
    if account.startswith("xhs"):
        from zimeiti_api.core import notify
        from zimeiti_api.governance import platform_state, risk
        from zimeiti_api.platforms.xhs import XhsPublisher

        if not platform_state.is_enabled(account):
            raise ValueError(f"平台 {account} 已停用（登录失效待人工恢复），拒绝发布")
        pub = XhsPublisher()
        # 私密发布（仅自己可见）——宪法 I 落地形态，人工确认后才公开
        try:
            platform_result = pub.publish_draft(draft, cover_path=cover_image_path)
        except Exception as exc:
            risk.handle_platform_error(account, "publish", str(exc))
            raise
        xhs_outcome = {
            "platform_result": platform_result,
            "readback": _xhs_readback_subprocess(title),
        }
        notify.send(
            "publish_result",
            f"[{account}] 发布完成 outcome={xhs_outcome['readback']}：{title}",
        )
        return xhs_outcome
    raise ValueError(f"未知平台账号: {account}")


def _xhs_readback_subprocess(title: str) -> str:
    """小红书读回走独立子进程（zimeiti_api.platforms.xhs_readback CLI）。

    为何必须子进程：litellm/agent 运行时残留事件循环会使主进程 sync Playwright
    报「Sync API inside the asyncio loop」（A3 实测，线程隔离无效）。
    参考: scripts/walkthrough_a3_xhs.py 的读回实现。
    """
    import subprocess  # nosec B404 - 仅调用本项目固定 CLI，无 shell
    import sys

    try:
        proc = subprocess.run(  # nosec B603 - 参数为固定模块名+标题，无 shell 拼接
            [sys.executable, "-m", "zimeiti_api.platforms.xhs_readback", "--title", title],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=300,
            cwd=str(Path(__file__).resolve().parents[2]),
        )
        return json.loads(proc.stdout.strip().splitlines()[-1])["outcome"]
    except Exception:  # noqa: BLE001 - 观测层异常降级为 unverified（不冒报成功）
        logger.warning("xhs 子进程读回失败，降级 unverified", exc_info=True)
        return "unverified"


def _load_state(cycle_dir: Path) -> dict:
    f = Path(cycle_dir) / "state.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return {"cards": [], "selected": None, "drafts": None, "compliance": None}


def _save_state(cycle_dir: Path, state: dict) -> None:
    """原子写：tmp + replace，避免跨进程读到半截 JSON。"""
    f = Path(cycle_dir) / "state.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    os.replace(tmp, f)


def build_default_tools(
    profile: dict[str, Any],
    model: Any,
    executor: PublishExecutor,
    cycle_dir: Path | str,
    output_root: Path | str | None = None,
    platform_router: Any | None = None,
) -> list:
    """按账号画像构建工具集。

    platform_router：平台调用路由（默认 real_platform_router；测试注入记录型）。


    cycle_dir：本轮变更的会话目录（跨进程共享状态）；
    output_root：草稿/产物根目录（默认 outputs/，测试可用环境变量重定向）。
    """
    account = profile["account"]
    router = platform_router or real_platform_router
    gate = ComplianceGate()

    def _account_credentials() -> str:
        """读取本账号密文凭证（宪法 II：密文落盘；解密由执行器单次完成）。"""
        cred_dir = Path(
            os.environ.get("ZIMEITI_CREDENTIALS_DIR")
            or __import__("zimeiti_api.config", fromlist=["CREDENTIALS_DIR"]).CREDENTIALS_DIR
        )
        f = cred_dir / f"{account}.sealed"
        if not f.exists():
            raise ValueError(f"账号 {account} 无已存凭证（{f}）。请先完成平台登录并加密保存。")
        return f.read_text(encoding="utf-8").strip()

    def _record_publish_event(
        state: dict,
        status: str,
        notes: str = "",
        publish_url: str = "",
    ) -> None:
        """发布成功/失败均记录事件（ops-metrics 数据源，spec 要求不静默丢弃）。"""
        try:
            selected = state.get("selected") or {}
            MetricsDB().record_event(
                platform=account,
                title=selected.get("title", ""),
                source_folder=cdir.name,
                publish_date=datetime.now().strftime("%Y-%m-%d"),
                profile=profile.get("account", ""),
                topic_direction=selected.get("direction", ""),
                status=status,
                notes=notes,
                publish_url=publish_url,
            )
        except Exception as exc:  # noqa: BLE001 - 数据层异常不影响发布结果返回
            audit.record("metrics_record_failed", account=account, error=str(exc))

    cdir = Path(cycle_dir)
    out_root = Path(output_root or os.environ.get("ZIMEITI_OUTPUT_DIR", "outputs"))

    @tool
    def discover_topics(manual_direction: str = "") -> str:
        """发现选题：产出选题卡列表（JSON）。选题需要人工挑选后才能进入创作。"""
        cards = _discover_topics(profile, manual_direction=manual_direction or None)
        state = _load_state(cdir)
        state["cards"] = cards
        state["selected"] = None
        _save_state(cdir, state)
        audit.record("topic_discovered", account=account, count=len(cards))
        return json.dumps(cards, ensure_ascii=False)

    @tool
    def select_topic(title: str) -> str:
        """人工挑选选题（hosted 模式此调用触发审批中断）。未挑选时创作被闸门阻断。"""
        state = _load_state(cdir)
        card = next((c for c in state.get("cards", []) if c["title"] == title), None)
        selected = _select_topic(card)
        state["selected"] = {
            "title": selected.title,
            "reason": selected.reason,
            "direction": selected.direction,
        }
        _save_state(cdir, state)
        audit.record("topic_selected", account=account, title=title)
        return f"已选定选题：{selected.title}（{selected.direction}）"

    @tool
    def create_drafts() -> str:
        """创作双平台图文草稿（要求先挑选选题）。产出自动过合规闸门并落盘。"""
        state = _load_state(cdir)
        selected = state.get("selected")
        if not selected:
            return "错误：尚未挑选选题，创作被闸门阻断"
        try:
            drafts = _create_drafts(model, _select_topic(selected), profile)
        except Exception as exc:
            audit.record("creation_failed", account=account, error=str(exc))
            return f"创作失败：{exc}"
        violations = []
        for d in (drafts.xhs, drafts.gzh):
            r = gate.review(f"{d.title}\n{d.body}")
            if not r["passed"]:
                violations += r["violations"]
        compliance = {"passed": not violations, "violations": violations}
        slug = datetime.now().strftime("%Y%m%d-%H%M%S")
        out = out_root / account / slug
        out.mkdir(parents=True, exist_ok=True)
        (out / "drafts.json").write_text(
            json.dumps(
                {
                    "topic": selected["title"],
                    "account": account,
                    "created_at": datetime.now().isoformat(),
                    "compliance": compliance,
                    "drafts": {"xhs": vars(drafts.xhs), "gzh": vars(drafts.gzh)},
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        state["drafts"] = {"path": str(out)}
        state["compliance"] = compliance
        _save_state(cdir, state)
        audit.record(
            "drafts_created", account=account, path=str(out), compliance=compliance["passed"]
        )
        if violations:
            return f"草稿已生成但被合规闸门阻断：{violations}（不可发布）"
        return f"草稿已生成并通过合规审查，落盘 {out}（可进入发布审批）"

    @tool
    def publish() -> str:
        """发布已通过合规审查的草稿（此调用触发人工审批中断）。"""
        state = _load_state(cdir)
        drafts_ref = state.get("drafts")
        if not drafts_ref or not (state.get("compliance") or {}).get("passed"):
            return "错误：没有通过合规审查的草稿可发布"
        drafts = json.loads((Path(drafts_ref["path"]) / "drafts.json").read_text(encoding="utf-8"))[
            "drafts"
        ]
        try:
            platform_draft = drafts["gzh"] if account.startswith("gzh") else drafts["xhs"]
            # 发布前约束校验前置（P0⑥，fail-closed：命中即拒绝，未调用平台）
            from zimeiti_api.governance.preflight import preflight

            pre_violations = preflight(account, platform_draft)
            if pre_violations:
                audit.record("preflight_rejected", account=account, violations=pre_violations)
                return f"发布前约束校验未通过：{pre_violations}（fail-closed，未调用平台）"
            # 平台启停门禁（P0⑦）
            from zimeiti_api.governance import platform_state

            if not platform_state.is_enabled(account):
                return "错误：平台已停用（登录失效待人工恢复），拒绝发布"
            result = executor.publish(
                account,
                platform_draft,
                platform_call=router,
                credentials_sealed=_account_credentials(),
            )
        except Exception as exc:
            audit.record("publish_failed", account=account, error=str(exc))
            _record_publish_event(state, status="failed", notes=str(exc))
            return f"发布被护栏拒绝：{exc}"
        publish_calls.append(state["selected"]["title"])
        audit.record("published", account=account, outcome=result["readback"])
        _record_publish_event(
            state,
            status="ok",
            notes=f"outcome={result['readback']}",
            publish_url=str(result.get("platform_result", "")),
        )
        return f"发布结果：{result}"

    @tool
    def ask_human(question: str, options: str = "") -> str:
        """执行中向人提问（触发人工应答中断）。

        此工具体永不执行：人工回答经 respond 决策以合成 ToolMessage 注入
        （deepagents/langchain HumanInTheLoop 协议）。options 用「|」分隔候选答案。
        """
        raise RuntimeError("ask_human 不应被执行——应经 respond 决策由人回答")

    return [discover_topics, select_topic, create_drafts, publish, ask_human]


def tool_catalog(profile: dict[str, Any], model: Any, executor: PublishExecutor, cycle_dir: Path | str) -> list[dict[str, str]]:
    """agent 工具清单（web-pages-batch T5，只读展示：名称+描述，不含闭包）。"""
    tools = build_default_tools(profile, model, executor, cycle_dir)
    return [{"name": t.name, "description": t.description} for t in tools]
