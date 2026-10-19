/**
 * 联调用登录驱动：出二维码 → 等扫码 → 落盘账号。
 * 与 index.js login 的区别：把 waitForWeixinLogin 的轮询过程也打出来，
 * 便于联调时看到「已扫码/已确认」的中间态。
 */

import {
  startWeixinLoginWithQr,
  displayQRCode,
  waitForWeixinLogin,
} from "../vendor/openclaw-weixin/dist/src/auth/login-qr.js";
import { saveWeixinAccount } from "../src/login.js";

const ACCOUNT_ID = process.env.WECHAT_LOGIN_ACCOUNT || "main";

async function main() {
  const started = await startWeixinLoginWithQr({ accountId: ACCOUNT_ID });
  if (!started?.qrcodeUrl) {
    process.stderr.write(`出码失败：${started?.message || "无二维码"}\n`);
    process.exit(1);
  }
  process.stdout.write("\n===== 请用手机微信扫下面这个码（8 分钟内有效）=====\n\n");
  await displayQRCode(started.qrcodeUrl);
  process.stdout.write("\n（若终端二维码糊，可用上面 printed 的链接在手机打开）\n");
  process.stdout.write("等待扫码……\n");

  const deadline = Date.now() + 7 * 60 * 1000;
  let lastPhase = "";
  while (Date.now() < deadline) {
    const r = await waitForWeixinLogin({ sessionKey: started.sessionKey, timeoutMs: 20000 });
    if (r?.connected) {
      await saveWeixinAccount(r.accountId || ACCOUNT_ID, {
        botToken: r.botToken,
        baseUrl: r.baseUrl,
        cdnBaseUrl: r.cdnBaseUrl || "",
        userId: r.userId,
        ilinkBotId: r.accountId || ACCOUNT_ID,
      });
      process.stdout.write(
        `\n✅ 登录成功！账号 ${r.accountId || ACCOUNT_ID}（userId=${r.userId || "?"}）\n`,
      );
      process.stdout.write("登录态已落盘。现在可以：node src/index.js start\n");
      return;
    }
    const phase = String(r?.message || "").slice(0, 60);
    if (phase && phase !== lastPhase) {
      process.stdout.write(`  … ${phase}\n`);
      lastPhase = phase;
    }
    if (r?.connected === false && /过期|重新/.test(String(r?.message || ""))) {
      process.stderr.write("二维码过期，请重新运行 login。\n");
      process.exit(1);
    }
  }
  process.stderr.write("等待超时（7 分钟）——请重新运行。\n");
  process.exit(1);
}

main().catch((e) => {
  process.stderr.write(String(e));
  process.exit(1);
});
