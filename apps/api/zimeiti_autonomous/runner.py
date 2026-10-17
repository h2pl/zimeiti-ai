"""流程执行器（autonomous-flow）：串行跑步骤，逐步落记录与产出，失败即停。

护栏（重试/熔断/成本上限/自主模式 HITL 放行）不在本变更——见 autonomous-guardrails。
本模块只保证「失败停在第 N 步、原因可见、不吞异常」。
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

from . import flows as fl
from .guardrails import AutonomyPolicy

_POLICY = AutonomyPolicy()
_LAST_ATTEMPTS: dict = {"n": 0}


def _retry(fn, tries: int) -> str:
    """步骤级重试（记录尝试次数；配置性错误不重试——见 guardrails.is_retryable）。"""
    from .guardrails import is_retryable

    last: BaseException | None = None
    for i in range(max(0, int(tries)) + 1):
        try:
            _LAST_ATTEMPTS["n"] = i + 1
            return fn()
        except Exception as e:  # noqa: BLE001
            last = e
            if not is_retryable(e) or i == int(tries):
                raise
    raise last if last else RuntimeError("重试逻辑异常")


AgentEntry = Callable[[str, str], str]

_agent_entry: AgentEntry | None = None


class EntryNotInjected(RuntimeError):
    """组装层未注入 agent 入口。"""


def set_agent_entry(fn: AgentEntry | None) -> None:
    """注入 agent 同步对话入口（app.py 组装层调用；None 用于测试隔离）。"""
    global _agent_entry
    _agent_entry = fn


def _require_entry() -> AgentEntry:
    if _agent_entry is None:
        raise EntryNotInjected(
            "agent 入口未注入（组装层需调用 zimeiti_autonomous.runner.set_agent_entry）"
        )
    return _agent_entry


def _archive(archive_root: Path, flow_id: str, idx: int, step: str, text: str) -> str:
    """逐步产出归档到 outputs/_automations/<flow_id>/NN-<step>.md。"""
    d = archive_root / flow_id
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{idx:02d}-{step}.md"
    p.write_text(text or "", encoding="utf-8")
    return str(p)


def run_flow(
    flow_id: str,
    name: str,
    steps: list[str],
    config: dict | None = None,
    archive_root: Path | None = None,
    record: Callable[[dict], None] | None = None,
) -> dict:
    """串行执行一条流程。

    - 每步：组装 prompt（带上一步摘要）→ 调注入入口 → 落产出文件与步骤记录
    - 失败即停：记录 failed_step 与 error，后续步骤不再执行
    - record 回调（可选）用于把结果落 PG（store 层注入，保持本模块无 PG 依赖）
    """
    entry = _require_entry()
    steps = fl.validate_steps(steps)
    cfg = config or {}
    root = Path(archive_root) if archive_root else Path(".")

    results: list[dict] = []
    prev_summary = ""
    failed_step = ""
    started = time.time()

    for i, step in enumerate(steps, start=1):
        t0 = time.time()
        rec: dict = {
            "step": step,
            "index": i,
            "status": "running",
            "duration_ms": 0,
            "output_path": "",
            "summary": "",
            "error": "",
            "retries": 0,
        }
        try:
            feedback = ""
            if step == "discover" and cfg.get("feedback", True):
                from .feedback import context_for_discover  # 局部导入：无数据时降级为空

                try:
                    feedback = context_for_discover()
                except Exception:  # noqa: BLE001   回流失败不阻断流程
                    feedback = ""
            prompt = fl.build_step_prompt(step, cfg, prev_summary, feedback=feedback)

            use_guard = bool(cfg.get("guardrails", True))
            tries = int(cfg.get("retry", 2)) if use_guard else 0
            attempts = 0

            # 默认参数绑定循环变量，避免闭包延迟绑定（ruff B023）
            def _call(_step: str = step, _prompt: str = prompt) -> str:
                return entry(f"flow-{flow_id}-{_step}", _prompt) or ""

            out = _call() if not use_guard else _retry(_call, tries)
            attempts = _LAST_ATTEMPTS.get("n", 0)
            rec["retries"] = max(0, attempts - 1)

            # 自主模式 HITL 策略：需人工确认的动作标 blocked（不阻塞，继续后续步骤）
            if use_guard and _POLICY.classify(out) == "blocked":
                rec["status"] = "blocked"
                rec["summary"] = fl.summarize(out)
                rec["output_path"] = _archive(root, flow_id, i, step, out)
                rec["needs_confirm"] = True
                prev_summary = rec["summary"]
                results.append(rec)
                continue
            rec["output_path"] = _archive(root, flow_id, i, step, out)
            rec["summary"] = fl.summarize(out)
            rec["status"] = "done"
            prev_summary = rec["summary"]
        except Exception as e:  # noqa: BLE001   失败即停，原因如实记录
            rec["status"] = "failed"
            rec["error"] = f"{type(e).__name__}: {e}"
            rec["retries"] = max(0, _LAST_ATTEMPTS.get("n", 1) - 1)
            rec["duration_ms"] = int((time.time() - t0) * 1000)
            results.append(rec)
            failed_step = step
            break
        rec["duration_ms"] = int((time.time() - t0) * 1000)
        results.append(rec)

    res = {
        "flow_id": flow_id,
        "name": name,
        "status": "failed" if failed_step else "done",
        "failed_step": failed_step,
        "steps": results,
        "duration_ms": int((time.time() - started) * 1000),
    }
    if record is not None:
        try:
            record(res)
        except Exception:  # noqa: BLE001   记录失败不掩盖执行结果
            pass
    return res
