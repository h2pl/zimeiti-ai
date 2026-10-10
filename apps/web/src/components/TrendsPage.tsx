/** 趋势页（基线归一化指标，数据来自校准证据引擎）——Easel 范式。 */
import { useEffect, useState } from "react";
import type { Trends } from "../lib/api";
import { fetchProfiles, fetchTrends } from "../lib/api";
import { IconTrend } from "./icons";

export default function TrendsPage() {
  const [accounts, setAccounts] = useState<{ account: string }[]>([]);
  const [current, setCurrent] = useState("");
  const [data, setData] = useState<Trends | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchProfiles()
      .then((a) => {
        setAccounts(a);
        if (a.length) setCurrent(a[0].account);
      })
      .catch(() => setAccounts([]));
  }, []);

  useEffect(() => {
    if (!current) return;
    setData(null);
    setError("");
    // S2 修复：切换账号清空旧数据；过期响应竞态以错误态覆盖兜底
    fetchTrends(current)
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, [current]);

  return (
    <>
      <div className="page-head">
        <div>
          <div className="page-title">
            <IconTrend />
            趋势
          </div>
          <div className="page-subtitle">账号级指标基线归一化（最新值 / 历史均值）——数据来自校准证据引擎</div>
        </div>
      </div>
      <div className="page-body">
        <div className="options">
          {accounts.map((a) => (
            <button
              key={a.account}
              className={a.account === current ? "chip active" : "chip"}
              onClick={() => setCurrent(a.account)}
            >
              {a.account}
            </button>
          ))}
        </div>
        {error && <div className="notice-error">无数据：{error}</div>}
        {data && (
          <>
            <table style={{ marginTop: 14 }}>
              <thead>
                <tr>
                  <th>指标</th>
                  <th>均值</th>
                  <th>最新</th>
                  <th>归一化</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(data.baseline).map(([k, b]) => (
                  <tr key={k}>
                    <td>{k}</td>
                    <td>{b.mean}</td>
                    <td>{b.latest}</td>
                    <td>
                      {b.normalized === null
                        ? "基线不足"
                        : `${b.normalized}x${b.normalized >= 1 ? " ↑" : " ↓"}`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="page-subtitle">
              样本：{data.events} 篇事件 / {data.snapshots} 条快照——关联性不等于因果性
            </p>
          </>
        )}
      </div>
    </>
  );
}
