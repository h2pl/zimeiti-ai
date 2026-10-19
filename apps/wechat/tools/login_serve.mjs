/**
 * 联调登录助手：稳定跳转服务 + 登录流程。
 *
 * 背景（联调实测）：二维码约每 2 分钟自动刷新（上限 MAX_QR_REFRESH_COUNT 次），
 * 聊天里贴的码/链接在用户读到时就已过期，而每次刷新都让旧码作废——用户永远扫不到
 * 「当前」那个码。
 *
 * 解法：本地起一个 302 跳转服务，手机开一个固定地址，始终跳到最新有效码。
 *   node tools/login_serve.mjs            # 默认 0.0.0.0:8791
 *   PORT=9000 node tools/login_serve.mjs
 *
 * 成功后自动退出（桥可 start）。
 */

import http from "node:http";
import { login } from "../src/login.js";

const PORT = Number(process.env.PORT || 8791);
let latestUrl = "";
let done = false;

const server = http.createServer((req, res) => {
  if (req.url === "/health") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ ok: true, loggedIn: done, hasQr: Boolean(latestUrl) }));
    return;
  }
  if (!latestUrl) {
    res.writeHead(503, { "Content-Type": "text/plain; charset=utf-8" });
    res.end("二维码生成中，请稍候重试…");
    return;
  }
  // 302 到当前有效码（手机浏览器打开即见扫码页）
  res.writeHead(302, { Location: latestUrl });
  res.end();
});

// 捕获 stdout 里的 liteapp 链接（vendor displayQRCode 会打印）
const origWrite = process.stdout.write.bind(process.stdout);
process.stdout.write = (chunk, ...rest) => {
  const s = typeof chunk === "string" ? chunk : chunk.toString();
  const m = s.match(/https:\/\/liteapp\.weixin\.qq\.com\/q\/[^\s]+/);
  if (m) {
    latestUrl = m[0];
    process.stderr.write(`[login_serve] 当前有效码已更新\n`);
  }
  return origWrite(chunk, ...rest);
};

server.listen(PORT, "0.0.0.0", async () => {
  const nets = await import("node:os").then((os) => os.networkInterfaces());
  const ips = [];
  for (const list of Object.values(nets)) {
    for (const n of list || []) {
      if (n.family === "IPv4" && !n.internal) ips.push(n.address);
    }
  }
  process.stderr.write(
    `\n=== 请用手机（连同一 Wi-Fi）打开：http://${ips[0] || "<本机IP>"}:${PORT} ===\n`
    + `（会跳转到当前有效的扫码页；码刷新也不用怕，这个地址不变）\n`
    + `（登录窗口约 6 分钟，到期自动重新出码——本服务会一直等着）\n\n`,
  );
  // 循环重试：单次登录窗口约 6 分钟（3 次刷新上限），失败就重开——
  // 稳定地址不变，用户可以从容扫码（联调实测：聊天贴码有时效错配）。
  for (let attempt = 1; attempt <= 20 && !done; attempt += 1) {
    try {
      const r = await login({ accountId: process.env.WECHAT_LOGIN_ACCOUNT || "main", force: true });
      done = Boolean(r.ok);
      process.stderr.write(`\n=== 第 ${attempt} 次尝试：${r.message} ===\n`);
    } catch (e) {
      process.stderr.write(`\n=== 第 ${attempt} 次尝试异常：${String(e).slice(0, 120)} ===\n`);
    }
    if (!done) {
      process.stderr.write("[login_serve] 3 秒后重新出码…\n");
      await new Promise((r) => setTimeout(r, 3000));
    }
  }
  server.close();
  process.exit(done ? 0 : 1);
});
