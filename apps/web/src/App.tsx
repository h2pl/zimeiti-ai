import { useCallback, useEffect, useState } from "react";
import "./App.css";

interface Approval {
  thread_id: string;
  instruction: string;
}

interface LogEntry {
  ts: string;
  action: string;
  thread_id?: string;
}

export default function App() {
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [log, setLog] = useState<LogEntry[]>([]);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    const [a, l] = await Promise.all([
      fetch("/api/approvals").then((r) => r.json()),
      fetch("/api/publish-log").then((r) => r.json()),
    ]);
    setApprovals(a);
    setLog(l.reverse());
  }, []);

  useEffect(() => {
    void refresh();
    const timer = setInterval(refresh, 5000);
    return () => clearInterval(timer);
  }, [refresh]);

  const confirm = async (threadId: string) => {
    setBusy(true);
    try {
      await fetch(`/api/approvals/${threadId}/confirm`, { method: "POST" });
      await refresh();
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="container">
      <h1>Zimeiti AI · 发布审批</h1>
      <section>
        <h2>待审批（{approvals.length}）</h2>
        {approvals.length === 0 && <p className="empty">暂无待审批项</p>}
        {approvals.map((a) => (
          <div key={a.thread_id} className="card">
            <div>
              <strong>{a.instruction}</strong>
              <div className="meta">thread: {a.thread_id}</div>
            </div>
            <button disabled={busy} onClick={() => void confirm(a.thread_id)}>
              确认发布
            </button>
          </div>
        ))}
      </section>
      <section>
        <h2>执行日志</h2>
        <table>
          <thead>
            <tr>
              <th>时间</th>
              <th>动作</th>
              <th>线程</th>
            </tr>
          </thead>
          <tbody>
            {log.map((e, i) => (
              <tr key={i}>
                <td>{new Date(e.ts).toLocaleString()}</td>
                <td>{e.action}</td>
                <td>{e.thread_id ?? "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  );
}
