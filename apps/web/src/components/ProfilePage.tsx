/** 画像管理（查看+受控编辑）——参考: Easel ProfilePage 表单模式。 */
import { useCallback, useEffect, useState } from "react";
import type { ProfileData } from "../lib/api";
import { fetchProfile, fetchProfiles, updateProfile } from "../lib/api";
import { IconUser } from "./icons";

const FIELDS: { key: keyof ProfileData; label: string; multiline?: boolean }[] = [
  { key: "positioning", label: "定位" },
  { key: "style", label: "风格" },
  { key: "audience", label: "受众" },
  { key: "content_focus", label: "内容形态" },
  { key: "boundary", label: "红线", multiline: true },
  { key: "platform_rules", label: "平台规则", multiline: true },
  { key: "preferences", label: "偏好", multiline: true },
];

export default function ProfilePage() {
  const [accounts, setAccounts] = useState<{ account: string; enabled: boolean }[]>([]);
  const [current, setCurrent] = useState("");
  const [data, setData] = useState<ProfileData | null>(null);
  const [toast, setToast] = useState<{ text: string; ok: boolean } | null>(null);

  const showToast = (text: string, ok = true) => {
    setToast({ text, ok });
    setTimeout(() => setToast(null), 2200);
  };

  const loadAccounts = useCallback(() => {
    fetchProfiles().then(setAccounts).catch(() => setAccounts([]));
  }, []);

  useEffect(() => {
    loadAccounts();
  }, [loadAccounts]);

  const load = useCallback(async (account: string) => {
    setCurrent(account);
    fetchProfile(account).then(setData).catch((e) => showToast(e instanceof Error ? e.message : String(e), false));
  }, []);

  const save = async () => {
    if (!data) return;
    try {
      await updateProfile(current, data);
      showToast("已保存（git 可 diff 回滚）");
    } catch (e) {
      showToast(e instanceof Error ? e.message : String(e), false);
    }
  };

  return (
    <>
      <div className="page-head">
        <div>
          <div className="page-title">
            <IconUser />
            画像管理
          </div>
          <div className="page-subtitle">编辑经 fail-closed 校验（非法输入被拒绝且文件不变），写入即 git 可 diff 回滚</div>
        </div>
      </div>
      <div className="page-body">
        <div className="options">
          {accounts.map((a) => (
            <button
              key={a.account}
              className={a.account === current ? "chip active" : "chip"}
              onClick={() => void load(a.account)}
            >
              {a.account}
              {a.enabled ? "" : "（停用）"}
            </button>
          ))}
        </div>
        {data ? (
          <div style={{ maxWidth: 560, marginTop: 14 }}>
            {FIELDS.map((f) => (
              <div key={f.key}>
                <label className="field-label">{f.label}</label>
                {f.multiline ? (
                  <textarea
                    className="field"
                    rows={2}
                    value={String(data[f.key] ?? "")}
                    onChange={(e) => setData({ ...data, [f.key]: e.target.value })}
                  />
                ) : (
                  <input
                    className="field"
                    value={String(data[f.key] ?? "")}
                    onChange={(e) => setData({ ...data, [f.key]: e.target.value })}
                  />
                )}
              </div>
            ))}
            <button className="btn btn-primary" style={{ marginTop: 16 }} onClick={() => void save()}>
              保存
            </button>
          </div>
        ) : (
          <div className="dash-empty">选择一个账号查看画像</div>
        )}
      </div>
      {toast && <div className={toast.ok ? "toast ok" : "toast err"}>{toast.text}</div>}
    </>
  );
}
