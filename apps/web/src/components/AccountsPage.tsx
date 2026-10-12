/** 账号管理（启停切换/凭证/登录态）——Easel AccountsPage 对标。 */
import { useCallback, useEffect, useState } from "react";
import type { AccountDetail } from "../lib/api";
import { createAccount, deleteAccount, fetchAccounts, toggleAccount } from "../lib/api";
import { IconUser } from "./icons";

export default function AccountsPage() {
  const [accounts, setAccounts] = useState<AccountDetail[]>([]);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<{ text: string; ok: boolean } | null>(null);
  const [creating, setCreating] = useState(false);
  const [newAccount, setNewAccount] = useState("");
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  const showToast = (text: string, ok = true) => {
    setToast({ text, ok });
    setTimeout(() => setToast(null), 2200);
  };

  const load = useCallback(() => {
    fetchAccounts().then(setAccounts).catch(() => setAccounts([]));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const create = async () => {
    const account = newAccount.trim();
    if (!account) return;
    setBusy(true);
    try {
      await createAccount({
        account,
        positioning: "（待完善）",
        style: "（待完善）",
        audience: "（待完善）",
        content_focus: "图文",
        boundary: "",
        platform_rules: "",
        preferences: "",
      });
      showToast(`已创建 ${account}（画像待完善；凭证请用 seal CLI 补齐后发布门禁才放行）`);
      setNewAccount("");
      setCreating(false);
      load();
    } catch (e) {
      showToast(e instanceof Error ? e.message : String(e), false);
    } finally {
      setBusy(false);
    }
  };

  const remove = async (account: string) => {
    setBusy(true);
    try {
      const r = await deleteAccount(account);
      showToast(`已删除 ${account}（清理：${Object.keys(r.removed).join("、")}）`);
      setConfirmDelete(null);
      load();
    } catch (e) {
      showToast(e instanceof Error ? e.message : String(e), false);
    } finally {
      setBusy(false);
    }
  };

  const toggle = async (a: AccountDetail) => {
    setBusy(true);
    try {
      await toggleAccount(a.account, !a.enabled);
      showToast(a.enabled ? `已停用 ${a.account}（发布将被拒绝）` : `已启用 ${a.account}`);
      load();
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
            <IconUser />
            账号管理
          </div>
          <div className="page-subtitle">
            启停即时生效（停用后发布路由拒绝）；凭证与登录态仅展示存在性，重登走既有扫码链路
          </div>
        </div>
      </div>
      <div className="page-body">
        <div className="options" style={{ marginBottom: 12 }}>
          <button className="btn btn-primary btn-sm" onClick={() => setCreating(!creating)}>
            {creating ? "取消新建" : "+ 新建账号"}
          </button>
          {creating && (
            <>
              <input
                className="field"
                style={{ maxWidth: 220 }}
                placeholder="账号名（如 gzh-2 / xhs-matrix）"
                value={newAccount}
                onChange={(e) => setNewAccount(e.target.value)}
              />
              <button className="btn btn-sm" disabled={busy || !newAccount.trim()} onClick={() => void create()}>
                创建（占位画像，待完善）
              </button>
            </>
          )}
        </div>
        {accounts.length === 0 && <div className="dash-empty">尚未配置账号画像</div>}
        {accounts.map((a) => (
          <div key={a.account} className="card idea-card" style={{ marginBottom: 10 }}>
            <div className="idea-card-title">
              {a.account}{" "}
              <span className={a.enabled ? "badge badge-ok" : "badge badge-warn"}>
                {a.enabled ? "启用中" : "已停用"}
              </span>
            </div>
            <div className="idea-card-direction">
              凭证（.sealed）：{a.credentials_sealed ? "✅ 已加密保存" : "⛔ 缺失"}
              {a.login_state !== null && (
                <>　登录态：{a.login_state ? "✅ 存在" : "⛔ 缺失（先扫码登录）"}</>
              )}
            </div>
            <div className="idea-card-actions" style={{ display: "flex" }}>
              <button
                className={a.enabled ? "btn btn-sm btn-danger" : "btn btn-sm btn-primary"}
                disabled={busy}
                onClick={() => void toggle(a)}
              >
                {a.enabled ? "停用" : "启用"}
              </button>
              {confirmDelete === a.account ? (
                <>
                  <span className="status-bad">确认删除？（画像+凭证一并清除，不可恢复）</span>
                  <button className="btn btn-sm btn-danger" disabled={busy} onClick={() => void remove(a.account)}>
                    确认删除
                  </button>
                  <button className="btn btn-sm" onClick={() => setConfirmDelete(null)}>
                    取消
                  </button>
                </>
              ) : (
                <button className="btn btn-sm btn-danger" onClick={() => setConfirmDelete(a.account)}>
                  删除
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
      {toast && <div className={toast.ok ? "toast ok" : "toast err"}>{toast.text}</div>}
    </>
  );
}
