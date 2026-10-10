/** 运维操作（触发托管循环/取数/校准）+ agent 工具清单——Easel SkillPage 对标。 */
import { useCallback, useEffect, useState } from "react";
import { fetchTools, triggerOps } from "../lib/api";
import { IconList } from "./icons";

export default function SkillPage() {
  const [tools, setTools] = useState<{ name: string; description: string }[]>([]);
  const [toast, setToast] = useState<{ text: string; ok: boolean } | null>(null);

  const showToast = (text: string, ok = true) => {
    setToast({ text, ok });
    setTimeout(() => setToast(null), 2200);
  };

  const load = useCallback(() => {
    fetchTools().then(setTools).catch(() => setTools([]));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const trigger = async (job: "hosted_content" | "ops_data") => {
    try {
      const r = await triggerOps(job);
      showToast(`已触发 ${r.triggered}，网关下一循环执行`);
      load();
    } catch (e) {
      showToast(e instanceof Error ? e.message : String(e), false);
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
            手动触发运维任务（写入标记，由常驻网关下一循环消费执行）+ agent 工具清单
          </div>
        </div>
      </div>
      <div className="page-body">
        <div className="section-title">手动触发</div>
        <div className="options">
          <button className="btn btn-primary" onClick={() => void trigger("hosted_content")}>
            触发托管循环（选题+创作）
          </button>
          <button className="btn" onClick={() => void trigger("ops_data")}>
            立即取数+校准
          </button>
        </div>
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
