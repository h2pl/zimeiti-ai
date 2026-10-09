"""运营数据 HTML 报告页：确定性生成自包含可视化报告。

设计来源（对标调研，非自创）：Easel `data-report`——数据读取、聚合、出图、
HTML 组装全部由脚本确定性完成，产出「KPI 卡 + 图表 + 数据表 + 洞察区」的
自包含 HTML（可离线打开）；模型只写洞察文字。

与 Easel 的差异：图表用内联 SVG 而非 matplotlib+base64（本项目图表类型简单：
趋势折线/柱状，零新增依赖）；数据源为 ops-metrics Postgres 而非 CSV。

CLI：uv run python -m zimeiti_api.ops_report_page [--platform xhs-main] [-o 输出路径]
"""

import argparse
import html
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from zimeiti_api.ops_metrics import MetricsDB, classify_lifecycle

_CSS = (
    "body{font-family:'Segoe UI','Microsoft YaHei',sans-serif;margin:0;"
    "background:#f5f6fa;color:#2d3436}"
    ".wrap{max-width:1080px;margin:0 auto;padding:24px}"
    "h1{font-size:22px}h2{font-size:16px;margin:28px 0 12px;"
    "border-left:4px solid #e84393;padding-left:8px}"
    ".kpis{display:flex;gap:12px;flex-wrap:wrap}"
    ".kpi{background:#fff;border-radius:10px;padding:14px 18px;"
    "box-shadow:0 1px 4px rgba(0,0,0,.08);min-width:130px}"
    ".kpi .v{font-size:24px;font-weight:700;color:#e84393}"
    ".kpi .k{font-size:12px;color:#636e72;margin-top:4px}"
    ".kpi .na{font-size:16px;color:#b2bec3}"
    "table{border-collapse:collapse;width:100%;background:#fff;"
    "box-shadow:0 1px 4px rgba(0,0,0,.06)}"
    "th,td{padding:8px 10px;border-bottom:1px solid #ecf0f1;font-size:13px;text-align:left}"
    "th{background:#f8f9fa}"
    ".status-failed{color:#d63031}.status-ok{color:#00b894}"
    ".meta{color:#636e72;font-size:12px;margin:6px 0 18px}"
    ".insight{background:#fff8e1;border-radius:10px;padding:14px 18px;font-size:13px}"
)

_KPI_XHS_ACCOUNT = ("粉丝数", "获赞与收藏")


def _esc(s: Any) -> str:
    return html.escape(str(s))


def _svg_line(series: list[dict], metric: str) -> str:
    """快照时序 → 内联 SVG 折线（数值与时间进 title，可悬停查看）。"""
    if len(series) < 2:
        return "<p class='na'>无数据（快照不足）</p>"
    w, h, pad = 420, 140, 18
    values = [s["value"] for s in series]
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1.0
    poly_pts = []
    circles = []
    for i, s in enumerate(series):
        x = pad + i * (w - 2 * pad) / (len(series) - 1)
        y = h - pad - (s["value"] - lo) / span * (h - 2 * pad)
        poly_pts.append(f"{x:.1f},{y:.1f}")
        label = _esc(f"{s['captured_at']} {s['value']:g}")
        circles.append(
            f"<circle cx='{x:.1f}' cy='{y:.1f}' r='3' fill='#e84393'>"
            f"<title>{label}</title></circle>"
        )
    polyline = (
        "<polyline points='"
        + ",".join(poly_pts)
        + "' fill='none' stroke='#e84393' stroke-width='2'/>"
    )
    return (
        f"<svg width='{w}' height='{h}' role='img' aria-label='{_esc(metric)} 趋势'>"
        f"{polyline}{''.join(circles)}</svg>"
        f"<div class='meta'>{_esc(metric)}：{lo:g} → {hi:g}</div>"
    )


def _svg_bars(counter: dict[str, int], title: str) -> str:
    """类别计数 → 内联 SVG 柱状图。"""
    if not counter:
        return "<p class='na'>无数据</p>"
    w, h, pad = 420, 140, 24
    items = sorted(counter.items(), key=lambda x: -x[1])
    n = len(items)
    bar_w = (w - 2 * pad) / max(n, 1)
    hi = max(v for _, v in items) or 1
    parts = []
    for i, (k, v) in enumerate(items):
        bh = v / hi * (h - 2 * pad)
        x = pad + i * bar_w
        parts.append(
            f"<rect x='{x:.1f}' y='{h - pad - bh:.1f}' width='{bar_w * 0.7:.1f}'"
            f" height='{bh:.1f}' fill='#0984e3'><title>{_esc(k)}: {v}</title></rect>"
            f"<text x='{x + bar_w * 0.35:.1f}' y='{h - pad + 14}' font-size='10'"
            f" text-anchor='middle'>{_esc(k)}</text>"
            f"<text x='{x + bar_w * 0.35:.1f}' y='{h - pad - bh - 4:.1f}' font-size='10'"
            f" text-anchor='middle'>{v}</text>"
        )
    return (
        f"<svg width='{w}' height='{h}' role='img' aria-label='{_esc(title)}'>"
        + "".join(parts)
        + "</svg>"
    )


def _kpi_card(label: str, value: Any) -> str:
    body = (
        f"<div class='v'>{_esc(value)}</div>"
        if value is not None
        else "<div class='na'>无数据</div>"
    )
    return f"<div class='kpi'>{body}<div class='k'>{_esc(label)}</div></div>"


def render_html_report(
    db: MetricsDB, platform: str | None = None, out_path: str | None = None
) -> str:
    """确定性生成自包含 HTML 报告页（只读；缺数据指标显示「无数据」）。"""
    events = db.list_events(platform)
    snaps = db.list_snapshots(platform)
    errors = db.list_errors(platform)

    # KPI：账号级最新指标（event_id 为空的快照，list 按 captured_at 排序后写覆盖）
    account: dict[str, float] = {}
    for s in snaps:
        if s["event_id"] is None:
            account[s["metric"]] = s["value"]
    kpis = [
        _kpi_card("粉丝数", account.get("粉丝数")),
        _kpi_card("获赞与收藏", account.get("获赞与收藏")),
        _kpi_card("发布事件", len(events)),
        _kpi_card("指标快照", len(snaps)),
    ]

    # 生命周期分布（单篇 read 序列判定）
    dist: dict[str, int] = {}
    for eid in {e["id"] for e in events}:
        series = [s["value"] for s in snaps if s["event_id"] == eid and s["metric"] == "read"]
        kind = classify_lifecycle(series)
        dist[kind] = dist.get(kind, 0) + 1

    # 趋势图：按 metric 分组（≥2 点才有折线）
    by_metric: dict[str, list[dict]] = {}
    for s in snaps:
        by_metric.setdefault(s["metric"], []).append(s)

    def _trend_div(metric: str, series: list[dict]) -> str:
        ordered = sorted(series, key=lambda x: x["captured_at"])
        return f"<div style='margin-bottom:16px'>{_svg_line(ordered, metric)}</div>"

    trend_parts = [_trend_div(k, v) for k, v in sorted(by_metric.items()) if len(v) >= 2]
    trend_html = "".join(trend_parts) or "<p class='na'>无数据（快照不足）</p>"

    # 发布节奏（按星期）
    rhythm: dict[str, int] = {}
    weekday_zh = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    for e in events:
        day = weekday_zh[datetime.fromisoformat(e["publish_date"]).weekday()]
        rhythm[day] = rhythm.get(day, 0) + 1

    rows = []
    for e in events:
        rows.append(
            f"<tr><td>{_esc(e['platform'])}</td><td>{_esc(e['title'])}</td>"
            f"<td>{_esc(e['publish_date'])}</td>"
            f"<td class='status-{_esc(e['status'])}'>{_esc(e['status'])}</td>"
            f"<td>{_esc(e['profile'])}</td><td>{_esc(e['topic_direction'])}</td></tr>"
        )

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    plat = _esc(platform or "全部平台")
    doc = (
        f"<!DOCTYPE html>\n<html lang='zh-CN'><head><meta charset='utf-8'>"
        f"<title>运营数据报告 - {plat}</title><style>{_CSS}</style></head>"
        f"<body><div class='wrap'>"
        f"<h1>运营数据报告 · {plat}</h1>"
        f"<div class='meta'>生成时间 {now} ｜ 采集错误 {len(errors)} 条</div>"
        f"<h2>KPI</h2><div class='kpis'>{''.join(kpis)}</div>"
        f"<h2>生命周期分布</h2>{_svg_bars(dist, '内容生命周期')}"
        f"<h2>指标趋势</h2>{trend_html}"
        f"<h2>发布节奏</h2>{_svg_bars(rhythm, '发布节奏')}"
        f"<h2>发布事件</h2>"
        f"<table><tr><th>平台</th><th>标题</th><th>发布日</th><th>状态</th>"
        f"<th>画像</th><th>选题方向</th></tr>{''.join(rows)}</table>"
        f"<h2>洞察区（待 Agent 校准报告）</h2>"
        f"<div class='insight'>确定性关键发现与策略建议见校准评估报告"
        f"（data/metrics/evals/）。本区域由托管循环的 Agent 回读校准报告与"
        f"内容原文后填写。</div>"
        f"</div></body></html>"
    )
    if out_path:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text(doc, encoding="utf-8")
    return doc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="运营数据 HTML 报告页（确定性生成）")
    parser.add_argument("--platform", default=None)
    parser.add_argument("-o", "--out", default=None, help="输出 HTML 路径")
    args = parser.parse_args(argv)

    db = MetricsDB()
    doc = render_html_report(db, platform=args.platform)
    if args.out:
        out = args.out
    else:
        from zimeiti_api.config import DATA_DIR

        date_tag = datetime.now().strftime("%Y-%m-%d")
        out = str(Path(DATA_DIR) / "metrics" / f"report-{args.platform or 'all'}-{date_tag}.html")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(doc, encoding="utf-8")
    print(json.dumps({"report": out}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
