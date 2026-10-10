/** 审批中心（含 agent 问题卡片，P1⑧）——Easel 范式。 */
import { useCallback, useEffect, useState } from "react";
import type { Approval } from "../lib/api";
import { answerQuestion, confirmApproval, fetchApprovals, rejectApproval } from "../lib/api";
import { IconCheck } from "./icons";

export default function ApprovalsPage() {
  const [items, setItems] = useState<Approval[]>([]);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<{ text: string; ok: boolean } | null>(null);
  const [custom, setCustom] = useState<Record<string, string>>({});

  const showToast = (text: string, ok = true) => {
    setToast({ text, ok });
    setTimeout(() => setToast(null), 2200);
  };

  const load = useCallback(() => {
    fetchApprovals().then(setItems).catch(() => {});
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, [load]);

  const run = async (fn: () => Promise<unknown>, okText: string) => {
    setBusy(true);
    try {
      await fn();
      showToast(okText);
    } catch (e) {
      showToast(e instanceof Error ? e.message : String(e), false);
    } finally {
      setBusy(false);
      load();
    }
  };

  const questions = items.filter((a) => a.kind === "question");
  const plain = items.filter((a) => a.kind !== "question");

  return (
    <>
      <div className="page-head">
        <div>
          <div className="page-title">
            <IconCheck />
            审批中心
          </div>
          <div className="page-subtitle">
            agent 的人工闸门：选题确认、发布确认与执行中提问（5 秒自动刷新）
          </div>
        </div>
      </div>
      <div className="page-body">
        <div className="section-title">Agent 提问（{questions.length}）</div>
        {questions.length === 0 && <div className="dash-empty">暂无提问</div>}
        {questions.map((a) => (
          <div key={a.thread_id} className="card idea-card" style={{ marginBottom: 10 }}>
            <div className="idea-card-title">{a.question || a.instruction}</div>
            <div className="idea-card-direction">
              thread: {a.thread_id} · {a.account}
            </div>
            <div className="options">
              {(a.options || []).map((o) => (
                <button
                  key={o}
                  className="btn btn-sm"
                  disabled={busy}
                  onClick={() => void run(() => answerQuestion(a.thread_id, o), "已回答")}
                >
                  {o}
                </button>
              ))}
              <input
                className="field"
                style={{ maxWidth: 260 }}
                placeholder="自定义回答…"
                value={custom[a.thread_id] || ""}
                onChange={(e) => setCustom({ ...custom, [a.thread_id]: e.target.value })}
              />
              <button
                className="btn btn-sm btn-primary"
                disabled={busy}
                onClick={() => void run(() => answerQuestion(a.thread_id, custom[a.thread_id] || ""), "已回答")}
              >
                回答
              </button>
            </div>
          </div>
        ))}

        <div className="section-title">待审批（{plain.length}）</div>
        {plain.length === 0 && <div className="dash-empty">暂无待审批项</div>}
        {plain.map((a) => (
          <div key={a.thread_id} className="card idea-card" style={{ marginBottom: 10 }}>
            <div className="idea-card-title">{a.instruction}</div>
            <div className="idea-card-direction">
              thread: {a.thread_id} · {a.account}
            </div>
            <div className="idea-card-actions" style={{ display: "flex" }}>
              <button
                className="btn btn-sm btn-primary"
                disabled={busy}
                onClick={() => void run(() => confirmApproval(a.thread_id), "已确认")}
              >
                确认发布
              </button>
              <button
                className="btn btn-sm btn-danger"
                disabled={busy}
                onClick={() => void run(() => rejectApproval(a.thread_id), "已拒绝")}
              >
                拒绝
              </button>
            </div>
          </div>
        ))}
      </div>
      {toast && <div className={toast.ok ? "toast ok" : "toast err"}>{toast.text}</div>}
    </>
  );
}
