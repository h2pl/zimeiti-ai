/** 内容库（feat-outputs-viewer：元数据列表 + 展开正文面板）——Easel OutputsPage 对标。 */
import { useCallback, useEffect, useState } from "react";
import type { OutputDetail, OutputItem } from "../lib/api";
import { coverUrl, fetchOutputDetail, fetchOutputs, fetchProfiles } from "../lib/api";
import { IconFolder } from "./icons";

export default function OutputsPage() {
  const [accounts, setAccounts] = useState<{ account: string }[]>([]);
  const [current, setCurrent] = useState("");
  const [items, setItems] = useState<OutputItem[] | null>(null);
  const [openSlug, setOpenSlug] = useState<string | null>(null);
  const [detail, setDetail] = useState<OutputDetail | null>(null);

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
    setOpenSlug(null);
    fetchOutputs(current)
      .then(setItems)
      .catch(() => setItems([]));
  }, [current]);

  const toggle = useCallback(
    async (slug: string) => {
      if (openSlug === slug) {
        setOpenSlug(null);
        return;
      }
      try {
        const d = await fetchOutputDetail(current, slug);
        setDetail(d);
        setOpenSlug(slug);
      } catch {
        setDetail(null);
      }
    },
    [current, openSlug],
  );

  return (
    <>
      <div className="page-head">
        <div>
          <div className="page-title">
            <IconFolder />
            内容库
          </div>
          <div className="page-subtitle">已发布的草稿产物归档（只读，展开查看两平台正文与封面）</div>
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
        {items === null && <div className="dash-empty">加载中…</div>}
        {items && items.length === 0 && (
          <div className="empty-state">
            <div className="empty-icon">🗂</div>
            <h3>暂无产物</h3>
            <p>托管循环创作并发布的草稿会归档在这里。</p>
          </div>
        )}
        {items &&
          items.map((o) => (
            <div key={o.slug} className="card idea-card" style={{ marginBottom: 8 }}>
              <div className="idea-card-title">{o.title || o.topic}</div>
              <div className="idea-card-direction">
                {o.created_at.slice(0, 16).replace("T", " ")} ·{" "}
                {o.compliance_passed ? "合规通过" : "合规拦截"}
              </div>
              <div className="options">
                <button className="btn btn-sm" onClick={() => void toggle(o.slug)}>
                  {openSlug === o.slug ? "收起正文" : "展开正文"}
                </button>
              </div>
              {openSlug === o.slug && detail && (
                <div style={{ marginTop: 10 }}>
                  <img
                    src={coverUrl(current, o.slug)}
                    alt="封面"
                    style={{ maxWidth: 220, borderRadius: 8, marginBottom: 10 }}
                    onError={(e) => {
                      (e.target as HTMLImageElement).style.display = "none";
                    }}
                  />
                  <h4 className="idea-card-title">小红书</h4>
                  <div className="page-subtitle">{detail.drafts.xhs?.title ?? ""}</div>
                  <p style={{ whiteSpace: "pre-wrap" }}>{detail.drafts.xhs?.body ?? ""}</p>
                  <div className="options">
                    {(detail.drafts.xhs?.tags || []).map((t) => (
                      <span key={t} className="badge badge-accent">
                        #{t}
                      </span>
                    ))}
                  </div>
                  <h4 className="idea-card-title">公众号</h4>
                  <div className="page-subtitle">{detail.drafts.gzh?.title ?? ""}</div>
                  <p className="page-subtitle">{detail.drafts.gzh?.summary ?? ""}</p>
                  <p style={{ whiteSpace: "pre-wrap" }}>{detail.drafts.gzh?.body ?? ""}</p>
                </div>
              )}
            </div>
          ))}
      </div>
    </>
  );
}
