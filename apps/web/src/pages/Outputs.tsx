import { useEffect, useState } from "react";
import { api } from "../api";
import type { OutputItem } from "../api";

/** 内容库（已发布草稿产物，只读）。 */
export default function Outputs() {
  const [accounts, setAccounts] = useState<{ account: string }[]>([]);
  const [current, setCurrent] = useState("");
  const [items, setItems] = useState<OutputItem[] | null>(null);

  useEffect(() => {
    void api
      .profiles()
      .then((a) => {
        setAccounts(a);
        if (a.length && !current) setCurrent(a[0].account);
      })
      .catch(() => setAccounts([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!current) return;
    setItems(null);
    void api
      .outputs(current)
      .then(setItems)
      .catch(() => setItems([]));
  }, [current]);

  return (
    <>
      <h2>内容库</h2>
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
      {items === null && <p className="empty">加载中…</p>}
      {items && items.length === 0 && <p className="empty">暂无产物</p>}
      {items && items.length > 0 && (
        <table>
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
                <td>{o.compliance_passed ? "✅" : "⛔"}</td>
                <td className="meta">{o.slug}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
