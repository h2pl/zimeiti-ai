import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import type { Board } from "../api";

const STATUSES = ["待做", "进行中", "已完成"];

/** 选题看板（P1⑪，Easel IdeasPage 对标）。 */
export default function Ideas() {
  const [board, setBoard] = useState<Board>({});
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    setBoard(await api.kanban().catch(() => ({})));
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const move = async (title: string, status: string) => {
    setBusy(true);
    try {
      await api.move(title, status);
      await refresh();
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
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
    </>
  );
}
