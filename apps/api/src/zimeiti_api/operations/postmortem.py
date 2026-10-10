"""单篇复盘与爆款规律提炼（P1⑨）。

参考: Easel skill-content-postmortem——模式 A 单条内容多维拆解成败（含「同期
对照」基线比较）；模式 B ≥5 条内容提炼可复制公式。铁律：脚本只给确定性证据，
结论仅报告，不自动改画像/策略（对齐 xiaobei content-calibrator）。

用法：
  uv run python -m zimeiti_api.operations.postmortem note --platform xhs-main --title "标题"
  uv run python -m zimeiti_api.operations.postmortem formula --platform xhs-main [--top 3]
输出 markdown（落盘 data/metrics/postmortems/）。
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from zimeiti_api.operations.metrics import MetricsDB, classify_lifecycle


def _out_dir() -> Path:
    from zimeiti_api.config import DATA_DIR

    return Path(DATA_DIR) / "metrics" / "postmortems"


def note_evidence(db: MetricsDB, platform: str, title: str) -> dict[str, Any] | None:
    """单篇确定性证据：发布信息 + read 快照序列 + 生命周期 + 同期对照。"""
    events = [e for e in db.list_events(platform) if e["title"] == title]
    if not events:
        return None
    event = events[0]
    snaps = [
        s
        for s in db.list_snapshots(platform)
        if s.get("event_id") == event["id"] and s["metric"] == "read"
    ]
    snaps.sort(key=lambda s: s["captured_at"])
    series = [s["value"] for s in snaps]
    # 同期对照：该账号其他单篇的终值（基线比较，xiaobei 基线归一化思路的单篇版）
    peers = {}
    for e2 in db.list_events(platform):
        if e2["id"] == event["id"]:
            continue
        vals = [
            s["value"]
            for s in db.list_snapshots(platform)
            if s.get("event_id") == e2["id"] and s["metric"] == "read"
        ]
        if vals:
            peers[e2["title"]] = max(vals)
    peer_mean = round(sum(peers.values()) / len(peers), 1) if peers else None
    return {
        "platform": platform,
        "title": title,
        "publish_date": event["publish_date"],
        "profile": event.get("profile", ""),
        "topic_direction": event.get("topic_direction", ""),
        "read_series": series,
        "read_latest": series[-1] if series else None,
        "lifecycle": classify_lifecycle(series) if len(series) >= 2 else "数据不足",
        "peer_mean": peer_mean,
        "vs_peers": (round(series[-1] / peer_mean, 2) if series and peer_mean else None),
        "notes_count": len(peers) + 1,
    }


def render_note(evidence: dict[str, Any]) -> str:
    lines = [f"# 单篇复盘：{evidence['title']}", ""]
    lines.append(f"- 平台/日期：{evidence['platform']} / {evidence['publish_date']}")
    lines.append(f"- 选题方向：{evidence['topic_direction'] or '未记录'}")
    lines.append(f"- read 序列：{evidence['read_series'] or '无快照'}")
    lines.append(f"- 生命周期：{evidence['lifecycle']}")
    if evidence["vs_peers"] is not None:
        rel = "高于" if evidence["vs_peers"] >= 1 else "低于"
        lines.append(
            f"- 同期对照：终值 {evidence['read_latest']} / 其他 {evidence['notes_count'] - 1}"
            f" 篇均值 {evidence['peer_mean']} → {rel}均值 {evidence['vs_peers']}x"
        )
    else:
        lines.append("- 同期对照：样本不足（需同账号 ≥2 篇有 read 快照）")
    lines += [
        "",
        "## 局限性",
        "",
        "- 关联性不等于因果性——本报告只呈现确定性证据，成败归因需人工结合内容判断",
        f"- 样本：{evidence['notes_count']} 篇（同账号），对照基线可能受样本量影响",
        "",
    ]
    return "\n".join(lines)


def top_formula(db: MetricsDB, platform: str, top: int = 3) -> dict[str, Any]:
    """爆款规律提炼的证据面：按 read 终值排名 + 各篇选题方向/生命周期。"""
    ranked = []
    for e in db.list_events(platform):
        vals = [
            s["value"]
            for s in db.list_snapshots(platform)
            if s.get("event_id") == e["id"] and s["metric"] == "read"
        ]
        ranked.append(
            {
                "title": e["title"],
                "publish_date": e["publish_date"],
                "topic_direction": e.get("topic_direction", ""),
                "read_latest": max(vals) if vals else None,
                "lifecycle": classify_lifecycle(vals) if len(vals) >= 2 else "数据不足",
            }
        )
    ranked = [r for r in ranked if r["read_latest"] is not None]
    ranked.sort(key=lambda r: r["read_latest"], reverse=True)
    return {"platform": platform, "sample": len(ranked), "top": ranked[:top]}


def render_formula(ev: dict[str, Any]) -> str:
    lines = [f"# 爆款规律提炼（{ev['platform']}，样本 {ev['sample']} 篇）", ""]
    if ev["sample"] < 5:
        lines.append(f"> 样本 {ev['sample']} < 5：规律可信度低，仅作记录（Easel 阈值）。")
    for i, r in enumerate(ev["top"], 1):
        lines.append(
            f"{i}. 《{r['title']}》read={r['read_latest']}（{r['lifecycle']}，"
            f"{r['publish_date']}）方向：{r['topic_direction'] or '未记录'}"
        )
    lines += [
        "",
        "## 局限性",
        "",
        "- 提炼的是相关性证据；是否可复制需人工判断并经下一轮发布验证",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    parser = argparse.ArgumentParser(description="单篇复盘/爆款规律（确定性证据）")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_note = sub.add_parser("note", help="单篇复盘")
    p_note.add_argument("--platform", required=True)
    p_note.add_argument("--title", required=True)
    p_form = sub.add_parser("formula", help="爆款规律提炼")
    p_form.add_argument("--platform", required=True)
    p_form.add_argument("--top", type=int, default=3)
    args = parser.parse_args(argv)

    db = MetricsDB()
    if args.cmd == "note":
        ev = note_evidence(db, args.platform, args.title)
        if ev is None:
            print(json.dumps({"error": f"未找到事件：{args.title}"}, ensure_ascii=False))
            return 1
        md = render_note(ev)
    else:
        md = render_formula(top_formula(db, args.platform, args.top))
    out = _out_dir()
    out.mkdir(parents=True, exist_ok=True)
    tag = datetime.now().strftime("%Y-%m-%d")
    path = out / f"{args.platform}-{args.cmd}-{tag}.md"
    path.write_text(md, encoding="utf-8")
    print(json.dumps({"report": str(path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
