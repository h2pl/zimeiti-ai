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

import { login, loadWeixinAccount, listIndexedWeixinAccountIds } from "./login.js";
import { listBindings } from "./sessions.js";
import { WechatBridge } from "./bridge.js";
import { Dispatcher } from "./dispatcher.js";
import { ZimeitiClient } from "./zimeiti-client.js";
import { IlinkTransport } from "./transport.js";
import { ILINK_BASE_URL, VENDOR_DIR, zimeitiBase } from "./config.js";
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

/** 全部已登录账号（多账号并行，wechat-bridge-ops）。 */
async function loadAccounts() {
  const out = [];
  for (const id of listIndexedWeixinAccountIds()) {
    const acc = await loadWeixinAccount(id);
    if (acc?.botToken) out.push({ accountId: id, acc });
  }
  return out;
}

async function cmdStart() {
  const accounts = await loadAccounts();
  if (!accounts.length) {
    process.stderr.write("未登录。先执行 `node src/index.js login` 扫码连接微信。\n");
    return 1;
  }
  const client = new ZimeitiClient();
  const reachable = await client.ping();
  if (!reachable) {
    process.stderr.write(
      `⚠️ zimeiti 后端不可达（${zimeitiBase()}）。\n`
      + "请先启动服务（make api / make dev）——桥仍会启动，但消息将得不到回复。\n",
    );
  }

  // 每账号一个桥实例并行；单账号崩溃隔离（wechat-bridge-ops D3）
  const loops = accounts.map(({ accountId, acc }) => {
    const transport = new IlinkTransport({
      baseUrl: acc.baseUrl || ILINK_BASE_URL,
      token: acc.botToken,
    });
    const bot = { id: acc.ilinkBotId || accountId, name: acc.name || "" };
    const dispatcher = new Dispatcher({
      client,
      transport,
      bot,
      ilinkOpts: {
        baseUrl: acc.baseUrl || ILINK_BASE_URL,
        token: acc.botToken,
        cdnBaseUrl: acc.cdnBaseUrl || "",
      },
    });
    const bridge = new WechatBridge({
      token: acc.botToken,
      baseUrl: acc.baseUrl || ILINK_BASE_URL,
      transport,
      onMessage: (msg) => dispatcher.handle(msg),
    });
    return bridge.start().catch((err) => {
      process.stderr.write(`[${accountId}] 桥实例退出：${String(err)}\n`);
    });
  });

  process.stdout.write(
    `微信桥已启动：${accounts.length} 个账号 → ${zimeitiBase()}\n`
    + accounts.map((a) => `  - ${a.accountId}`).join("\n")
    + "\n在微信里对机器人说话即可；发「新会话」清空上下文；群里需@机器人。Ctrl+C 停止。\n",
  );
  const shutdown = async () => {
    process.stdout.write("\n正在停止…\n");
    process.exit(0);
  };
  process.on("SIGINT", shutdown);
  process.on("SIGTERM", shutdown);
  await Promise.allSettled(loops);
  return 0;
}

async function cmdStatus() {
  const accounts = await loadAccounts();
  if (!accounts.length) {
    process.stdout.write("未登录。执行 `node src/index.js login` 扫码连接微信。\n");
    return 1;
  }
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
