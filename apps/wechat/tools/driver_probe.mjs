/**
 * 探针驱动（供 apps/scripts/probe_wechat_bridge.py 调用）：
 * 真实 ZimeitiClient（指向 ZIMEITI_API）+ 假 ilink transport，跑若干条入站消息，
 * 以 JSON 输出每次回发。不接真微信、不消耗 token（zimeiti 无密钥时优雅降级）。
 *
 * 用法：ZIMEITI_API=http://127.0.0.1:8123 WECHAT_STATE_DIR=<tmp> node driver_probe.mjs
 * stdin：JSON 数组 [{from_user_id, content}, ...]
 */

import { Dispatcher } from "../src/dispatcher.js";

async function main() {
  const { ZimeitiClient } = await import("../src/zimeiti-client.js");
  const chunks = [];
  for await (const c of process.stdin) chunks.push(c);
  const messages = JSON.parse(Buffer.concat(chunks).toString("utf8") || "[]");

  const client = new ZimeitiClient({ timeoutMs: 30_000 });
  const sent = [];
  const typings = [];
  const transport = {
    typing: async ({ to }) => { typings.push(to); },
    send: async ({ to, body }) => { sent.push({ to, content: body.content }); return { ret: 0 }; },
  };
  const dispatcher = new Dispatcher({ client, transport });
  const sessionIds = [];
  const origChat = client.chat.bind(client);
  client.chat = async (opts) => {
    sessionIds.push(opts.sessionId);
    return origChat(opts);
  };

  for (const m of messages) {
    await dispatcher.handle(m);
  }
  process.stdout.write(JSON.stringify({ sent, typings, sessionIds }, null, 2));
}

main().catch((e) => {
  process.stderr.write(String(e));
  process.exit(1);
});
