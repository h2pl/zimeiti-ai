import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import type { Approval } from "../api";

/** 审批中心（含 agent 问题卡片，P1⑧）。 */
export default function Approvals() {
  const [items, setItems] = useState<Approval[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [custom, setCustom] = useState<Record<string, string>>({});

  const refresh = useCallback(async () => {
    try {
      setItems(await api.approvals());
      setError("");
    } catch (e) {
      setError(String(e));
    }
  }, []);

  useEffect(() => {
    void refresh();
    const t = setInterval(refresh, 5000);
    return () => clearInterval(t);
  }, [refresh]);

  const run = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    try {
      await fn();
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const questions = items.filter((a) => a.kind === "question");
  const plain = items.filter((a) => a.kind !== "question");

  return (
    <>
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
              <button key={o} disabled={busy} onClick={() => void run(() => api.answer(a.thread_id, o))}>
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
              onClick={() => void run(() => api.answer(a.thread_id, custom[a.thread_id] || ""))}
            >
              回答
            </button>
          </div>
        </div>
      ))}

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
            <button disabled={busy} onClick={() => void run(() => api.confirm(a.thread_id))}>
              确认发布
            </button>
            <button
              disabled={busy}
              className="danger"
              onClick={() => void run(() => api.reject(a.thread_id))}
            >
              拒绝
            </button>
          </div>
        </div>
      ))}
      {error && <p className="empty">{error}</p>}
    </>
  );
}
