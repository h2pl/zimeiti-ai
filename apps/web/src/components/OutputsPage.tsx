/** 内容库（正文查看器，feat-outputs-viewer）——参考: Easel OutputsPage。 */
import { useCallback, useEffect, useState } from "react";
import DOMPurify from "dompurify";
import { marked } from "marked";
import { fetchOutputDetail, fetchOutputs, fetchProfiles } from "../lib/api";
import type { OutputDetail, OutputItem } from "../lib/api";
import { IconFolder } from "./icons";

interface Workspace {
  account: string;
  slug: string;
  platform: string;
  body: string;
  title: string;
  compliance_passed: boolean;
}

function mdToHtml(md: string): string {
  return DOMPurify.sanitize(marked.parse(md) as string);
}

export default function OutputsPage() {
  const [accounts, setAccounts] = useState<{ account: string }[]>([]);
  const [current, setCurrent] = useState("");
  const [items, setItems] = useState<OutputItem[] | null>(null);
  const [detail, setDetail] = useState<OutputDetail | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!current) return;
    setError("");
    try {
      setItems(await fetchOutputs(current));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setItems([]);
    }
  }, [current]);

  useEffect(() => {
    fetchProfiles()
      .then((a) => {
        setAccounts(a);
        if (a.length && !current) setCurrent(a[0].account);
      })
      .catch(() => setAccounts([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const openDetail = async (slug: string) => {
    setError("");
    try {
      setDetail(await fetchOutputDetail(current, slug));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  return (
    <>
      <div className="page-head">
        <div>
          <div className="page-title">
            <IconFolder />
            内容库
          </div>
          <div className="page-subtitle">已发布的草稿产物归档（只读，含合规结论与正文查看）</div>
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
        {error && <div className="notice-error">加载失败：{error}</div>}
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
                <th></th>
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
                  <td>
                    <button className="btn btn-sm" onClick={() => void openDetail(o.slug)}>
                      查看正文
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      {detail && (
        <div className="overlay" onClick={() => setDetail(null)}>
          <div
            className="modal"
            style={{ maxWidth: 860, maxHeight: "86vh", overflowY: "auto" }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="page-title" style={{ fontSize: 20 }}>
              {detail.drafts?.xhs?.title || detail.topic}
            </div>
            <div className="page-subtitle">
              {detail.account} · {detail.slug} · {detail.created_at.slice(0, 16).replace("T", " ")} ·{" "}
              <span
                className={detail.compliance?.passed ? "badge badge-ok" : "badge badge-warn"}
              >
                合规{detail.compliance?.passed ? "通过" : "拦截"}
              </span>
            </div>
            {(["xhs", "gzh"] as const).map(
              (p) =>
                detail.drafts?.[p] && (
                  <div key={p} style={{ marginTop: 14 }}>
                    <div className="section-title">
                      {p === "xhs" ? "小红书稿" : "公众号稿"}
                      {p === "xhs" && detail.drafts?.xhs?.tags?.length ? (
                        <span className="badge">{detail.drafts.xhs.tags.join(" / ")}</span>
                      ) : null}
                    </div>
                    <div
                      className="page-subtitle"
                      dangerouslySetInnerHTML={{ __html: mdToHtml(detail.drafts[p].body || "") }}
                    />
                  </div>
                ),
            )}
            <div style={{ marginTop: 18, textAlign: "right" }}>
              <button className="btn" onClick={() => setDetail(null)}>
                关闭
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

// Workspace 类型保留（发布编排变更将复用）
export type { Workspace };
