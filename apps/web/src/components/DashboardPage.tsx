/** 概览页——信息架构对齐 Easel DashboardPage（问候语/快捷操作/KPI 图标卡/模块卡片）。 */
import { useCallback, useEffect, useState } from "react";
import type { Dashboard } from "../lib/api";
import { fetchDashboard } from "../lib/api";
import { IconCalendar, IconIdea, IconTrend, IconUser } from "./icons";

function greeting(): string {
  const h = new Date().getHours();
  if (h < 6) return "夜深了";
  if (h < 12) return "早上好";
  if (h < 18) return "下午好";
  return "晚上好";
}

export default function DashboardPage({ onNavigate }: { onNavigate: (p: "approvals" | "ideas" | "calendar" | "outputs" | "trends" | "logs") => void }) {
  const [data, setData] = useState<Dashboard | null>(null);

  const load = useCallback(() => {
    fetchDashboard().then(setData).catch(() => {});
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, [load]);

  const offline = Object.entries(data?.accounts || {}).filter(([, v]) => !v);

  return (
    <>
      <div className="page-head">
        <div>
          <div className="page-title">
            {greeting()} 👋
          </div>
          <div className="page-subtitle">
            {offline.length > 0
              ? `⚠ ${offline.map(([k]) => k).join("、")} 登录态已失效——已停用该平台，请人工重登后恢复。`
              : "全部账号登录态健康，托管循环与审批流正常。"}
          </div>
        </div>
      </div>
      <div className="page-body">
        <div className="dash-actions">
          <button className="chip" onClick={() => onNavigate("approvals")}>
            💬 去审批
          </button>
          <button className="chip" onClick={() => onNavigate("ideas")}>
            ✦ 选题看板
          </button>
          <button className="chip" onClick={() => onNavigate("calendar")}>
            📅 内容日历
          </button>
          <button className="chip" onClick={() => onNavigate("outputs")}>
            📁 内容库
          </button>
        </div>
        <div className="kpi-row">
          <div className="kpi">
            <div className="kpi-icon"><IconIdea size={16} /></div>
            <div className="kpi-num">{data?.pending_approvals ?? "-"}</div>
            <div className="kpi-label">待审批</div>
          </div>
          <div className="kpi">
            <div className="kpi-icon"><IconCalendar size={16} /></div>
            <div className="kpi-num">{data?.today_publishes ?? "-"}</div>
            <div className="kpi-label">今日发布</div>
          </div>
          <div className="kpi">
            <div className="kpi-icon"><IconUser size={16} /></div>
            <div className="kpi-num">
              {data ? `${Object.entries(data.accounts).filter(([, v]) => v).length}/${Object.keys(data.accounts).length}` : "-"}
            </div>
            <div className="kpi-label">已登录账号</div>
          </div>
          <div className="kpi">
            <div className="kpi-icon"><IconTrend size={16} /></div>
            <div className="kpi-num">
              <a className="kpi-link" href="#trends" onClick={(e) => { e.preventDefault(); onNavigate("trends"); }}>
                查看 →
              </a>
            </div>
            <div className="kpi-label">创作数据</div>
          </div>
        </div>
        <div className="dash-grid">
          <div className="card dash-card">
            <div className="dash-card-head">
              <span className="dash-card-title">执行日志</span>
              <a className="dash-card-link" href="#logs" onClick={(e) => { e.preventDefault(); onNavigate("logs"); }}>
                日志 →
              </a>
            </div>
            {(data?.recent_log.length ?? 0) === 0 && <div className="dash-empty">暂无日志</div>}
            {data?.recent_log.slice(0, 5).map((e, i) => (
              <div key={i} className="dash-log-row">
                <span className="dash-log-ts">{new Date(e.ts).toLocaleTimeString()}</span>
                <span>{e.action}</span>
              </div>
            ))}
          </div>
          <div className="card dash-card">
            <div className="dash-card-head">
              <span className="dash-card-title">账号状态</span>
              <span className="dash-card-link">画像 →</span>
            </div>
            {Object.entries(data?.accounts || {}).length === 0 && (
              <div className="dash-empty">尚未配置账号画像</div>
            )}
            {Object.entries(data?.accounts || {}).map(([k, v]) => (
              <div key={k} className="dash-log-row">
                <span className={v ? "status-dot online" : "status-dot offline"} />
                <span className={v ? "status-ok" : "status-bad"}>{k}</span>
                <span className="dash-empty">{v ? "" : "登录失效，待重登"}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
