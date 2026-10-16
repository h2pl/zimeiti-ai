import { useCallback, useEffect, useState } from 'react';
import {
  fetchAutomations, createAutomation, updateAutomation, deleteAutomation,
  runAutomationNow, fetchAutomationRuns,
} from '../lib/api';
import type { Automation, AutomationRun } from '../lib/api';
import { IconTrash, IconCalendar } from './icons';

const EMPTY = { name: '', kind: 'case', schedule: '08:00', payload: '' };

function fmtTime(ts: number): string {
  if (!ts) return '—';
  const d = new Date(ts * 1000);
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getMonth() + 1}/${d.getDate()} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

function fmtDuration(run: AutomationRun): string {
  if (!run.finished) return '进行中';
  const s = Math.max(0, run.finished - run.started);
  return s >= 60 ? `${Math.floor(s / 60)}分${s % 60}秒` : `${s}秒`;
}

export default function AutomationsPage() {
  const [items, setItems] = useState<Automation[]>([]);
  const [runs, setRuns] = useState<AutomationRun[]>([]);
  const [form, setForm] = useState<typeof EMPTY | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [toast, setToast] = useState('');

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([
      fetchAutomations().then((r) => r.automations || []),
      fetchAutomationRuns().then((r) => r.runs || []).catch(() => [] as AutomationRun[]),
    ])
      .then(([a, r]) => { setItems(a); setRuns(r); setError(''); })
      .catch((e) => setError(String((e as Error)?.message || e)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const flash = (msg: string) => { setToast(msg); window.setTimeout(() => setToast(''), 2500); };

  const submit = () => {
    if (!form || !form.name.trim()) { flash('请填写任务名称'); return; }
    createAutomation({
      name: form.name.trim(), kind: form.kind, schedule: form.schedule, payload: form.payload,
    })
      .then(() => { setForm(null); flash('已创建'); load(); })
      .catch((e) => flash(`创建失败：${(e as Error)?.message || e}`));
  };

  const toggle = (a: Automation) => {
    updateAutomation(a.id, { enabled: !a.enabled })
      .then(() => load())
      .catch((e) => flash(`更新失败：${(e as Error)?.message || e}`));
  };

  const runNow = (a: Automation) => {
    runAutomationNow(a.id)
      .then(() => {
        flash('已在后台开始执行，稍后刷新查看结果');
        window.setTimeout(load, 2000);  // 后台任务，延迟拉一次记录即可
      })
      .catch((e) => flash(`执行失败：${(e as Error)?.message || e}`));
  };

  const remove = (a: Automation) => {
    deleteAutomation(a.id).then(() => { flash('已删除'); load(); })
      .catch((e) => flash(`删除失败：${(e as Error)?.message || e}`));
  };

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h2>自动化</h2>
          <p className="page-sub">每天定时跑的运营任务：到点自动执行，重启不丢（任务存在数据库）。</p>
        </div>
        <button className="btn-primary" onClick={() => setForm(form ? null : { ...EMPTY })}>
          {form ? '取消' : '+ 新建任务'}
        </button>
      </div>

      {toast && <div className="toast">{toast}</div>}

      {form && (
        <div className="panel">
          <div className="form-row">
            <label>名称</label>
            <input value={form.name} placeholder="如：每日出稿"
              onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </div>
          <div className="form-row">
            <label>类型</label>
            <select value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })}>
              <option value="case">运营流程（跑完整运营 case）</option>
              <option value="prompt">自定义指令（按你写的指令跑一轮）</option>
            </select>
          </div>
          <div className="form-row">
            <label>每日时刻</label>
            <input type="time" value={form.schedule}
              onChange={(e) => setForm({ ...form, schedule: e.target.value })} />
          </div>
          {form.kind === 'prompt' && (
            <div className="form-row">
              <label>指令</label>
              <input value={form.payload} placeholder="如：找今天的 AI 热点并给三个角度"
                onChange={(e) => setForm({ ...form, payload: e.target.value })} />
            </div>
          )}
          <button className="btn-primary" onClick={submit}>保存</button>
        </div>
      )}

      {loading && <p className="page-empty">加载中…</p>}
      {error && <p className="page-empty">加载失败：{error}</p>}
      {!loading && !error && items.length === 0 && (
        <p className="page-empty">还没有定时任务。点右上角「新建任务」，比如每天早上 8 点自动出稿。</p>
      )}

      <div className="auto-list">
        {items.map((a) => (
          <div className={`auto-card${a.enabled ? '' : ' is-off'}`} key={a.id}>
            <div className="auto-main">
              <div className="auto-title">
                <IconCalendar size={14} />
                <strong>{a.name}</strong>
                <span className="tag">{a.kind === 'case' ? '运营流程' : '自定义指令'}</span>
                {!a.enabled && <span className="tag tag-off">已停用</span>}
              </div>
              <div className="auto-meta">
                每天 {a.schedule} · 下次 {fmtTime(a.next_run)}
                {a.last_run ? ` · 上次 ${fmtTime(a.last_run)}` : ''}
                {a.payload ? ` · ${a.payload.slice(0, 40)}` : ''}
              </div>
            </div>
            <div className="auto-actions">
              <button className="btn-ghost" onClick={() => toggle(a)}>{a.enabled ? '停用' : '启用'}</button>
              <button className="btn-ghost" onClick={() => runNow(a)}>立即执行</button>
              <button className="btn-ghost" onClick={() => remove(a)} title="删除">
                <IconTrash size={14} />
              </button>
            </div>
          </div>
        ))}
      </div>

      {runs.length > 0 && (
        <div className="panel">
          <h3>最近执行</h3>
          <div className="run-list">
            {runs.slice(0, 10).map((r) => (
              <div className="run-item" key={r.id}>
                <span className={`dot dot-${r.status}`} />
                <span className="run-time">{fmtTime(r.started)}</span>
                <span className="run-status">
                  {r.status === 'running' ? '执行中' : r.status === 'done' ? '成功' : '失败'}
                </span>
                <span className="run-dur">{fmtDuration(r)}</span>
                <span className="run-summary">{(r.summary || '').slice(0, 120)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
