#!/usr/bin/env node
/**
 * zimeiti 微信通道桥 CLI。
 *
 *   node src/index.js login     扫码登录（终端二维码）
 *   node src/index.js start     常驻桥接：微信 → zimeiti agent → 微信
 *   node src/index.js status    登录态 / 会话映射 / zimeiti 连通性自检
 *   node src/index.js version   协议码与桥的版本
 *
 * 退出码：0 成功；1 运行错误；2 用法错误。
 */

import { login, status, loadWeixinAccount, listIndexedWeixinAccountIds } from "./login.js";
import { listBindings } from "./sessions.js";
import { WechatBridge } from "./bridge.js";
import { Dispatcher } from "./dispatcher.js";
import { ZimeitiClient } from "./zimeiti-client.js";
import { IlinkTransport } from "./transport.js";
import { ILINK_BASE_URL, VENDOR_DIR } from "./config.js";
import { readFile } from "node:fs/promises";
import path from "node:path";

const USAGE = `zimeiti 微信通道桥（vendor 腾讯 ilink 协议码，不依赖 openclaw）

用法：
  node src/index.js login     扫码登录微信（终端显示二维码）
  node src/index.js start     常驻桥接（微信 ↔ zimeiti agent）
  node src/index.js status    登录态 / 会话映射 / zimeiti 连通性自检
  node src/index.js version   协议码与桥版本

环境变量：
  ZIMEITI_API           zimeiti 后端地址（默认 http://127.0.0.1:8000）
  WECHAT_STATE_DIR      运行态目录（默认 apps/wechat/state）
  WECHAT_ZIMEITI_TIMEOUT_MS  单轮对话超时（默认 180000）
`;

async function vendorVersion() {
  try {
    return (await readFile(path.join(VENDOR_DIR, "VERSION"), "utf8")).trim();
  } catch {
    return "(unknown)";
  }
}

/** 取一个已登录账号（当前单账号运行）。 */
async function pickAccount() {
  for (const id of listIndexedWeixinAccountIds()) {
    const acc = await loadWeixinAccount(id);
    if (acc?.botToken) return { accountId: id, acc };
  }
  return null;
}

async function cmdStart() {
  const picked = await pickAccount();
  if (!picked) {
    process.stderr.write("未登录。先执行 `node src/index.js login` 扫码连接微信。\n");
    return 1;
  }
  const client = new ZimeitiClient();
  const reachable = await client.ping();
  if (!reachable) {
    process.stderr.write(
      `⚠️ zimeiti 后端不可达（${process.env.ZIMEITI_API || "http://127.0.0.1:8000"}）。\n`
      + "请先启动服务（make api / make dev）——桥仍会启动，但消息将得不到回复。\n",
    );
  }
  const transport = new IlinkTransport({
    baseUrl: picked.acc.baseUrl || ILINK_BASE_URL,
    token: picked.acc.botToken,
  });
  const dispatcher = new Dispatcher({ client, transport });
  const bridge = new WechatBridge({
    token: picked.acc.botToken,
    baseUrl: picked.acc.baseUrl || ILINK_BASE_URL,
    transport,
    onMessage: (msg) => dispatcher.handle(msg),
  });

  process.stdout.write(
    `微信桥已启动：账号 ${picked.accountId} → ${process.env.ZIMEITI_API || "http://127.0.0.1:8000"}\n`
    + "在微信里对「小贝」说话即可；发「新会话」清空上下文。Ctrl+C 停止。\n",
  );
  const shutdown = async () => {
    process.stdout.write("\n正在停止…\n");
    await bridge.stop();
    process.exit(0);
  };
  process.on("SIGINT", shutdown);
  process.on("SIGTERM", shutdown);
  await bridge.start();
  return 0;
}

async function cmdStatus() {
  const s = await status();
  if (!s.loggedIn) {
    process.stdout.write("未登录。执行 `node src/index.js login` 扫码连接微信。\n");
    return 1;
  }
  const client = new ZimeitiClient();
  const reachable = await client.ping();
  const bindings = await listBindings();
  for (const a of s.accounts) {
    process.stdout.write(
      `已登录：${a.accountId}（baseUrl=${a.baseUrl}，连接于 ${new Date(a.connectedAt).toLocaleString()}）\n`,
    );
  }
  process.stdout.write(
    `zimeiti 后端：${reachable ? "可达 ✅" : "不可达 ❌（请 make api）"}`
    + `（${process.env.ZIMEITI_API || "http://127.0.0.1:8000"}）\n`,
  );
  process.stdout.write(`会话映射：${Object.keys(bindings).length} 个微信用户\n`);
  return reachable ? 0 : 1;
}

async function main(argv) {
  const [cmd] = argv;
  if (!cmd || cmd === "help" || cmd === "--help" || cmd === "-h") {
    process.stdout.write(USAGE);
    return cmd ? 0 : 2;
  }
  if (cmd === "version") {
    process.stdout.write(`bridge=0.2.0 protocol=@tencent-weixin/openclaw-weixin@${await vendorVersion()}\n`);
    return 0;
  }
  if (cmd === "login") {
    const r = await login({});
    process.stdout.write(`${r.message}\n`);
    return r.ok ? 0 : 1;
  }
  if (cmd === "start") return cmdStart();
  if (cmd === "status") return cmdStatus();
  process.stderr.write(`未知命令：${cmd}\n${USAGE}`);
  return 2;
}

main(process.argv.slice(2))
  .then((code) => process.exit(code))
  .catch((err) => {
    process.stderr.write(`错误：${String(err)}\n`);
    process.exit(1);
  });
