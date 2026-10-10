/** 选题看板——参考: Easel IdeasPage（COLUMNS 常量 + kanban-* + 卡片操作 hover 显示）。 */
import { useCallback, useEffect, useMemo, useState } from "react";
import type { Board, Card } from "../lib/api";
import { fetchKanban, moveCard } from "../lib/api";
import { IconIdea } from "./icons";

const COLUMNS: { key: string; label: string; color: string }[] = [
  { key: "待做", label: "待做", color: "var(--text-tertiary)" },
  { key: "进行中", label: "进行中", color: "var(--amber)" },
  { key: "已完成", label: "已完成", color: "var(--green)" },
];

export default function IdeasPage() {
  const [board, setBoard] = useState<Board>({});
  const [toast, setToast] = useState<{ text: string; ok: boolean } | null>(null);

  const load = useCallback(() => {
    fetchKanban().then(setBoard).catch(() => {});
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const byStatus = useMemo(
    () =>
      Object.fromEntries(
        COLUMNS.map((c) => [c.key, board[c.key] || []]),
      ) as unknown as Record<string, Card[]>,
    [board],
  );

  const showToast = (text: string, ok = true) => {
    setToast({ text, ok });
    setTimeout(() => setToast(null), 2200);
  };

  const move = async (title: string, status: string) => {
    try {
      await moveCard(title, status);
      showToast(`已移动到「${status}」`);
      load();
    } catch (e) {
      showToast(e instanceof Error ? e.message : String(e), false);
    }
  };

  return (
    <>
      <div className="page-head">
        <div>
          <div className="page-title">
            <IconIdea />
            选题看板
          </div>
          <div className="page-subtitle">托管循环发现的选题卡在此流转：待做 → 进行中 → 已完成</div>
        </div>
      </div>
      <div className="kanban">
        {COLUMNS.map((col) => (
          <div key={col.key} className="kanban-col">
            <div className="kanban-col-head">
              <span className="kanban-dot" style={{ background: col.color }} />
              {col.label}
              <span className="kanban-count">{byStatus[col.key].length}</span>
            </div>
            <div className="kanban-list">
              {byStatus[col.key].length === 0 && (
                <div className="kanban-empty">暂无选题</div>
              )}
              {byStatus[col.key].map((it) => (
                <div key={it.title} className="card idea-card">
                  <div className="idea-card-title">{it.title}</div>
                  <div className="idea-card-direction">{it.direction}</div>
                  <div className="idea-card-actions">
                    {COLUMNS.filter((c) => c.key !== col.key).map((c) => (
                      <button key={c.key} className="btn" onClick={() => void move(it.title, c.key)}>
                        → {c.label}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
      {toast && <div className={toast.ok ? "toast ok" : "toast err"}>{toast.text}</div>}
    </>
  );
}
