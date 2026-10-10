import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import type { ProfileData } from "../api";

const FIELDS: { key: keyof ProfileData; label: string; multiline?: boolean }[] = [
  { key: "positioning", label: "定位" },
  { key: "style", label: "风格" },
  { key: "audience", label: "受众" },
  { key: "content_focus", label: "内容形态" },
  { key: "boundary", label: "红线", multiline: true },
  { key: "platform_rules", label: "平台规则", multiline: true },
  { key: "preferences", label: "偏好", multiline: true },
];

/** 画像管理（查看+受控编辑，PUT fail-closed）。 */
export default function Profile() {
  const [accounts, setAccounts] = useState<{ account: string; enabled: boolean }[]>([]);
  const [current, setCurrent] = useState<string>("");
  const [data, setData] = useState<ProfileData | null>(null);
  const [msg, setMsg] = useState("");

  const loadAccounts = useCallback(async () => {
    setAccounts(await api.profiles().catch(() => []));
  }, []);

  useEffect(() => {
    void loadAccounts();
  }, [loadAccounts]);

  const load = useCallback(async (account: string) => {
    setCurrent(account);
    setMsg("");
    setData(await api.profile(account).catch(() => null));
  }, []);

  const save = async () => {
    if (!data) return;
    try {
      await api.saveProfile(current, data);
      setMsg("✅ 已保存");
    } catch (e) {
      setMsg(`⛔ ${e instanceof Error ? e.message : String(e)}`);
    }
  };

  return (
    <>
      <h2>画像管理</h2>
      <div className="options">
        {accounts.map((a) => (
          <button
            key={a.account}
            className={a.account === current ? "active" : ""}
            onClick={() => void load(a.account)}
          >
            {a.account} {a.enabled ? "" : "（停用）"}
          </button>
        ))}
      </div>
      {data ? (
        <div className="form">
          {FIELDS.map((f) => (
            <label key={f.key}>
              {f.label}
              {f.multiline ? (
                <textarea
                  rows={2}
                  value={String(data[f.key] ?? "")}
                  onChange={(e) => setData({ ...data, [f.key]: e.target.value })}
                />
              ) : (
                <input
                  value={String(data[f.key] ?? "")}
                  onChange={(e) => setData({ ...data, [f.key]: e.target.value })}
                />
              )}
            </label>
          ))}
          <button disabled={!current} onClick={() => void save()}>
            保存
          </button>
          {msg && <span className="meta">{msg}</span>}
        </div>
      ) : (
        <p className="empty">选择一个账号查看画像</p>
      )}
    </>
  );
}
