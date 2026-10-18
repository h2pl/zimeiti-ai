/**
 * 扫码登录（wechat-bridge-scaffold）。
 *
 * 直接驱动 vendor 的 ilink 登录函数（零 openclaw 依赖）：
 *   startWeixinLoginWithQr → displayQRCode → waitForWeixinLogin
 * 成功后把登录态经 vendor accounts.saveWeixinAccount 落盘（shim 提供其依赖的
 * 两个 helper）。transport 可注入——单测不触网。
 */

import { mkdir } from "node:fs/promises";
import {
  startWeixinLoginWithQr,
  waitForWeixinLogin,
  displayQRCode,
} from "../vendor/openclaw-weixin/dist/src/auth/login-qr.js";
import {
  saveWeixinAccount,
  loadWeixinAccount,
  clearWeixinAccount,
  listIndexedWeixinAccountIds,
} from "../vendor/openclaw-weixin/dist/src/auth/accounts.js";
import { accountsFile, stateDir } from "./config.js";

export { loadWeixinAccount, clearWeixinAccount, listIndexedWeixinAccountIds };

/** 完整扫码登录流程。opts.transport 仅供测试注入（记录调用，不触网时由测试替换模块）。 */
export async function login(opts = {}) {
  await mkdir(stateDir(), { recursive: true });
  const accountId = opts.accountId || "default";
  const started = await startWeixinLoginWithQr({ accountId, force: true });
  if (!started.qrcodeUrl) {
    return { ok: false, message: started.message || "二维码获取失败" };
  }
  await displayQRCode(started.qrcodeUrl);
  process.stdout.write(`${started.message}\n（二维码 8 分钟内有效，扫码后按手机提示确认）\n`);

  const result = await waitForWeixinLogin({
    sessionKey: started.sessionKey,
    timeoutMs: opts.timeoutMs ?? 480_000,
    verbose: true,
  });
  if (!result.connected) {
    return { ok: false, message: result.message || "登录未完成" };
  }
  await saveWeixinAccount(result.accountId || accountId, {
    botToken: result.botToken,
    baseUrl: result.baseUrl,
    cdnBaseUrl: result.cdnBaseUrl || "",
    userId: result.userId,
    connectedAt: Date.now(),
  });
  return {
    ok: true,
    accountId: result.accountId || accountId,
    message: `已连接微信（账号 ${result.accountId || accountId}）`,
  };
}

/** 登录态自检（status 命令）。 */
export async function status() {
  const ids = listIndexedWeixinAccountIds();
  const accounts = [];
  for (const id of ids) {
    const acc = await loadWeixinAccount(id);
    if (acc?.botToken) {
      accounts.push({
        accountId: id,
        baseUrl: acc.baseUrl,
        connectedAt: acc.connectedAt,
        userId: acc.userId,
      });
    }
  }
  return { loggedIn: accounts.length > 0, accounts, accountsFile: accountsFile() };
}
