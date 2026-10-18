"""zimeiti 命令行入口：chat / flows / runs / usage。

退出码契约（design D5）：0=成功；1=API 错误（含连接失败）；2=用法错误。
所有输出走 UTF-8（Windows GBK 终端保护）。
"""

from __future__ import annotations

import argparse
import os
import sys

from . import client as cl

_STEP_LABEL = {
    "discover": "发现",
    "plan": "选题",
    "produce": "创作",
    "publish": "发布",
    "review": "复盘",
}
_STEP_STATUS = {
    "done": "完成",
    "blocked": "待确认",
    "failed": "失败",
    "running": "进行中",
}


def _reconfigure_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except Exception:  # noqa: BLE001   老 Python/重定向场景降级
            pass


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="zimeiti",
        description="zimeiti 命令行入口（连接已有后端；模型凭据留在服务端）",
    )
    p.add_argument(
        "--base",
        default=os.environ.get("ZIMEITI_API") or cl.DEFAULT_BASE,
        help="后端地址（默认 %(default)s，可用 ZIMEITI_API 覆盖）",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    # 公共父解析器：--base 在子命令前后都能写（`zimeiti runs --base X` 曾报
    # unrecognized arguments——argparse 全局参数必须在子命令前，体验差）。
    # default=SUPPRESS：子命令未指定时不覆盖顶层已解析的值。
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--base", default=argparse.SUPPRESS, help=argparse.SUPPRESS)

    c = sub.add_parser("chat", parents=[common], help="对话一句（流式输出）")
    c.add_argument("message", help="要发送的消息")
    c.add_argument("--session", default="", help="会话 id（默认服务端新建）")
    c.add_argument("--timeout", type=float, default=600.0, help="流读取超时（秒）")

    f = sub.add_parser("flows", parents=[common], help="运营流程：列表 / 新建 / 立即执行")
    fsub = f.add_subparsers(dest="action")
    fsub.add_parser("list", help="列出流程")
    fn = fsub.add_parser("new", help="新建流程")
    fn.add_argument("--name", required=True, help="流程名称")
    fn.add_argument(
        "--steps",
        default="discover,plan",
        help="步骤子集，逗号分隔（discover/plan/produce/publish/review）",
    )
    fn.add_argument("--schedule", default="", help="每日时刻 HH:MM（留空=仅手动）")
    fn.add_argument("--topic", default="", help="主题/方向")
    fr = fsub.add_parser("run", help="立即执行一次（会真实消耗模型额度）")
    fr.add_argument("id", help="流程 id")

    r = sub.add_parser("runs", parents=[common], help="执行记录（含逐步明细）")
    r.add_argument("--flow", default="", help="只看某流程")
    r.add_argument("--limit", type=int, default=10, help="条数（默认 10）")

    sub.add_parser("usage", parents=[common], help="用量与折算金额")
    return p


def _fmt_ms(ms: int) -> str:
    s = max(0, round((ms or 0) / 1000))
    return f"{s // 60}分{s % 60}秒" if s >= 60 else f"{s}秒"


def _cmd_flows(args) -> int:
    if args.action in (None, "list"):
        data = cl.get(args.base, "/api/flows")
        rows = data.get("flows", [])
        if not rows:
            print("（没有流程）")
            return 0
        for f in rows:
            steps = " ".join(_STEP_LABEL.get(s, s) for s in f.get("steps", []))
            state = "启用" if f.get("enabled") else "已停用"
            print(f"{f['id']}  {f['name']}  [{steps}]  每天 {f.get('schedule') or '—'}  {state}")
        return 0
    if args.action == "new":
        picked = [s.strip() for s in args.steps.split(",") if s.strip()]
        cfg: dict = {"draft_only": True}
        if args.topic.strip():
            cfg["topic"] = args.topic.strip()
        out = cl.post(
            args.base,
            "/api/flows",
            {"name": args.name, "steps": picked, "schedule": args.schedule, "config": cfg},
        )
        print(f"已创建：{out.get('id')}（步骤 {' '.join(_STEP_LABEL.get(s, s) for s in picked)}）")
        return 0
    if args.action == "run":
        res = cl.post(args.base, f"/api/flows/{args.id}/run", timeout=1800.0)
        print(f"执行结果：{res.get('status')}（{_fmt_ms(res.get('duration_ms', 0))}）")
        for s in res.get("steps", []):
            label = _STEP_LABEL.get(s.get("step"), s.get("step"))
            status = _STEP_STATUS.get(s.get("status"), s.get("status"))
            line = f"  {label}：{status}"
            if s.get("error"):
                line += f"（{s['error'][:120]}）"
            print(line)
        if res.get("failed_step"):
            print(f"失败步骤：{_STEP_LABEL.get(res['failed_step'], res['failed_step'])}")
        return 0 if res.get("status") == "done" else 1
    return 2


def _cmd_runs(args) -> int:
    q = f"?limit={args.limit}"
    if args.flow:
        q += f"&flow_id={args.flow}"
    data = cl.get(args.base, f"/api/flows/runs{q}")
    rows = data.get("runs", [])
    if not rows:
        print("（暂无执行记录）")
        return 0
    for r in rows:
        head = (
            f"{r.get('started') or 0}  {r.get('status')}  {_fmt_ms(r.get('duration_ms', 0))}"
            f"  flow={r.get('flow_id')}"
        )
        print(head)
        for s in r.get("steps", []):
            print(
                f"    {_STEP_LABEL.get(s.get('step'), s.get('step'))}"
                f"：{_STEP_STATUS.get(s.get('status'), s.get('status'))}"
            )
    return 0


def _cmd_usage(args) -> int:
    data = cl.get(args.base, "/api/usage")
    totals = data.get("totals") or data
    tokens = totals.get("total_tokens")
    cost = totals.get("cost_usd")
    partial = "（部分未折算）" if totals.get("cost_usd_partial") else ""
    print(f"总 tokens：{tokens if tokens is not None else '未知'}")
    cost_text = f"${cost:.4f}" if isinstance(cost, (int, float)) else "未折算"
    print(f"折算金额：{cost_text}{partial}")
    return 0


def _cmd_chat(args) -> int:
    got = False
    try:
        for event, text in cl.sse_chat(args.base, args.message, args.session, args.timeout):
            got = True
            if event == "token":
                print(text, end="", flush=True)
            elif event == "error":
                print(f"\n[错误] {text}", file=sys.stderr)
                return 1
            elif event == "activity":
                print(f"\r[进度] {text[:80]}", file=sys.stderr, flush=True)
    except cl.ApiError as e:
        print(f"\n[错误] {e}", file=sys.stderr)
        return 1
    if got:
        print()
    return 0


def main(argv: list[str] | None = None) -> int:
    _reconfigure_utf8()
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "chat":
            return _cmd_chat(args)
        if args.cmd == "flows":
            return _cmd_flows(args)
        if args.cmd == "runs":
            return _cmd_runs(args)
        if args.cmd == "usage":
            return _cmd_usage(args)
    except cl.ApiError as e:
        print(f"[错误] {e}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
