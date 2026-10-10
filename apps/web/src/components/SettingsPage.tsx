/** 设置页（通知 webhook）——Easel SettingsPanel 对标。 */
import { useCallback, useEffect, useState } from "react";
import { fetchAppSettings, updateAppSettings } from "../lib/api";

export default function SettingsPage() {
  const [webhook, setWebhook] = useState("");
  const [toast, setToast] = useState<{ text: string; ok: boolean } | null>(null);

  const showToast = (text: string, ok = true) => {
    setToast({ text, ok });
    setTimeout(() => setToast(null), 2200);
  };

  const load = useCallback(() => {
    fetchAppSettings()
      .then((s) => setWebhook(s.notify_webhook_url || ""))
      .catch(() => {});
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const save = async () => {
    try {
      await updateAppSettings({ notify_webhook_url: webhook.trim() });
      showToast("已保存，下一次通知即时生效");
    } catch (e) {
      showToast(e instanceof Error ? e.message : String(e), false);
    }
  };

  return (
    <>
      <div className="page-head">
        <div>
          <div className="page-title">设置</div>
          <div className="page-subtitle">通知 webhook（飞书/钉钉/企微/TG）；留空则静默不推送</div>
        </div>
      </div>
      <div className="page-body">
        <label className="field-label">通知 webhook URL</label>
        <input
          className="field"
          placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/…"
          value={webhook}
          onChange={(e) => setWebhook(e.target.value)}
        />
        <button className="btn btn-primary" style={{ marginTop: 14 }} onClick={() => void save()}>
          保存
        </button>
      </div>
      {toast && <div className={toast.ok ? "toast ok" : "toast err"}>{toast.text}</div>}
    </>
  );
}
