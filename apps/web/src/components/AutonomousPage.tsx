import { useCallback, useEffect, useState } from 'react';
import {
  fetchFlows, fetchFlowStepCatalog, createFlow, deleteFlow,
  fetchFlowRuns, fetchAutonomousStatus, fetchFeedback,
} from '../lib/api';
import type { Flow, FlowRun, StepOption, AutonomousStatus, FeedbackSignal } from '../lib/api';
import { IconAutonomous, IconTrash } from './icons';

const EMPTY = { name: '', steps: ['discover', 'plan'] as string[], schedule: '08:00', topic: '' };

function fmtTime(ms: number): string {
  if (!ms) return '—';
  const d = new Date(ms);
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getMonth() + 1}/${d.getDate()} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

function fmtDur(ms: number): string {
  const s = Math.max(0, Math.round((ms || 0) / 1000));
  return s >= 60 ? `${Math.floor(s / 60)}分${s % 60}秒` : `${s}秒`;
}

const STEP_LABEL: Record<string, string> = {
  discover: '发现', plan: '选题', produce: '创作', publish: '发布', review: '复盘',
};

export default function AutonomousPage() {
  const [items, setItems] = useState<Flow[]>([]);
  const [runs, setRuns] = useState<FlowRun[]>([]);
  const [catalog, setCatalog] = useState<StepOption[]>([]);
  const [status, setStatus] = useState<AutonomousStatus | null>(null);
  const [fb, setFb] = useState<FeedbackSignal | null>(null);
  const [form, setForm] = useState<typeof EMPTY | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [toast, setToast] = useState('');

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([
      fetchFlows().then((r) => r.flows || []).catch(() => [] as Flow[]),
      fetchFlowRuns().then((r) => r.runs || []).catch(() => [] as FlowRun[]),
      fetchFlowStepCatalog().then((r) => r.steps || []).catch(() => [] as StepOption[]),
      fetchAutonomousStatus().catch(() => null),
      fetchFeedback().catch(() => null),
    ])
      .then(([f, r, c, s, fbv]) => {
        setItems(f); setRuns(r); setCatalog(c); setStatus(s); setFb(fbv); setError('');
      })
      .catch((e) => setError(String((e as Error)?.message || e)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const flash = (msg: string) => { setToast(msg); window.setTimeout(() => setToast(''), 2200); };

  const toggleStep = (v: string) => {
    if (!form) return;
    const has = form.steps.includes(v);
    setForm({ ...form, steps: has ? form.steps.filter((s) => s !== v) : [...form.steps, v] });
  };

  const submit = () => {
    if (!form || !form.name.trim()) { flash('请填写流程名称'); return; }
    if (form.steps.length === 0) { flash('至少勾选一个步骤'); return; }
    createFlow({
      name: form.name.trim(),
      steps: form.steps as Flow['steps'],
      schedule: form.schedule,
      config: { topic: form.topic.trim(), draft_only: true },
    })
      .then(() => { setForm(null); flash('已创建'); load(); })
      .catch((e) => flash(`创建失败：${(e as Error)?.message || e}`));
  };

  const remove = (f: Flow) => {
    deleteFlow(f.id).then(() => { flash('已删除'); load(); })
      .catch((e) => flash(`删除失败：${(e as Error)?.message || e}`));
  };

  const budgetText = !status?.budget
    ? '—'
    : status.budget.unknown
      ? '未接入用量'
      : status.budget.error
        ? '用量不可用'
        : typeof status.budget.spent_usd === 'number'
          ? `≈ $${status.budget.spent_usd.toFixed(4)}${status.budget.partial ? '（部分未计价）' : ''}`
          : '未折算费用';

  const tripped = status?.circuit?.disabled_flows || [];

  return (
    <div className="page-scroll automations-page">
      <div className="page-head">
        <div>
          <h1 className="page-title"><IconAutonomous size={21} /> 自主运营</h1>
          <p className="page-subtitle">
            把运营链路托管给 agent：到点自动跑「发现→选题→创作→发布→复盘」，
            已发布的事实会回流校准下一轮选题。
          </p>
        </div>
        <button className="btn btn-sm btn-primary" onClick={() => setForm(form ? null : { ...EMPTY })}>
          {form ? '取消' : '+ 新建流程'}
        </button>
      </div>

      {toast && <div className="toast ok"><span className="toast-icon">✓</span>{toast}</div>}
      {error && <div className="notice-error">加载失败：{error}</div>}

      {status && (
        <div className="card auto-empty-card" style={{ textAlign: 'left' }}>
          <div className="usage-head">
            <strong>运行状态</strong>
            <span className="usage-unit">护栏：重试 / 熔断 / 预算 / 待确认</span>
          </div>
          <div className="usage-total">
            <span>当日预算 {budgetText}</span>
            <span>待确认 {status.blocked?.length ?? 0} 项</span>
            <span>熔断停用 {tripped.length} 条</span>
          </div>
          {tripped.length > 0 && (
            <div className="foot-note">
              连续失败已被护栏停用：{tripped.map((f) => f.name).join('、')}——修好后可在流程里重新启用。
            </div>
          )}
          {fb && (
            <div className="foot-note">
              选题校准信号：{fb.calibration}
            </div>
          )}
        </div>
      )}

      {loading && <p className="auto-empty">加载中…</p>}
      {!loading && !error && items.length === 0 && !form && (
        <div className="card auto-empty-card">
          还没有运营流程。点右上角「新建流程」，比如每天早上 8 点自动发现并选题。
        </div>
      )}

      {form && (
        <div className="panel auto-form">
          <div className="panel-title">新建运营流程</div>
          <label className="field-label" htmlFor="flow-name">流程名称</label>
          <input id="flow-name" className="field" value={form.name} placeholder="如：每日选题"
            onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <label className="field-label">执行步骤（按勾选顺序跑）</label>
          <div className="auto-steps">
            {(catalog.length ? catalog : Object.keys(STEP_LABEL).map((v) => ({ value: v, label: STEP_LABEL[v] })))
              .map((s) => (
                <label className="auto-step" key={s.value}>
                  <input type="checkbox" checked={form.steps.includes(s.value)}
                    onChange={() => toggleStep(s.value)} />
                  {s.label}
                </label>
              ))}
          </div>
          <label className="field-label" htmlFor="flow-schedule">每日时刻</label>
          <input id="flow-schedule" type="time" className="field" value={form.schedule}
            onChange={(e) => setForm({ ...form, schedule: e.target.value })} />
          <label className="field-label" htmlFor="flow-topic">主题/方向（可选）</label>
          <input id="flow-topic" className="field" value={form.topic} placeholder="如：AI 工具测评"
            onChange={(e) => setForm({ ...form, topic: e.target.value })} />
          <div style={{ marginTop: 14 }}>
            <button className="btn btn-sm btn-primary" onClick={submit}>保存</button>
          </div>
        </div>
      )}

      <div className="auto-list">
        {items.map((f) => (
          <div className={`card auto-card${f.enabled ? '' : ' auto-card-off'}`} key={f.id}>
            <div className="auto-main">
              <div className="auto-title">
                <IconAutonomous size={14} />
                <strong>{f.name}</strong>
                {(f.steps || []).map((s) => (
                  <span className="badge badge-accent" key={s}>{STEP_LABEL[s] || s}</span>
                ))}
                {!f.enabled && <span className="badge badge-warn">已停用</span>}
              </div>
              <div className="auto-meta">
                每天 {f.schedule || '—'}
                {f.config?.topic ? ` · 主题 ${f.config.topic}` : ''}
                {f.config?.draft_only ? ' · 只出草稿' : ''}
              </div>
            </div>
            <div className="auto-actions">
              <button className="session-act danger" title="删除" onClick={() => remove(f)}>
                <IconTrash size={13} />
              </button>
            </div>
          </div>
        ))}
      </div>

      {runs.length > 0 && (
        <div className="panel auto-runs">
          <div className="panel-title">最近执行</div>
          <div className="run-list">
            {runs.slice(0, 10).map((r) => (
              <div className="run-item" key={r.id}>
                <span className={`dot dot-${r.status}`} />
                <span className="run-time">{fmtTime(r.started)}</span>
                <span className="run-status">
                  {r.status === 'running' ? '执行中' : r.status === 'done' ? '成功' : '失败'}
                  {r.failed_step ? `（${STEP_LABEL[r.failed_step] || r.failed_step}）` : ''}
                </span>
                <span className="run-dur">{fmtDur(r.duration_ms)}</span>
                <span className="run-summary">
                  {(r.steps || []).map((s) => `${STEP_LABEL[s.step] || s.step}:${
                    s.status === 'done' ? '完成' : s.status === 'blocked' ? '待确认'
                      : s.status === 'failed' ? '失败' : '进行中'}`).join(' · ')}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="foot-note">
        立即执行会真实消耗模型额度，页面不提供一键执行；流程由调度器到点自动执行。
      </div>
    </div>
  );
}
