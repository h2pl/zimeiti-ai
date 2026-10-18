/**
 * shim: openclaw/plugin-sdk/account-id — normalizeAccountId
 *
 * 依据（取证）：vendor 协议码中仅 accounts.js 与 channel.js 引用此 helper，
 * 用途是把账号标识规范化后作为配置键/目录名。语义等价实现：
 * 去首尾空白 → 小写 → 仅保留 [a-z0-9_-] → 限长 64 → 空值兜底 "default"。
 */

export function normalizeAccountId(raw) {
  const cleaned = String(raw ?? "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_-]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 64);
  return cleaned || "default";
}

export default { normalizeAccountId };
