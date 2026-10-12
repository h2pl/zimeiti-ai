/** 运维操作（feat-skill-runner：技能卡片 + 参数化触发）——Easel SkillPage 对标。 */
import { useCallback, useEffect, useState } from "react";
import { fetchProfiles, fetchTools, triggerOps } from "../lib/api";
import { IconList } from "./icons";

interface SkillDef {
  id: "hosted_content" | "ops_data";
  name: string;
  desc: string;
  params: { account?: boolean; direction?: boolean };
}

const SKILLS: SkillDef[] = [
  {
    id: "hosted_content",
    name: "托管循环（选题+创作）",
    desc: "为指定账号触发一轮选题与创作，中断在人工闸门等待审批",
    params: { account: true, direction: true },
  },
  {
    id: "ops_data",
    name: "数据取数+校准",
    desc: "双平台指标取数（T-1）并按量触发策略校准",
    params: {},
  },
];

export default function SkillPage() {
  const [accounts, setAccounts] = useState<{ account: string }[]>([]);
  const [tools, setTools] = useState<{ name: string; description: string }[]>([]);
  const [form, setForm] = useState<Record<string, { account: string; direction: string }>>({});
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<{ text: string; ok: boolean } | null>(null);

  const showToast = (text: string, ok = true) => {
    setToast({ text, ok });
    setTimeout(() => setToast(null), 2600);
  };

  const load = useCallback(() => {
    fetchProfiles()
      .then((a) => {
        setAccounts(a);
        setForm((f) => {
          const init = { ...f };
          for (const s of SKILLS) {
            if (!init[s.id]) init[s.id] = { account: a[0]?.account ?? "", direction: "" };
          }
          return init;
        });
      })
      .catch(() => setAccounts([]));
    fetchTools().then(setTools).catch(() => setTools([]));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const run = async (skill: SkillDef) => {
    const f = form[skill.id] || { account: "", direction: "" };
    const params: Record<string, string> = {};
    if (skill.params.account && f.account) params.account = f.account;
    if (skill.params.direction && f.direction.trim()) params.direction = f.direction.trim();
    setBusy(true);
    try {
      await triggerOps(skill.id, params);
      showToast(`已触发「${skill.name}」，网关下一循环执行`);
    } catch (e) {
      showToast(e instanceof Error ? e.message : String(e), false);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <div className="page-head">
        <div>
          <div className="page-title">
            <IconList />
            运维操作
          </div>
          <div className="page-subtitle">
            技能卡片：填写参数手动触发（写入标记，由常驻网关下一循环原子消费执行）
          </div>
        </div>
      </div>
      <div className="page-body">
        <div className="section-title">技能</div>
        {SKILLS.map((s) => (
          <div key={s.id} className="card idea-card" style={{ marginBottom: 10 }}>
            <div className="idea-card-title">{s.name}</div>
            <div className="idea-card-direction">{s.desc}</div>
            <div className="options">
              {s.params.account && (
                <>
                  <span className="page-subtitle">账号</span>
                  <select
                    className="field"
                    style={{ maxWidth: 180 }}
                    value={form[s.id]?.account ?? ""}
                    onChange={(e) =>
                      setForm((f) => ({
                        ...f,
                        [s.id]: { ...(f[s.id] || { account: "", direction: "" }), account: e.target.value },
                      }))
                    }
                  >
                    {accounts.map((a) => (
                      <option key={a.account} value={a.account}>
                        {a.account}
                      </option>
                    ))}
                  </select>
                </>
              )}
              {s.params.direction && (
                <input
                  className="field"
                  style={{ maxWidth: 280 }}
                  placeholder="选题方向（留空=信息源发现）"
                  value={form[s.id]?.direction ?? ""}
                  onChange={(e) =>
                    setForm((f) => ({
                      ...f,
                      [s.id]: { ...(f[s.id] || { account: "", direction: "" }), direction: e.target.value },
                    }))
                  }
                />
              )}
              <button
                className="btn btn-sm btn-primary"
                disabled={busy}
                onClick={() => void run(s)}
              >
                运行
              </button>
            </div>
          </div>
        ))}
        <div className="section-title">Agent 工具清单（{tools.length}）</div>
        {tools.map((t) => (
          <div key={t.name} className="card idea-card" style={{ marginBottom: 8 }}>
            <div className="idea-card-title">{t.name}</div>
            <div className="idea-card-direction">{t.description}</div>
          </div>
        ))}
      </div>
      {toast && <div className={toast.ok ? "toast ok" : "toast err"}>{toast.text}</div>}
    </>
  );
}
