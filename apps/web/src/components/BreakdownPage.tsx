/** 拆爆款/单篇复盘——参考: Easel BreakdownPage（模式 A 证据 + 模式 B 提炼）。 */
import { useCallback, useEffect, useState } from "react";
import DOMPurify from "dompurify";
import { marked } from "marked";
import type { FormulaResult } from "../lib/api";
import { fetchPostmortemNote, fetchPostmortems, fetchProfiles } from "../lib/api";
import { IconTrend } from "./icons";

function renderMd(md: string): string {
  return DOMPurify.sanitize(marked.parse(md) as string);
}

export default function BreakdownPage() {
  const [accounts, setAccounts] = useState<{ account: string }[]>([]);
  const [current, setCurrent] = useState("");
  const [result, setResult] = useState<FormulaResult | null>(null);
  const [note, setNote] = useState<{ title: string; html: string } | null>(null);

  const loadFormula = useCallback((account: string) => {
    if (!account) return;
    fetchPostmortems(account).then(setResult).catch(() => setResult(null));
  }, []);

  useEffect(() => {
    fetchProfiles()
      .then((a) => {
        setAccounts(a);
        if (a.length) setCurrent(a[0].account);
      })
      .catch(() => setAccounts([]));
  }, []);

  useEffect(() => {
    loadFormula(current);
  }, [current, loadFormula]);

  const openNote = async (title: string) => {
    try {
      const r = await fetchPostmortemNote(current, title);
      setNote({ title, html: renderMd(r.markdown) });
    } catch {
      setNote({ title, html: "<p>加载失败</p>" });
    }
  };

  return (
    <>
      <div className="page-head">
        <div>
          <div className="page-title">
            <IconTrend />
            拆爆款
          </div>
          <div className="page-subtitle">
            单篇复盘证据与爆款规律提炼（确定性统计，关联性不等于因果性；样本 &lt;5 提示可信度低）
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
        {result && (
          <div className="card" style={{ padding: "16px 18px", marginBottom: 14 }}>
            <div className="idea-card-title">爆款规律（样本 {result.sample} 篇）</div>
            {result.sample < 5 && (
              <div className="idea-card-direction">样本不足 5 篇，规律可信度低，仅作记录。</div>
            )}
            <div style={{ marginTop: 8 }}>
              {result.top.map((t, i) => (
                <div key={t.title} className="dash-log-row">
                  <span className="trend-rank top">{i + 1}</span>
                  <span className="trend-title" style={{ cursor: "pointer" }} onClick={() => void openNote(t.title)}>
                    {t.title}
                  </span>
                  <span className="badge">{t.read_latest} read</span>
                  <span className="badge">{t.lifecycle}</span>
                </div>
              ))}
            </div>
          </div>
        )}
        {note && (
          <div className="card" style={{ padding: "16px 18px" }}>
            <div className="idea-card-title">单篇复盘：{note.title}</div>
            <div
              className="page-subtitle"
              /* DOMPurify.sanitize 后注入 */
              dangerouslySetInnerHTML={{ __html: note.html }}
            />
          </div>
        )}
      </div>
    </>
  );
}
