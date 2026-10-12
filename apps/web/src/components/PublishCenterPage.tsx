/** 发布中心（feat-publish-orchestration：预检/定时排期/取消）——Easel PublishPage 对标。 */
import { useCallback, useEffect, useState } from "react";
import type { OutputItem, PreflightResult, QueueEntry } from "../lib/api";
import {
  cancelQueueEntry,
  enqueueDraft,
  enqueueDraftScheduled,
  fetchOutputs,
  fetchPreflight,
  fetchProfiles,
  fetchPublishQueue,
} from "../lib/api";
import { IconSend } from "./icons";

export default function PublishCenterPage() {
  const [accounts, setAccounts] = useState<{ account: string }[]>([]);
  const [current, setCurrent] = useState("");
  const [outputs, setOutputs] = useState<OutputItem[] | null>(null);
  const [queue, setQueue] = useState<QueueEntry[]>([]);
  const [busy, setBusy] = useState(false);
  const [preflight, setPreflight] = useState<Record<string, PreflightResult | null>>({});
  const [runAt, setRunAt] = useState("");
  const [toast, setToast] = useState<{ text: string; ok: boolean } | null>(null);

  const showToast = (text: string, ok = true) => {
    setToast({ text, ok });
    setTimeout(() => setToast(null), 2600);
  };

  const load = useCallback(async () => {
    const accs = await fetchProfiles().catch(() => []);
    setAccounts(accs);
    if (accs.length && !current) setCurrent(accs[0].account);
    if (current) {
      setOutputs(await fetchOutputs(current).catch(() => []));
      setQueue(await fetchPublishQueue().catch(() => []));
    }
  }, [current]);

  useEffect(() => {
    void load();
  }, [load]);

  const runPreflight = async (slug: string) => {
    try {
      const r = await fetchPreflight(current, slug);
      setPreflight((p) => ({ ...p, [slug]: r }));
    } catch (e) {
      showToast(e instanceof Error ? e.message : String(e), false);
    }
  };

  const doEnqueue = async (o: OutputItem, scheduled: boolean) => {
    setBusy(true);
    try {
      if (scheduled && !runAt) {
        showToast("请先选择计划时间", false);
        return;
      }
      if (scheduled) {
        await enqueueDraftScheduled(current, o.slug, o.title || o.topic, runAt);
      } else {
        await enqueueDraft(current, o.slug, o.title || o.topic);
      }
      showToast(scheduled ? `已定时排期：${runAt.replace("T", " ")}` : "已入队");
      await load();
    } catch (e) {
      showToast(e instanceof Error ? e.message : String(e), false);
    } finally {
      setBusy(false);
    }
  };

  const cancel = async (entry: QueueEntry) => {
    setBusy(true);
    try {
      await cancelQueueEntry(entry.id);
      showToast("已取消");
      await load();
    } catch (e) {
      showToast(e instanceof Error ? e.message : String(e), false);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <div className="page-head">
        <div>
          <div className="page-title">
            <IconSend />
            发布中心
          </div>
          <div className="page-subtitle">
            发布编排：预检 → 入队（可定时）→ 网关/审批链路消费发布；重复入队被拒绝
          </div>
        </div>
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
      </div>
      <div className="page-body">
        <div className="section-title">
          可排期草稿
          <label className="field-label" style={{ margin: 0, marginLeft: 12 }}>
            计划时间
            <input
              type="datetime-local"
              className="field"
              style={{ marginLeft: 8, width: 220 }}
              value={runAt}
              onChange={(e) => setRunAt(e.target.value)}
            />
          </label>
          <span className="page-subtitle">（留空 = 立即入队）</span>
        </div>
        {outputs === null && <div className="dash-empty">加载中…</div>}
        {outputs && outputs.length === 0 && (
          <div className="empty-state">
            <div className="empty-icon">🗂</div>
            <h3>暂无草稿产物</h3>
            <p>在对话工作台或托管循环中创作的内容会出现在这里。</p>
          </div>
        )}
        {outputs &&
          outputs.map((o) => {
            const pf = preflight[o.slug];
            const violations = pf ? Object.values(pf.preflight).flat() : [];
            return (
              <div key={o.slug} className="card idea-card" style={{ marginBottom: 8 }}>
                <div className="idea-card-title">{o.title || o.topic}</div>
                <div className="idea-card-direction">
                  {o.created_at.slice(0, 16).replace("T", " ")} ·{" "}
                  {o.compliance_passed ? "合规通过" : "合规拦截"}
                </div>
                <div className="options">
                  <button
                    className="btn btn-sm"
                    disabled={busy || !o.compliance_passed}
                    onClick={() => void runPreflight(o.slug)}
                  >
                    {pf ? "重新预检" : "预检"}
                  </button>
                  <button
                    className="btn btn-sm btn-primary"
                    disabled={busy || !o.compliance_passed || (pf !== undefined && pf !== null && !pf.passed)}
                    onClick={() => void doEnqueue(o, Boolean(runAt))}
                  >
                    {runAt ? "定时入队" : "入发布队列"}
                  </button>
                </div>
                {pf && (
                  <div className="idea-card-direction" style={{ marginTop: 6 }}>
                    {pf.passed ? (
                      <span className="badge badge-ok">预检通过</span>
                    ) : (
                      <>
                        <span className="badge badge-warn">预检未通过：</span>
                        {violations.map((v, i) => (
                          <span key={i} className="badge badge-warn">
                            {v}
                          </span>
                        ))}
                      </>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        <div className="section-title">发布队列（{queue.length}）</div>
        <table>
          <thead>
            <tr>
              <th>账号</th>
              <th>标题</th>
              <th>计划时间</th>
              <th>状态</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {queue.map((e) => (
              <tr key={e.id}>
                <td>{e.account}</td>
                <td>{e.title}</td>
                <td>{e.run_at.slice(0, 16).replace("T", " ")}</td>
                <td>
                  <span
                    className={
                      e.status === "done"
                        ? "badge badge-ok"
                        : e.status === "failed"
                          ? "badge badge-warn"
                          : "badge badge-accent"
                    }
                  >
                    {e.status}
                  </span>
                </td>
                <td>
                  {e.status === "pending" && (
                    <button className="btn btn-sm btn-danger" disabled={busy} onClick={() => void cancel(e)}>
                      取消
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {toast && <div className={toast.ok ? "toast ok" : "toast err"}>{toast.text}</div>}
    </>
  );
}
