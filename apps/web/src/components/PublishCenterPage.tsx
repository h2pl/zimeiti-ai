/** 发布中心（web-chat-publish：内容库草稿入队 + 队列状态）——Easel PublishPage 对标。 */
import { useCallback, useEffect, useState } from "react";
import type { OutputItem } from "../lib/api";
import { enqueueDraft, fetchOutputs, fetchProfiles, fetchPublishQueue } from "../lib/api";
import { IconSend } from "./icons";

interface QueueEntry {
  id: string;
  account: string;
  drafts_path: string;
  title: string;
  run_at: string;
  status: string;
}

export default function PublishCenterPage() {
  const [accounts, setAccounts] = useState<{ account: string }[]>([]);
  const [current, setCurrent] = useState("");
  const [outputs, setOutputs] = useState<OutputItem[] | null>(null);
  const [queue, setQueue] = useState<QueueEntry[]>([]);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<{ text: string; ok: boolean } | null>(null);

  const showToast = (text: string, ok = true) => {
    setToast({ text, ok });
    setTimeout(() => setToast(null), 2200);
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

  const enqueue = async (o: OutputItem) => {
    setBusy(true);
    try {
      await enqueueDraft(current, o.slug, o.title || o.topic);
      showToast(`已入队：${o.title || o.topic}`);
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
            内容库草稿入发布队列（幂等：重复入队被拒绝）；入队后由网关/审批链路消费发布
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
        <div className="section-title">可入队草稿</div>
        {outputs === null && <div className="dash-empty">加载中…</div>}
        {outputs && outputs.length === 0 && (
          <div className="empty-state">
            <div className="empty-icon">🗂</div>
            <h3>暂无草稿产物</h3>
            <p>在对话工作台或托管循环中创作的内容会出现在这里。</p>
          </div>
        )}
        {outputs &&
          outputs.map((o) => (
            <div key={o.slug} className="card idea-card" style={{ marginBottom: 8 }}>
              <div className="idea-card-title">{o.title || o.topic}</div>
              <div className="idea-card-direction">
                {o.created_at.slice(0, 16).replace("T", " ")} ·{" "}
                {o.compliance_passed ? "合规通过" : "合规拦截"}
              </div>
              <div className="idea-card-actions" style={{ display: "flex" }}>
                <button
                  className="btn btn-sm btn-primary"
                  disabled={busy || !o.compliance_passed}
                  onClick={() => void enqueue(o)}
                >
                  入发布队列
                </button>
              </div>
            </div>
          ))}
        <div className="section-title">发布队列（{queue.length}）</div>
        <table>
          <thead>
            <tr>
              <th>账号</th>
              <th>标题</th>
              <th>计划时间</th>
              <th>状态</th>
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
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {toast && <div className={toast.ok ? "toast ok" : "toast err"}>{toast.text}</div>}
    </>
  );
}
