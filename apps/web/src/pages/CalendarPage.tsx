import { useEffect, useState } from "react";
import { api } from "../api";
import type { CalEvent } from "../api";

/** 内容日历（P1⑪，Easel CalendarPage 对标）。 */
export default function CalendarPage() {
  const [events, setEvents] = useState<CalEvent[]>([]);

  useEffect(() => {
    void api.calendar().then(setEvents).catch(() => setEvents([]));
  }, []);

  return (
    <>
      <h2>内容日历（{events.length}）</h2>
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
              <td>{e.platform}</td>
              <td>{e.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
