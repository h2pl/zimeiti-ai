/** 内容日历——参考: Easel CalendarPage（发布事件按日期倒序表）。 */
import { useEffect, useState } from "react";
import type { CalEvent } from "../lib/api";
import { fetchCalendar } from "../lib/api";
import { IconCalendar } from "./icons";

export default function CalendarPage() {
  const [events, setEvents] = useState<CalEvent[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchCalendar()
      .then(setEvents)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  return (
    <>
      <div className="page-head">
        <div>
          <div className="page-title">
            <IconCalendar />
            内容日历
          </div>
          <div className="page-subtitle">发布事件按日期归档（只读，来源运营数据底座）</div>
        </div>
      </div>
      <div className="page-body">
        {error && <div className="notice-error">加载失败：{error}</div>}
        {events !== null && events.length === 0 && (
          <div className="empty-state">
            <div className="empty-icon">📅</div>
            <h3>还没有发布记录</h3>
            <p>托管循环完成发布并读回核实后，事件会出现在这里。</p>
          </div>
        )}
        {events && events.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>日期</th>
                <th>标题</th>
                <th>平台</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              {events.map((e, i) => (
                <tr key={i}>
                  <td>{e.date}</td>
                  <td>{e.title}</td>
                  <td>
                    <span className="badge badge-accent">{e.platform}</span>
                  </td>
                  <td>
                    <span className={e.status === "ok" ? "badge badge-ok" : "badge badge-warn"}>
                      {e.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
