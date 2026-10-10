"""运营数据：发布事件 + 指标快照 + 只读归因（SQLite）。

设计来源（对标调研，非自创）：
- xiaobei `published-track`：SQLite 单库按平台分表、发布记录 upsert（去重键
  source_folder+publish_date）、采集失败留痕
- Easel 数据三层：发布事件与时序快照**分离表存储**（单一事实来源）、消费层
  **只读不回写**、确定性脚本聚合（模型只写洞察）、内容生命周期分类

数据落盘：项目 Postgres（DATABASE_URL）
CLI：uv run python -m zimeiti_api.operations.metrics {record|pull|report}
"""

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import psycopg

# xhs 创作者中心数据看板的指标标签（页面文本为「标签 | 值」相邻对）
XHS_DASHBOARD_LABELS = (
    "关注数",
    "粉丝数",
    "获赞与收藏",
    "曝光数",
    "观看数",
    "点赞数",
    "评论数",
    "收藏数",
    "分享数",
    "净涨粉",
    "新增关注",
    "取消关注",
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS publish_events (
    id SERIAL PRIMARY KEY,
    platform TEXT NOT NULL,
    title TEXT,
    content_type TEXT DEFAULT '',
    source_folder TEXT NOT NULL,
    publish_date TEXT NOT NULL,
    publish_url TEXT DEFAULT '',
    profile TEXT DEFAULT '',
    topic_direction TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'ok',
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(platform, source_folder, publish_date)
);
CREATE TABLE IF NOT EXISTS metric_snapshots (
    id SERIAL PRIMARY KEY,
    event_id INTEGER,
    platform TEXT NOT NULL,
    metric TEXT NOT NULL,
    value REAL NOT NULL,
    source TEXT NOT NULL,
    captured_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS collection_errors (
    id SERIAL PRIMARY KEY,
    platform TEXT NOT NULL,
    scope TEXT NOT NULL,
    error TEXT NOT NULL,
    occurred_at TEXT NOT NULL
);
"""


class MetricsDB:
    """SQLite 运营数据层（事件 upsert + 快照 + 失败留痕 + 只读归因）。"""

    def __init__(self, dsn: str | None = None):
        """连接项目 Postgres（默认 config.DATABASE_URL；测试可传带 search_path 的 dsn）。"""
        if dsn is None:
            from zimeiti_api.config import DATABASE_URL

            dsn = DATABASE_URL
        self.dsn = dsn
        self.setup()

    def setup(self) -> None:
        """幂等建表（对齐 checkpoints.py 的 saver.setup() 惯例）。"""
        with self._conn() as conn:
            conn.execute(SCHEMA)
            conn.commit()

    def _conn(self):
        """连接 PG（dict_row：行以字段名访问，便于读取侧直接转 dict）。"""
        return psycopg.connect(self.dsn, row_factory=psycopg.rows.dict_row)

    # ─── 写入侧 ────────────────────────────────────────────────────

    def record_event(
        self,
        platform: str,
        title: str,
        source_folder: str,
        publish_date: str,
        profile: str = "",
        topic_direction: str = "",
        status: str = "ok",
        notes: str = "",
        publish_url: str = "",
        content_type: str = "",
    ) -> int:
        """记录发布事件；同 platform+source_folder+publish_date 时更新既有行（xiaobei upsert）。"""
        now = datetime.now().isoformat(timespec="seconds")
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO publish_events
                    (platform, title, content_type, source_folder, publish_date,
                     publish_url, profile, topic_direction, status, notes,
                     created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(platform, source_folder, publish_date) DO UPDATE SET
                    title=excluded.title,
                    content_type=excluded.content_type,
                    publish_url=excluded.publish_url,
                    profile=excluded.profile,
                    topic_direction=excluded.topic_direction,
                    status=excluded.status,
                    notes=excluded.notes,
                    updated_at=excluded.updated_at
                """,
                (
                    platform,
                    title,
                    content_type,
                    source_folder,
                    publish_date,
                    publish_url,
                    profile,
                    topic_direction,
                    status,
                    notes,
                    now,
                    now,
                ),
            )
            row = conn.execute(
                "SELECT id FROM publish_events"
                " WHERE platform=%s AND source_folder=%s AND publish_date=%s",
                (platform, source_folder, publish_date),
            ).fetchone()
            conn.commit()
            return int(row["id"])

    def record_snapshot(
        self,
        event_id: int | None,
        platform: str,
        metric: str,
        value: float,
        source: str,
        captured_at: str | None = None,
    ) -> int:
        """写入指标快照（账号级指标 event_id 可为 None；captured_at 可注入便于测试）。"""
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO metric_snapshots"
                " (event_id, platform, metric, value, source, captured_at)"
                " VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                (
                    event_id,
                    platform,
                    metric,
                    value,
                    source,
                    captured_at or datetime.now().isoformat(timespec="seconds"),
                ),
            )
            conn.commit()
            return int(cur.fetchone()["id"])

    def record_error(self, platform: str, scope: str, error: str) -> int:
        """采集失败留痕（不写零值覆盖历史，spec 要求）。"""
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO collection_errors (platform, scope, error, occurred_at)"
                " VALUES (%s, %s, %s, %s) RETURNING id",
                (platform, scope, str(error)[:500], datetime.now().isoformat(timespec="seconds")),
            )
            conn.commit()
            return int(cur.fetchone()["id"])

            # ─── 读取侧 ────────────────────────────────────────────────────

    def list_events(self, platform: str | None = None) -> list[dict]:
        with self._conn() as conn:
            if platform:
                rows = conn.execute(
                    "SELECT * FROM publish_events WHERE platform=%s ORDER BY publish_date DESC",
                    (platform,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM publish_events ORDER BY publish_date DESC"
                ).fetchall()
            return [dict(r) for r in rows]

    def list_snapshots(self, platform: str | None = None) -> list[dict]:
        with self._conn() as conn:
            if platform:
                rows = conn.execute(
                    "SELECT * FROM metric_snapshots WHERE platform=%s ORDER BY captured_at",
                    (platform,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM metric_snapshots ORDER BY captured_at"
                ).fetchall()
            return [dict(r) for r in rows]

    def list_errors(self, platform: str | None = None) -> list[dict]:
        with self._conn() as conn:
            if platform:
                rows = conn.execute(
                    "SELECT * FROM collection_errors WHERE platform=%s ORDER BY occurred_at DESC",
                    (platform,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM collection_errors ORDER BY occurred_at DESC"
                ).fetchall()
            return [dict(r) for r in rows]

    def report(self, platform: str | None = None, profile: str | None = None) -> dict:
        """只读归因：趋势 + 内容生命周期判定（确定性规则，不回写）。"""
        with self._conn() as conn:
            events = [
                dict(r)
                for r in conn.execute(
                    "SELECT * FROM publish_events ORDER BY publish_date"
                ).fetchall()
            ]
            snaps = [
                dict(r)
                for r in conn.execute(
                    "SELECT * FROM metric_snapshots ORDER BY captured_at"
                ).fetchall()
            ]
        if platform:
            events = [e for e in events if e["platform"] == platform]
            snaps = [s for s in snaps if s["platform"] == platform]
        if profile:
            events = [e for e in events if e["profile"] == profile]

        # 趋势：每个 metric 的首末值与增量
        trend: dict[str, dict] = {}
        for s in snaps:
            t = trend.setdefault(
                s["metric"], {"first": s["value"], "last": s["value"], "delta": 0.0}
            )
            t["last"] = s["value"]
            t["delta"] = round(t["last"] - t["first"], 4)

        # 内容生命周期：按 event 的 read 序列判定
        notes = []
        for e in events:
            series = [
                s["value"] for s in snaps if s["event_id"] == e["id"] and s["metric"] == "read"
            ]
            notes.append(
                {
                    "event_id": e["id"],
                    "title": e["title"],
                    "platform": e["platform"],
                    "publish_date": e["publish_date"],
                    "lifecycle": classify_lifecycle(series),
                }
            )
        return {
            "platform": platform or "all",
            "profile": profile or "all",
            "events": len(events),
            "snapshots": len(snaps),
            "trend": trend,
            "notes": notes,
            "errors": len(self.list_errors(platform)) if platform else len(self.list_errors()),
        }


def classify_lifecycle(series: list[float]) -> str:
    """内容生命周期判定（确定性规则，来源：Easel 内容生命周期分类思路）。

    - 数据不足：<2 个采样点
    - 速爆型：首点已占终值 ≥80%，且后续增量 <10%
    - 稳增型：终值/首值 ≥1.5
    - 长尾型：其余
    """
    if len(series) < 2:
        return "数据不足"
    first, last = series[0], series[-1]
    if last <= 0:
        return "长尾型"
    if first / last >= 0.8 and (last - first) / last < 0.1:
        return "速爆型"
    if last / max(first, 1e-9) >= 1.5:
        return "稳增型"
    return "长尾型"


# ─── 解析（纯函数，便于单测） ────────────────────────────────────────────


def parse_gzh_datacube(raw: dict) -> dict[str, float]:
    """解析公众号 datacube 响应（{"list":[{ref_date,...}]}）→ 数值指标（去掉日期字段）。"""
    if not raw:
        return {}
    items = raw.get("list") or []
    if not items:
        return {}
    latest = items[-1]
    out: dict[str, float] = {}
    for k, v in latest.items():
        if k in ("ref_date",):
            continue
        if isinstance(v, (int, float)):
            out[k] = float(v)
    return out


def _numeric(token: str) -> float | None:
    """解析数值 token；非数值（如「环比-」）返回 None（不写零，零假阳性）。"""
    if not token:
        return None
    try:
        return float(token.rstrip("%").replace(",", ""))
    except ValueError:
        return None


def parse_xhs_dashboard(body_text: str) -> dict[str, float]:
    """解析创作者中心首页数据看板文本 → 指标。

    实测两种排版并存（A3 真账号走查，否则指标会错位一位）：
    - 账号概览区：值在前、标签在后 →「6 | 关注数 | 212 | 粉丝数 | 5281 | 获赞与收藏」
    - 笔记数据总览区：标签在前、值在后 →「曝光数 | 0 | 环比- | 观看数 | 0」

    以「笔记数据总览」为界分区解析；缺失或非数值不写零。
    """
    if not body_text:
        return {}
    # 页面文本统一按分隔符切分（真实页面换行/竖线混排）
    tokens = [t.strip() for t in body_text.replace("\n", "|").split("|") if t.strip()]
    boundary = next((i for i, t in enumerate(tokens) if "笔记数据总览" in t), None)
    out: dict[str, float] = {}
    for i, tok in enumerate(tokens):
        if tok not in XHS_DASHBOARD_LABELS:
            continue
        if boundary is not None and i < boundary:
            value = _numeric(tokens[i - 1]) if i > 0 else None  # 值在前
        else:
            value = _numeric(tokens[i + 1]) if i + 1 < len(tokens) else None
        if value is not None:
            out[tok] = value
    return out


# ─── 采集 ────────────────────────────────────────────────────────────────


def pull_gzh(db: MetricsDB, begin_date: str, end_date: str) -> dict:
    """公众号 datacube 取数（调用已 vendor 的 wechat_mp.client）。"""
    from zimeiti_api.core.credentials import load_account_credentials
    from zimeiti_api.governance.risk import handle_platform_error
    from zimeiti_api.platforms.gzh import GzhClient

    scope = f"datacube:{begin_date}~{end_date}"
    creds = load_account_credentials("gzh-main")
    client = GzhClient(creds["app_id"], creds["app_secret"])
    try:
        raw = client.datacube("getusersummary", begin_date, end_date)
    except Exception as exc:  # noqa: BLE001 - 采集失败留痕（不写零）
        db.record_error("gzh-main", scope, str(exc))
        level = handle_platform_error("gzh-main", scope, str(exc))
        return {"ok": False, "error": str(exc), "risk_level": level}
    metrics = parse_gzh_datacube(raw)
    if not metrics:
        db.record_error("gzh-main", scope, "空响应")
        return {"ok": False, "error": "空响应"}
    for metric, value in metrics.items():
        db.record_snapshot(None, "gzh-main", metric, value, source="datacube")
    return {"ok": True, "metrics": metrics}


def _xhs_throttle_path() -> Path:
    from pathlib import Path

    from zimeiti_api.config import DATA_DIR

    return Path(DATA_DIR) / "state" / "xhs-pull-throttle.json"


def pull_xhs(db: MetricsDB, page: Any = None) -> dict:
    """小红书数据看板取数（复用登录态打开创作者中心首页）。

    节流纪律（P0②，参考: xiaobei xhs-engagement「少操作一次页面就少一次风控
    暴露」）：单账号两次全量取数间隔 ≥20h；首页即窗口、不翻页（明文设计，
    禁止加翻页逻辑扩大风控暴露面）。

    注意：sync Playwright 需干净的事件循环环境——托管流程内请在独立进程调用本模块。
    """
    from datetime import datetime

    from zimeiti_api.governance.risk import handle_platform_error
    from zimeiti_api.platforms.xhs import XhsPublisher

    # ── 取数节流（软风控暴露面控制） ──────────────────────────────
    throttle_path = _xhs_throttle_path()
    now = datetime.now()
    last = ""
    if throttle_path.exists():
        try:
            last = json.loads(throttle_path.read_text(encoding="utf-8")).get("last", "")
        except (ValueError, OSError):
            last = ""
    if last:
        try:
            elapsed_h = (now - datetime.fromisoformat(last)).total_seconds() / 3600
            if elapsed_h < 20:
                db.record_error(
                    "xhs-main", "dashboard:home", f"节流跳过：距上次全量取数 {elapsed_h:.1f}h"
                )
                return {"ok": False, "skipped": f"取数节流（距上次 {elapsed_h:.1f}h < 20h）"}
        except ValueError:
            pass

    pub = XhsPublisher()
    own_page = page is None
    page = page or pub._open_page()
    try:
        page.goto(pub.selectors.get("home_url", "https://creator.xiaohongshu.com/new/home"))
        page.wait_for_timeout(6_000)
        body = page.inner_text("body")
    except Exception as exc:  # noqa: BLE001
        db.record_error("xhs-main", "dashboard:home", str(exc))
        level = handle_platform_error("xhs-main", "dashboard:home", str(exc))
        return {"ok": False, "error": str(exc), "risk_level": level}
    finally:
        if own_page:
            page.close()

    # 页面级登录墙判定（无异常但被重定向到登录页）
    from zimeiti_api.governance.risk import classify

    if classify(body) in ("login_wall", "soft_block"):
        level = handle_platform_error("xhs-main", "dashboard:home", body[:300])
        db.record_error("xhs-main", "dashboard:home", f"页面风控信号：{level}")
        return {"ok": False, "error": f"页面风控信号（{level}）", "risk_level": level}

    metrics = parse_xhs_dashboard(body)
    if not metrics:
        db.record_error("xhs-main", "dashboard:home", "未解析到指标")
        return {"ok": False, "error": "未解析到指标"}

    # 取数成功 → 更新节流游标
    throttle_path.parent.mkdir(parents=True, exist_ok=True)
    throttle_path.write_text(
        json.dumps({"last": now.isoformat(timespec="seconds")}, ensure_ascii=False),
        encoding="utf-8",
    )
    for metric, value in metrics.items():
        db.record_snapshot(None, "xhs-main", metric, value, source="creator-center")
    return {"ok": True, "metrics": metrics}


def migrate_from_sqlite(db: "MetricsDB", sqlite_path: str) -> dict:
    """一次性搬运：旧 SQLite 文件 → Postgres（需要时无损迁移）。

    仅搬运 publish_events / metric_snapshots 两表（collection_errors 为采集日志，不迁移）。
    """
    import sqlite3

    src_conn = sqlite3.connect(sqlite_path)
    src_conn.row_factory = sqlite3.Row
    events = [dict(r) for r in src_conn.execute("SELECT * FROM publish_events").fetchall()]
    snaps = [dict(r) for r in src_conn.execute("SELECT * FROM metric_snapshots").fetchall()]
    src_conn.close()

    counts = {"events": 0, "snapshots": 0}
    for e in events:
        db.record_event(
            platform=e["platform"],
            title=e["title"] or "",
            content_type=e.get("content_type") or "",
            source_folder=e["source_folder"],
            publish_date=e["publish_date"],
            publish_url=e.get("publish_url") or "",
            profile=e.get("profile") or "",
            topic_direction=e.get("topic_direction") or "",
            status=e.get("status") or "ok",
            notes=e.get("notes") or "",
        )
        counts["events"] += 1
    with db._conn() as conn:
        for s in snaps:
            conn.execute(
                "INSERT INTO metric_snapshots"
                " (event_id, platform, metric, value, source, captured_at)"
                " VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    s["event_id"],
                    s["platform"],
                    s["metric"],
                    s["value"],
                    s["source"],
                    s["captured_at"],
                ),
            )
            counts["snapshots"] += 1
        conn.commit()
    return counts


# ─── CLI ─────────────────────────────────────────────────────────────────


# 站点 → 账号（ops_daily/gateway 共用；单一事实来源在 ops_metrics）
SITE_ACCOUNTS = {"gzh": "gzh-main", "xhs": "xhs-main"}


def pull_platform(
    db: MetricsDB, site: str, begin_date: str | None = None, end_date: str | None = None
) -> dict:
    """按站点取数（调度器与 CLI 共用）。site: "gzh" | "xhs"。

    门禁（P0⑦②，任一命中即跳过——不是错误，是纪律）：
    - 平台已停用（登录失效未恢复）→ skipped
    - 软风控冷却中 → skipped
    gzh datacube 仅提供 T-1 及以前数据（A3 实测），默认取过去 7 天截至昨天。
    """
    from zimeiti_api.governance import platform_state
    from zimeiti_api.governance.risk import in_cooldown

    out: dict[str, Any] = {}
    account = SITE_ACCOUNTS.get(site, site)
    if not platform_state.is_enabled(account):
        entry = (platform_state._load() or {}).get(account) or {}
        out[site] = {"ok": False, "skipped": f"平台已停用（{entry.get('reason', '未知')}）"}
        return out
    if in_cooldown(account):
        out[site] = {"ok": False, "skipped": "软风控冷却中（30 分钟内不重试）"}
        return out
    if site == "gzh":
        today = datetime.now().date()
        end = end_date or (today - timedelta(days=1)).strftime("%Y-%m-%d")
        begin = begin_date or (today - timedelta(days=7)).strftime("%Y-%m-%d")
        out["gzh"] = pull_gzh(db, begin, end)
    if site == "xhs":
        out["xhs"] = pull_xhs(db)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="运营数据：事件记录/取数/只读归因")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_pull = sub.add_parser("pull", help="回收指标快照")
    p_pull.add_argument("--platform", default="all", choices=["all", "gzh", "xhs"])
    p_pull.add_argument("--begin", default=None, help="gzh datacube 起始日期 YYYY-MM-DD")
    p_pull.add_argument("--end", default=None, help="gzh datacube 结束日期 YYYY-MM-DD")

    p_rec = sub.add_parser("record", help="记录发布事件")
    p_rec.add_argument("--platform", required=True)
    p_rec.add_argument("--title", required=True)
    p_rec.add_argument("--source-folder", required=True)
    p_rec.add_argument("--publish-date", required=True)
    p_rec.add_argument("--profile", default="")
    p_rec.add_argument("--topic-direction", default="")
    p_rec.add_argument("--status", default="ok", choices=["ok", "failed"])
    p_rec.add_argument("--notes", default="")
    p_rec.add_argument("--publish-url", default="")

    p_mig = sub.add_parser("migrate-from-sqlite", help="一次性搬运旧 SQLite 数据到 PG")
    p_mig.add_argument("--path", required=True, help="旧 published.db 路径")

    p_rep = sub.add_parser("report", help="只读归因查询")
    p_rep.add_argument("--platform", default=None)
    p_rep.add_argument("--profile", default=None)

    args = parser.parse_args(argv)
    db = MetricsDB()

    if args.cmd == "record":
        event_id = db.record_event(
            platform=args.platform,
            title=args.title,
            source_folder=args.source_folder,
            publish_date=args.publish_date,
            profile=args.profile,
            topic_direction=args.topic_direction,
            status=args.status,
            notes=args.notes,
            publish_url=args.publish_url,
        )
        print(json.dumps({"event_id": event_id, "status": args.status}, ensure_ascii=False))
        return 0

    if args.cmd == "pull":
        sites = ("gzh", "xhs") if args.platform == "all" else (args.platform,)
        out: dict[str, Any] = {}
        for site in sites:
            out.update(pull_platform(db, site, args.begin, args.end))
        print(json.dumps(out, ensure_ascii=False, default=str))
        return 0

    if args.cmd == "migrate-from-sqlite":
        counts = migrate_from_sqlite(db, args.path)
        print(json.dumps(counts, ensure_ascii=False))
        return 0

    print(json.dumps(db.report(args.platform, args.profile), ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
