/**
 * 媒体探针驱动（供 probe_wechat_media.py 调用）：
 * 真实 Dispatcher + 假下载器/假发送器，验证入站媒体落盘附注与出站 MEDIA 回发。
 */

import path from "node:path";
import { Dispatcher } from "../src/dispatcher.js";
import { ZimeitiClient } from "../src/zimeiti-client.js";

async function main() {
  const client = new ZimeitiClient({ timeoutMs: 30_000 });
  const sent = [];
  const mediaSent = [];
  const seen = [];
  const transport = {
    typing: async () => ({}),
    send: async ({ to, body }) => { sent.push({ to, content: body.content }); },
  };
  const dispatcher = new Dispatcher({
    client: {
      chat: async (o) => {
        seen.push(o.message);
        if (o.message.includes("做张海报")) {
          return "这是海报\nMEDIA:/tmp/poster.png";
        }
        return "收到";
      },
    },
    transport,
    mediaHooks: {
      downloadMedia: async () => ({ buffer: Buffer.from("FAKEPNG"), meta: {} }),
      sendMedia: async ({ filePath, to, text }) => { mediaSent.push({ filePath, to, text }); },
    },
  });

  // 入站图片（item_list 带 IMAGE）
  await dispatcher.handle({
    from_user_id: "u-media",
    content: "",
    item_list: [
      { type: 1, text: "" },
      { type: 2, aeskey: "aabb", image_item: { media: { full_url: "https://cdn/a.bin", encrypt_query_param: "e", aes_key: "a2FiYw==" } } },
    ],
  });

  // 出站 MEDIA
  await dispatcher.handle({ from_user_id: "u-media", content: "做张海报" });

  const fs = await import("node:fs");
  const mediaDir = path.join(
    process.env.WECHAT_STATE_DIR || new URL("../state", import.meta.url).pathname,
    "media",
  );
  const mediaDirFiles = fs.existsSync(mediaDir)
    ? fs.readdirSync(mediaDir, { recursive: true }).filter((f) => String(f).endsWith(".png"))
    : [];
  process.stdout.write(JSON.stringify({ sent, mediaSent, agentSaw: seen, mediaDirFiles }, null, 2));
}

main().catch((e) => { process.stderr.write(String(e)); process.exit(1); });
