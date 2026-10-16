import { useCallback, useEffect, useState } from 'react';
import { fetchUsage } from '../lib/api';
import type { UsageSummary } from '../lib/api';

interface UsageCardProps {
  /** compact：工作台卡片（只显示汇总）；full：设置面板（带明细） */
  variant?: 'compact' | 'full';
}

export default function UsageCard({ variant = 'compact' }: UsageCardProps) {
  const [data, setData] = useState<UsageSummary | null>(null);
  const [error, setError] = useState('');
  const [days, setDays] = useState(30);

  const load = useCallback(() => {
    fetchUsage(undefined, days)
      .then((d) => { setData(d); setError(''); })
      .catch((e) => setError(String((e as Error)?.message || e)));
  }, [days]);

  useEffect(() => { load(); }, [load]);

  if (error) return <div className="usage-card">用量加载失败：{error}</div>;
  if (!data) return <div className="usage-card">用量加载中…</div>;

  const empty = (data.total_prompt || 0) + (data.total_completion || 0) === 0;

  return (
    <div className={`usage-card usage-${variant}`}>
      <div className="usage-head">
        <strong>用量</strong>
        {variant === 'full' && (
          <select value={days} onChange={(e) => setDays(Number(e.target.value))}>
            <option value={7}>近 7 天</option>
            <option value={30}>近 30 天</option>
            <option value={90}>近 90 天</option>
          </select>
        )}
      </div>
      {empty ? (
        <p className="usage-empty">暂无用量数据——开始对话后这里会累计。</p>
      ) : (
        <>
          <div className="usage-total">
            <span>输入 {data.total_prompt.toLocaleString()}</span>
            <span>输出 {data.total_completion.toLocaleString()}</span>
            <span className="usage-unit">token（未折算费用）</span>
          </div>
          {variant === 'full' && (
            <div className="usage-rows">
              {data.rows.map((r, i) => (
                <div className="usage-row" key={`${r.session_key}-${r.model}-${i}`}>
                  <span className="usage-session">{r.session_key || '(默认)'}</span>
                  <span className="usage-model">{r.model || '(未上报)'}</span>
                  <span>{r.prompt_tokens.toLocaleString()} / {r.completion_tokens.toLocaleString()}</span>
                  <span className="usage-turns">{r.turns} 轮</span>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
