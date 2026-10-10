import { useEffect, useState } from "react";
import { api } from "../api";
import type { Trends } from "../api";

/** 趋势页（基线归一化指标，数据来自校准证据引擎）。 */
export default function TrendsPage() {
  const [accounts, setAccounts] = useState<{ account: string }[]>([]);
  const [current, setCurrent] = useState("");
  const [data, setData] = useState<Trends | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    void api
      .profiles()
      .then(setAccounts)
      .catch(() => setAccounts([]));
  }, []);

  useEffect(() => {
    if (!current || !accounts.some((a) => a.account === current)) return;
    setData(null); // S2：切换账号清空旧数据，避免与新账号误读
    api
      .trends(current)
      .then((d) => {
        setData(d);
        setError("");
      })
      .catch((e) => {
        setData(null);
        setError(e instanceof Error ? e.message : String(e));
      });
  }, [current, accounts]);

  return (
    <>
      <h2>趋势</h2>
      <div className="options">
        {accounts.map((a) => (
          <button
            key={a.account}
            className={a.account === current ? "active" : ""}
            onClick={() => setCurrent(a.account)}
          >
            {a.account}
          </button>
        ))}
      </div>
      {error && <p className="empty">无数据：{error}</p>}
      {data && (
        <table>
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
      )}
      {data && (
        <p className="meta">
          样本：{data.events} 篇事件 / {data.snapshots} 条快照（关联性不等于因果性）
        </p>
      )}
    </>
  );
}
