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

from zimeiti_api import audit
from zimeiti_api.compliance import ComplianceGate
from zimeiti_api.creation import create_drafts as _create_drafts
from zimeiti_api.publisher import PublishExecutor
from zimeiti_api.topics import discover_topics as _discover_topics
from zimeiti_api.topics import select_topic as _select_topic

logger = logging.getLogger(__name__)

publish_calls: list[str] = []  # 兼容观测口（真实发布时记录）


def default_platform_call(draft: dict) -> str:
    """平台调用钩子：默认占位（MVP），真实平台脚本 8.2 替换；测试可 monkeypatch 观测。"""
    return "submitted"


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
) -> list:
    """按账号画像构建工具集。

    cycle_dir：本轮变更的会话目录（跨进程共享状态）；
    output_root：草稿/产物根目录（默认 outputs/，测试可用环境变量重定向）。
    """
    account = profile["account"]
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
            result = executor.publish(
                account,
                drafts["xhs"],
                platform_call=default_platform_call,
                credentials_sealed=_account_credentials(),
            )
        except Exception as exc:
            audit.record("publish_failed", account=account, error=str(exc))
            return f"发布被护栏拒绝：{exc}"
        publish_calls.append(state["selected"]["title"])
        audit.record("published", account=account, outcome=result["readback"])
        return f"发布结果：{result}"

    return [discover_topics, select_topic, create_drafts, publish]
