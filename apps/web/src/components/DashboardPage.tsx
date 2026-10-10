/** 概览页——Easel 范式：page-head + dash-empty + fetch().then(setState)。 */
import { useCallback, useEffect, useState } from "react";
import type { Dashboard } from "../lib/api";
import { fetchDashboard } from "../lib/api";
import { IconDashboard } from "./icons";

export default function DashboardPage() {
  const [data, setData] = useState<Dashboard | null>(null);

  const load = useCallback(() => {
    fetchDashboard().then(setData).catch(() => {});
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, [load]);

  return (
    <>
      <div className="page-head">
        <div>
          <div className="page-title">
            <IconDashboard />
            概览
          </div>
          <div className="page-subtitle">账号状态、审批待办与今日发布一览（5 秒自动刷新）</div>
        </div>
      </div>
      <div className="page-body">
        {!data && <div className="dash-empty">加载中…</div>}
        {data && (
          <>
            <div className="kpi-row">
              <div className="kpi">
                <div className="kpi-num">{data.pending_approvals}</div>
                <div className="kpi-label">待审批</div>
              </div>
              <div className="kpi">
                <div className="kpi-num">{data.today_publishes}</div>
                <div className="kpi-label">今日发布</div>
              </div>
              <div className="kpi">
                <div className="kpi-num">
                  {Object.entries(data.accounts).filter(([, v]) => v).length}/
                  {Object.keys(data.accounts).length}
                </div>
                <div className="kpi-label">账号在线</div>
              </div>
            </div>
            <div className="section-title">账号状态</div>
            {Object.entries(data.accounts).map(([k, v]) => (
              <div key={k} className="status-row">
                <span className={v ? "status-dot online" : "status-dot offline"} />
                <span className={v ? "status-row-text status-ok" : "status-row-text status-bad"}>
                  {k} {v ? "" : "——已停用，请人工重登后恢复"}
                </span>
              </div>
            ))}
            <div className="section-title">最近日志</div>
            {data.recent_log.length === 0 && <div className="dash-empty">暂无日志</div>}
            <table>
              <tbody>
                {data.recent_log.map((e, i) => (
                  <tr key={i}>
                    <td>{new Date(e.ts).toLocaleTimeString()}</td>
                    <td>{e.action}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </div>
    </>
  );
}
