import { useEffect, useState } from "react";
import { api } from "../api";
import type { LogEntry } from "../api";

/** 执行日志页。 */
export default function Logs() {
  const [log, setLog] = useState<LogEntry[]>([]);

  useEffect(() => {
    const load = () => void api.logs().then((l) => setLog(l.reverse())).catch(() => {});
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, []);

  return (
    <>
      <h2>执行日志</h2>
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
    </>
  );
}
