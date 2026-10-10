/** 类型化 API 客户端（D2：fetch 封装单点维护，页面不直接 fetch）。 */

export interface Approval {
  thread_id: string;
  instruction: string;
  account?: string;
  kind?: string;
  question?: string;
  options?: string[];
}

export interface LogEntry {
  ts: string;
  action: string;
  thread_id?: string;
}

export interface Dashboard {
  pending_approvals: number;
  accounts: Record<string, boolean>;
  today_publishes: number;
  recent_log: LogEntry[];
}

export interface Card {
  title: string;
  reason: string;
  direction: string;
  source: string;
}

export type Board = Record<string, Card[]>;

export interface CalEvent {
  date: string;
  title: string;
  platform: string;
  status: string;
}

export interface ProfileData {
  account: string;
  positioning: string;
  style: string;
  audience: string;
  content_focus: string;
  boundary: string;
  platform_rules: string;
  preferences: string;
  enabled?: boolean;
  [k: string]: unknown;
}

export interface TrendBaseline {
  mean: number;
  latest: number;
  normalized: number | null;
}

export interface Trends {
  platform: string;
  events: number;
  snapshots: number;
  baseline: Record<string, TrendBaseline>;
  lifecycle_distribution: Record<string, number>;
  rhythm: Record<string, number>;
}

export interface OutputItem {
  slug: string;
  title: string;
  topic: string;
  compliance_passed: boolean;
  created_at: string;
}

async function get<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url}: ${r.status}`);
  return r.json();
}

async function send<T>(url: string, method: string, body?: unknown): Promise<T> {
  const r = await fetch(url, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) {
    const detail = await r.json().catch(() => ({}));
    throw new Error(detail.detail || `${url}: ${r.status}`);
  }
  return r.json();
}

export const api = {
  dashboard: () => get<Dashboard>("/api/dashboard"),
  approvals: () => get<Approval[]>("/api/approvals"),
  confirm: (id: string) => send<{ last_message: string }>(`/api/approvals/${id}/confirm`, "POST"),
  reject: (id: string) => send(`/api/approvals/${id}/reject`, "POST"),
  answer: (id: string, message: string) =>
    send<{ last_message: string }>(`/api/questions/${id}/answer`, "POST", { message }),
  kanban: () => get<Board>("/api/kanban"),
  move: (title: string, status: string) =>
    send("/api/kanban/move", "POST", { title, status }),
  calendar: () => get<CalEvent[]>("/api/calendar"),
  profiles: () => get<{ account: string; enabled: boolean }[]>("/api/profiles"),
  profile: (account: string) => get<ProfileData>(`/api/profiles/${account}`),
  saveProfile: (account: string, data: ProfileData) =>
    send(`/api/profiles/${account}`, "PUT", data),
  trends: (account: string) => get<Trends>(`/api/trends/${account}`),
  outputs: (account: string) => get<OutputItem[]>(`/api/outputs/${account}`),
  logs: () => get<LogEntry[]>("/api/publish-log"),
};
