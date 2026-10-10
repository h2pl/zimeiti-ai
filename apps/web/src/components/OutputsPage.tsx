/** 内容库（已发布草稿产物，只读）——参考: Easel OutputsPage 空态模式。 */
import { useEffect, useState } from "react";
import type { OutputItem } from "../lib/api";
import { fetchOutputs, fetchProfiles } from "../lib/api";
import { IconFolder } from "./icons";

export default function OutputsPage() {
  const [accounts, setAccounts] = useState<{ account: string }[]>([]);
  const [current, setCurrent] = useState("");
  const [items, setItems] = useState<OutputItem[] | null>(null);
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
    setItems(null);
    fetchOutputs(current)
      .then(setItems)
      .catch((e) => {
        setItems([]);
        setError(e instanceof Error ? e.message : String(e));
      });
  }, [current]);

  return (
    <>
      <div className="page-head">
        <div>
          <div className="page-title">
            <IconFolder />
            内容库
          </div>
          <div className="page-subtitle">已发布的草稿产物归档（只读，含合规结论）</div>
        </div>
      </div>
      <div className="page-body">
        {error && <div className="notice-error">加载失败：{error}</div>}
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
        {items === null && <div className="dash-empty">加载中…</div>}
        {items && items.length === 0 && (
          <div className="empty-state">
            <div className="empty-icon">🗂</div>
            <h3>暂无产物</h3>
            <p>托管循环创作并发布的草稿会归档在这里。</p>
          </div>
        )}
        {items && items.length > 0 && (
          <table style={{ marginTop: 14 }}>
            <thead>
              <tr>
                <th>时间</th>
                <th>标题/选题</th>
                <th>合规</th>
                <th>slug</th>
              </tr>
            </thead>
            <tbody>
              {items.map((o) => (
                <tr key={o.slug}>
                  <td>{o.created_at.slice(0, 16).replace("T", " ")}</td>
                  <td>{o.title || o.topic}</td>
                  <td>
                    <span className={o.compliance_passed ? "badge badge-ok" : "badge badge-warn"}>
                      {o.compliance_passed ? "通过" : "拦截"}
                    </span>
                  </td>
                  <td className="page-subtitle">{o.slug}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
