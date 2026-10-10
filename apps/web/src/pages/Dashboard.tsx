import { useEffect, useState } from "react";
import { api } from "../api";
import type { Dashboard as Dash, LogEntry } from "../api";

/** 概览页（P1⑪ Easel Dashboard 对标）。 */
export default function Dashboard() {
  const [data, setData] = useState<Dash | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = () =>
      api
        .dashboard()
        .then(setData)
        .catch((e) => setError(String(e)));
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, []);

  if (error)
    return (
      <>
        <h2>概览</h2>
        <p className="empty">加载失败：{error}</p>
      </>
    );
  if (!data) return <p className="empty">加载中…</p>;

  return (
    <>
      <h2>概览</h2>
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
      <h3>账号状态</h3>
      <ul className="plain-list">
        {Object.entries(data.accounts).map(([k, v]) => (
          <li key={k}>
            {k}：{v ? "✅ 启用" : "⛔ 已停用（登录失效待恢复）"}
          </li>
        ))}
      </ul>
      <h3>最近日志</h3>
      <table>
        <tbody>
          {(data.recent_log as LogEntry[]).map((e, i) => (
            <tr key={i}>
              <td>{new Date(e.ts).toLocaleTimeString()}</td>
              <td>{e.action}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
