import { useCallback, useEffect, useState } from "react";
import "./App.css";

interface Approval {
  thread_id: string;
  instruction: string;
  account?: string;
  kind?: string;
  question?: string;
  options?: string[];
}

interface LogEntry {
  ts: string;
  action: string;
  thread_id?: string;
}

interface Board {
  [status: string]: { title: string; reason: string; direction: string; source: string }[];
}

interface CalEvent {
  date: string;
  title: string;
  platform: string;
  status: string;
}

const STATUSES = ["待做", "进行中", "已完成"];

export default function App() {
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [log, setLog] = useState<LogEntry[]>([]);
  const [board, setBoard] = useState<Board>({});
  const [events, setEvents] = useState<CalEvent[]>([]);
  const [busy, setBusy] = useState(false);
  const [custom, setCustom] = useState<Record<string, string>>({});

  const refresh = useCallback(async () => {
    const [a, l, k, c] = await Promise.all([
      fetch("/api/approvals").then((r) => r.json()),
      fetch("/api/publish-log").then((r) => r.json()),
      fetch("/api/kanban").then((r) => r.json()).catch(() => ({})),
      fetch("/api/calendar").then((r) => r.json()).catch(() => []),
    ]);
    setApprovals(a);
    setLog(l.reverse());
    setBoard(k);
    setEvents(c);
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

  const reject = async (threadId: string) => {
    setBusy(true);
    try {
      await fetch(`/api/approvals/${threadId}/reject`, { method: "POST" });
      await refresh();
    } finally {
      setBusy(false);
    }
  };

  const answer = async (threadId: string, message: string) => {
    if (!message.trim()) return;
    setBusy(true);
    try {
      await fetch(`/api/questions/${threadId}/answer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      });
      await refresh();
    } finally {
      setBusy(false);
    }
  };

  const move = async (title: string, status: string) => {
    setBusy(true);
    try {
      await fetch("/api/kanban/move", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, status }),
      });
      await refresh();
    } finally {
      setBusy(false);
    }
  };

  const questions = approvals.filter((a) => a.kind === "question");
  const plain = approvals.filter((a) => a.kind !== "question");

  return (
    <main className="container">
      <h1>Zimeiti AI · 运营工作台</h1>

      <section>
        <h2>Agent 提问（{questions.length}）</h2>
        {questions.length === 0 && <p className="empty">暂无提问</p>}
        {questions.map((a) => (
          <div key={a.thread_id} className="card question">
            <div>
              <strong>{a.question || a.instruction}</strong>
              <div className="meta">
                thread: {a.thread_id} · {a.account}
              </div>
            </div>
            <div className="options">
              {(a.options || []).map((o) => (
                <button key={o} disabled={busy} onClick={() => void answer(a.thread_id, o)}>
                  {o}
                </button>
              ))}
              <input
                placeholder="自定义回答…"
                value={custom[a.thread_id] || ""}
                onChange={(e) => setCustom({ ...custom, [a.thread_id]: e.target.value })}
              />
              <button
                disabled={busy}
                onClick={() => void answer(a.thread_id, custom[a.thread_id] || "")}
              >
                回答
              </button>
            </div>
          </div>
        ))}
      </section>

      <section>
        <h2>待审批（{plain.length}）</h2>
        {plain.length === 0 && <p className="empty">暂无待审批项</p>}
        {plain.map((a) => (
          <div key={a.thread_id} className="card">
            <div>
              <strong>{a.instruction}</strong>
              <div className="meta">
                thread: {a.thread_id} · {a.account}
              </div>
            </div>
            <div className="options">
              <button disabled={busy} onClick={() => void confirm(a.thread_id)}>
                确认发布
              </button>
              <button disabled={busy} className="danger" onClick={() => void reject(a.thread_id)}>
                拒绝
              </button>
            </div>
          </div>
        ))}
      </section>

      <section>
        <h2>选题看板</h2>
        <div className="board">
          {STATUSES.map((s) => (
            <div key={s} className="column">
              <h3>
                {s}（{(board[s] || []).length}）
              </h3>
              {(board[s] || []).map((c) => (
                <div key={c.title} className="card small">
                  <strong>{c.title}</strong>
                  <div className="meta">{c.direction}</div>
                  <div className="options">
                    {STATUSES.filter((x) => x !== s).map((x) => (
                      <button key={x} disabled={busy} onClick={() => void move(c.title, x)}>
                        → {x}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2>内容日历（{events.length}）</h2>
        <table>
          <thead>
            <tr>
              <th>日期</th>
              <th>标题</th>
              <th>平台</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            {events.map((e, i) => (
              <tr key={i}>
                <td>{e.date}</td>
                <td>{e.title}</td>
                <td>{e.platform}</td>
                <td>{e.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
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
