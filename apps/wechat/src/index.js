#!/usr/bin/env node
/**
 * zimeiti 微信通道桥 CLI。
 *
 *   node src/index.js login     扫码登录（终端二维码）
 *   node src/index.js status    登录态 / 会话映射 / 协议码版本自检
 *   node src/index.js version   协议码与桥的版本
 *   node src/index.js start     常驻桥接（wechat-bridge-transport 启用，本期占位）
 *
 * 退出码：0 成功；1 运行错误；2 用法错误。
 */

import { login, status } from "./login.js";
import { listBindings } from "./sessions.js";
import { VENDOR_DIR } from "./config.js";
import { readFile } from "node:fs/promises";
import path from "node:path";

const USAGE = `zimeiti 微信通道桥（vendor 腾讯 ilink 协议码，不依赖 openclaw）

用法：
  node src/index.js login     扫码登录微信（终端显示二维码）
  node src/index.js status    登录态 / 会话映射自检
  node src/index.js version   协议码与桥版本
  node src/index.js start     常驻桥接（需 wechat-bridge-transport 变更）
`;

async function vendorVersion() {
  try {
    return (await readFile(path.join(VENDOR_DIR, "VERSION"), "utf8")).trim();
  } catch {
    return "(unknown)";
  }
}

async function main(argv) {
  const [cmd] = argv;
  if (!cmd || cmd === "help" || cmd === "--help" || cmd === "-h") {
    process.stdout.write(USAGE);
    return cmd ? 0 : 2;
  }
  if (cmd === "version") {
    process.stdout.write(`bridge=0.1.0 protocol=@tencent-weixin/openclaw-weixin@${await vendorVersion()}\n`);
    return 0;
  }
  if (cmd === "login") {
    const r = await login({});
    process.stdout.write(`${r.message}\n`);
    return r.ok ? 0 : 1;
  }
  if (cmd === "status") {
    const s = await status();
    if (!s.loggedIn) {
      process.stdout.write("未登录。执行 `node src/index.js login` 扫码连接微信。\n");
      return 1;
    }
    const bindings = await listBindings();
    for (const a of s.accounts) {
      process.stdout.write(
        `已登录：${a.accountId}（baseUrl=${a.baseUrl}，连接于 ${new Date(a.connectedAt).toLocaleString()}）\n`,
      );
    }
    const n = Object.keys(bindings).length;
    process.stdout.write(`会话映射：${n} 个微信用户\n`);
    return 0;
  }
  if (cmd === "start") {
    process.stderr.write(
      "常驻桥接尚未启用——需要变更 wechat-bridge-transport（把入站消息桥到 zimeiti）。\n",
    );
    return 1;
  }
  process.stderr.write(`未知命令：${cmd}\n${USAGE}`);
  return 2;
}

main(process.argv.slice(2))
  .then((code) => process.exit(code))
  .catch((err) => {
    process.stderr.write(`错误：${String(err)}\n`);
    process.exit(1);
  });
