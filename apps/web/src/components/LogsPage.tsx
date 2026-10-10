/** 执行日志页——Easel 范式。 */
import { useEffect, useState } from "react";
import type { LogEntry } from "../lib/api";
import { fetchLogs } from "../lib/api";
import { IconList } from "./icons";

export default function LogsPage() {
  const [log, setLog] = useState<LogEntry[]>([]);

  useEffect(() => {
    const load = () =>
      fetchLogs()
        .then((l) => setLog(l.reverse()))
        .catch(() => {});
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, []);

  return (
    <>
      <div className="page-head">
        <div>
          <div className="page-title">
            <IconList />
            执行日志
          </div>
          <div className="page-subtitle">全链路审计事件（JSONL 底座，只读）</div>
        </div>
      </div>
      <div className="page-body">
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
      </div>
    </>
  );
}
