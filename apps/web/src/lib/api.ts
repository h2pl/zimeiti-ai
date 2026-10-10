/**
 * 集中 API 层——request<T> 封装与全量类型定义。
 * 参考: Easel web/frontend/src/lib/api.ts（错误取 FastAPI {detail}，而非泛化文案）。
 */

interface RequestInitExt extends RequestInit {
  // 预留：后续如需 AbortController/流式在此扩展
}

async function request<T>(url: string, options?: RequestInitExt): Promise<T> {
  const res = await fetch(url, { cache: 'no-store', ...options });
  if (!res.ok) {
    let detail = '';
    try {
      const j = await res.json();
      detail = (j && (j.detail || j.message)) || '';
    } catch { /* 非 JSON 错误体 */ }
    throw new Error(detail || `请求失败（${res.status} ${res.statusText}）`);
  }
  return res.json() as Promise<T>;
}

/* ── 类型定义（与后端契约逐字段对应） ─────────────────────────── */

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

/* ── 端点函数（动词开头，Easel 命名约定） ─────────────────────── */

export function fetchDashboard(): Promise<Dashboard> {
  return request('/api/dashboard');
}

export function fetchApprovals(): Promise<Approval[]> {
  return request('/api/approvals');
}

export function confirmApproval(threadId: string): Promise<{ last_message: string }> {
  return request(`/api/approvals/${threadId}/confirm`, { method: 'POST' });
}

export function rejectApproval(threadId: string): Promise<{ last_message: string }> {
  return request(`/api/approvals/${threadId}/reject`, { method: 'POST' });
}

export function answerQuestion(threadId: string, message: string): Promise<{ last_message: string }> {
  return request(`/api/questions/${threadId}/answer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });
}

export function fetchKanban(): Promise<Board> {
  return request<Board>('/api/kanban').catch(() => ({}) as Board);
}

export function moveCard(title: string, status: string): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>('/api/kanban/move', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, status }),
  });
}

export function fetchCalendar(): Promise<CalEvent[]> {
  return request<CalEvent[]>('/api/calendar').catch(() => [] as CalEvent[]);
}

export function fetchProfiles(): Promise<{ account: string; enabled: boolean }[]> {
  return request('/api/profiles');
}

export function fetchProfile(account: string): Promise<ProfileData> {
  return request(`/api/profiles/${account}`);
}

export function updateProfile(account: string, data: ProfileData): Promise<{ ok: boolean }> {
  return request(`/api/profiles/${account}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

export function fetchTrends(account: string): Promise<Trends> {
  return request(`/api/trends/${account}`);
}

export function fetchOutputs(account: string): Promise<OutputItem[]> {
  return request(`/api/outputs/${account}`);
}

export function fetchLogs(): Promise<LogEntry[]> {
  return request('/api/publish-log');
}
