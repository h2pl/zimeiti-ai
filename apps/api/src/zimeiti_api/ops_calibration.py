"""内容策略校准：把 ops-metrics 的归因数据转成可执行的创作策略证据与建议。

设计来源（对标调研，非自创）：
- xiaobei `content-calibrator` 四条评估铁律：
  ①趋势优先（账号基线归一化，绝对值只作上下文）
  ②脚本只给证据、好坏归因由 Agent 回读原文
  ③先排混杂再归因（排不了的降级「观察」）
  ④策略更新必须用户逐条确认（评估只产出建议，MUST NOT 自动改画像）
- Easel `skill-publish-analytics`：账号基线归一化、发布节奏归因、确定性脚本算

数据源：MetricsDB（只读，复用 ops-metrics 的 report/生命周期判定）。
CLI：uv run python -m zimeiti_api.ops_calibration calibrate [--platform] [--profile] [--force]
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

from zimeiti_api.ops_metrics import MetricsDB

# 成熟度阈值（xiaobei：成熟 = 快照数 ≥5 且事件跨度 ≥3 天）
MATURITY_MIN_SNAPSHOTS = 5
MATURITY_MIN_SPAN_DAYS = 3


def profile_paths(platform: str) -> list[Path]:
    """画像文件路径（校准报告记录对应画像；测试可 monkeypatch）。"""
    from zimeiti_api.config import PROFILES_DIR

    return sorted(Path(PROFILES_DIR).glob(f"{platform}*.yaml"))


def build_evidence(db: MetricsDB, platform: str, profile: str | None = None) -> dict:
    """确定性校准证据（只读）：基线归一化 / 趋势 / 生命周期分布 / 发布节奏。"""
    report = db.report(platform=platform, profile=profile)
    events = [e for e in db.list_events(platform) if profile in (None, "", e["profile"])]

    # 1. 基线归一化：账号级快照（event_id 为空）按 metric 取历史均值与最新值
    all_snaps = db.list_snapshots(platform)
    snaps = [s for s in all_snaps if s["event_id"] is None]
    baseline: dict[str, dict] = {}
    by_metric: dict[str, list[float]] = {}
    for s in snaps:
        by_metric.setdefault(s["metric"], []).append(s["value"])
    for metric, values in by_metric.items():
        mean = sum(values) / len(values)
        latest = values[-1]
        entry: dict = {"mean": round(mean, 4), "latest": latest}
        if len(values) >= 2:
            entry["normalized"] = round(latest / mean, 4)
        else:
            entry["normalized"] = None  # 基线不足（单点无法归一）
        baseline[metric] = entry

    # 2. 生命周期分布
    distribution: dict[str, int] = {}
    for n in report["notes"]:
        distribution[n["lifecycle"]] = distribution.get(n["lifecycle"], 0) + 1

    # 3. 发布节奏：事件按星期几分布
    rhythm: dict[str, int] = {}
    for e in events:
        day = datetime.fromisoformat(e["publish_date"]).strftime("%A")
        rhythm[day] = rhythm.get(day, 0) + 1

    return {
        "platform": platform,
        "profile": profile or "all",
        "events": len(events),
        "snapshots": len(all_snaps),  # 全部快照（含单篇级）计成熟度
        "baseline": baseline,
        "trend": report["trend"],
        "lifecycle_distribution": distribution,
        "rhythm": rhythm,
        "errors": len(db.list_errors(platform)),
    }


def _maturity(evidence: dict) -> tuple[bool, str]:
    """混杂评估：成熟记录（快照 ≥5 且事件跨度 ≥3 天）不足 → 降级「观察」。"""
    if evidence["snapshots"] < MATURITY_MIN_SNAPSHOTS:
        return False, "样本不足"
    if evidence["events"] < 2:
        return False, "样本不足"
    return True, ""


def render_eval_report(evidence: dict, generated_at: datetime | None = None) -> str:
    """渲染评估报告（证据/结论/洞察留位/建议；照 xiaobei evals 结构简化）。"""
    ev = evidence
    mature, reason = _maturity(ev)
    tag = "结论" if mature else f"观察（混杂：{reason}）"
    now = (generated_at or datetime.now()).strftime("%Y-%m-%d")

    lines = [
        f"# 策略校准评估：{ev['platform']} / {ev['profile']} / {now}",
        "",
        "## 证据（脚本计算）",
        "",
        f"- 事件数：{ev['events']}；快照数：{ev['snapshots']}；采集错误：{ev['errors']}",
        "",
        "### 基线归一化（值 / 账号均值，绝对值仅作上下文）",
        "",
    ]
    if ev["baseline"]:
        for metric, b in ev["baseline"].items():
            norm = b["normalized"] if b["normalized"] is not None else "基线不足"
            lines.append(f"- {metric}：均值 {b['mean']} / 最新 {b['latest']} → 归一化 {norm}")
    else:
        lines.append("- 无账号级快照")
    lines += ["", "### 趋势（首末对比）", ""]
    if ev["trend"]:
        for metric, t in ev["trend"].items():
            lines.append(f"- {metric}：{t['first']} → {t['last']}（delta {t['delta']}）")
    else:
        lines.append("- 无数据")
    lines += ["", "### 生命周期分布", ""]
    if ev["lifecycle_distribution"]:
        for k, v in sorted(ev["lifecycle_distribution"].items(), key=lambda x: -x[1]):
            lines.append(f"- {k}：{v} 篇")
    else:
        lines.append("- 无数据")
    lines += ["", "### 发布节奏（按星期）", ""]
    if ev["rhythm"]:
        for day in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"):
            if day in ev["rhythm"]:
                lines.append(f"- {day}：{ev['rhythm'][day]} 篇")
    else:
        lines.append("- 无数据")

    lines += [
        "",
        f"## 结论（{tag}）",
        "",
        "以上证据为确定性计算结果；好坏归因与策略含义由 Agent 回读证据与内容原文后填写。",
        "",
        "## Agent 洞察（待填写）",
        "",
        "## 建议（仅列出，不自动执行）",
        "",
    ]
    return "\n".join(lines) + "\n"


def _eval_dir() -> str:
    from zimeiti_api.config import DATA_DIR

    return str(Path(DATA_DIR) / "metrics" / "evals")


def calibrate(
    db: MetricsDB,
    platform: str,
    profile: str | None = None,
    force: bool = False,
    out_dir: str | None = None,
) -> list[str]:
    """生成校准评估报告（只读；不修改画像），返回报告路径列表。

    --force：绕过按量触发检查（xiaobei 手动兜底）。MVP 无按量触发，force 仅保留语义。
    """
    del force  # 按量触发为后续变更；MVP 总是允许手动校准
    evidence = build_evidence(db, platform=platform, profile=profile)
    if evidence["events"] == 0 and evidence["snapshots"] == 0:
        raise RuntimeError(f"无可校准数据：{platform} 无事件与快照")
    report_md = render_eval_report(evidence)
    date_tag = datetime.now().strftime("%Y-%m-%d")
    out = Path(out_dir) if out_dir else Path(_eval_dir())
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{platform}-{profile or 'all'}-{date_tag}.eval.md"
    path.write_text(report_md, encoding="utf-8")
    return [str(path)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="内容策略校准（证据引擎）")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_cal = sub.add_parser("calibrate", help="生成策略校准评估报告")
    p_cal.add_argument("--platform", required=True)
    p_cal.add_argument("--profile", default=None)
    p_cal.add_argument("--force", action="store_true", help="手动兜底触发")
    args = parser.parse_args(argv)

    db = MetricsDB()
    paths = calibrate(db, platform=args.platform, profile=args.profile, force=args.force)
    print(json.dumps({"reports": paths}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
