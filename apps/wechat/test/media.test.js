/**
 * wechat-bridge-media 单测（node:test，零网络：全部注入 fake 下载器/发送器）。
 */

import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, rm, readdir, stat } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";

const media = await import("../src/media.js");

// ── extractMediaItems ──────────────────────────────────────────────────────
test("extractMediaItems 从 item_list 提取各类型（vendor 字段名）", () => {
  const msg = {
    msg_id: "m1",
    item_list: [
      { type: 1, text: "看看这张" },
      {
        type: 2,
        aeskey: "aabb",
        image_item: {
          media: {
            full_url: "https://cdn.example/a.bin?enc=1",
            encrypt_query_param: "enc=1",
            aes_key: "a2FiYw==",
          },
        },
      },
      { type: 3, voice_item: { media: { full_url: "https://cdn.example/v.silk" } } },
      { type: 4, file_item: { media: { full_url: "https://cdn.example/f.pdf" }, file_name: "报价单.pdf" } },
    ],
  };
  const items = media.extractMediaItems(msg);
  assert.equal(items.length, 3, "TEXT 不计为媒体");
  assert.deepEqual(items.map((i) => i.type), [2, 3, 4]);
  assert.equal(items[0].item.image_item.media.full_url, "https://cdn.example/a.bin?enc=1");
  assert.equal(items[0].item.image_item.media.aes_key, "a2FiYw==");
  assert.equal(items[2].name, "报价单.pdf");
});

test("extractMediaItems 对无 item_list 或纯文本返回空", () => {
  assert.deepEqual(media.extractMediaItems({ content: "hi" }), []);
  assert.deepEqual(media.extractMediaItems({ item_list: [{ type: 1, text: "hi" }] }), []);
});

// ── saveInboundMedia ───────────────────────────────────────────────────────
test("saveInboundMedia 落盘并按类型命名； silk 标注", async () => {
  const dir = await mkdtemp(path.join(tmpdir(), "wx-media-"));
  try {
    const items = [
      { type: 2, msgId: "m1", idx: 0, download: { full_url: "https://cdn/a.bin" } },
      { type: 3, msgId: "m1", idx: 1, download: { full_url: "https://cdn/v.silk" } },
    ];
    const saved = await media.saveInboundMedia(items, {
      dir,
      downloadMedia: async () => ({ buffer: Buffer.from("PNGDATA") }),
    });
    assert.equal(saved.length, 2);
    assert.ok(saved.every((s) => s.ok));
    assert.match(saved[0].path, /-0\.png$/);
    assert.match(saved[1].path, /-1\.silk$/);
    assert.equal(media.mediaLabel(3).includes("silk"), true);
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
});

test("saveInboundMedia 单个失败不影响其余（失败隔离）", async () => {
  const dir = await mkdtemp(path.join(tmpdir(), "wx-media2-"));
  try {
    const items = [
      { type: 2, msgId: "m1", idx: 0, download: { full_url: "https://cdn/a.bin" } },
      { type: 2, msgId: "m1", idx: 1, download: { full_url: "https://cdn/b.bin" } },
    ];
    let n = 0;
    const saved = await media.saveInboundMedia(items, {
      dir,
      downloadMedia: async () => {
        n += 1;
        if (n === 1) throw new Error("CDN 超时");
        return { buffer: Buffer.from("OK") };
      },
    });
    assert.equal(saved[0].ok, false);
    assert.match(saved[0].error, /CDN 超时/);
    assert.equal(saved[1].ok, true);
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
});

// ── parseMediaDirectives ───────────────────────────────────────────────────
test("parseMediaDirectives：独占行才认；MEDIA 行剥离；路径保真", () => {
  const r = media.parseMediaDirectives(
    "这是海报\nMEDIA:/tmp/my poster.png\n请看\nMEDIA: https://cdn.example/x.jpg\n中间MEDIA:/nope.png",
  );
  assert.equal(r.media.length, 2);
  assert.equal(r.media[0], "/tmp/my poster.png", "路径含空格要保真");
  assert.equal(r.media[1], "https://cdn.example/x.jpg");
  const standalone = r.text.split("\n").filter((l) => /^\s*MEDIA:/.test(l));
  assert.equal(standalone.length, 0, "独占行 MEDIA 必须剥离");
  assert.ok(r.text.includes("这是海报") && r.text.includes("请看"));
  assert.ok(r.text.includes("中间MEDIA:/nope.png"), "行内形态不算指令");
});

test("parseMediaDirectives：file:// 前缀剥离；无指令时原文返回", () => {
  const r = media.parseMediaDirectives("MEDIA:file:///tmp/a.png");
  assert.equal(r.media[0], "/tmp/a.png");
  const r2 = media.parseMediaDirectives("普通文本");
  assert.deepEqual(r2.media, []);
  assert.equal(r2.text, "普通文本");
});

// ── dispatcher 双向接线 ────────────────────────────────────────────────────
test("dispatcher 入站图片：落盘 + agent 附注 + 用户确认", async () => {
  const dir = await mkdtemp(path.join(tmpdir(), "wx-md1-"));
  process.env.WECHAT_STATE_DIR = dir;
  try {
    const { Dispatcher } = await import("../src/dispatcher.js");
    const seen = [];
    const sent = [];
    const dispatcher = new Dispatcher({
      client: { chat: async (o) => { seen.push(o.message); return "收到"; } },
      transport: { typing: async () => ({}), send: async ({ body }) => { sent.push(body.content); } },
      mediaHooks: {
        saveInbound: async (items, opts) =>
          (await import("../src/media.js")).saveInboundMedia(items, {
            ...opts,
            downloadMedia: async () => ({ buffer: Buffer.from("PNG") }),
          }),
      },
    });
    await dispatcher.handle({
      from_user_id: "u1",
      content: "",
      item_list: [
        { type: 1, text: "" },
        { type: 2, image_item: { media: { full_url: "https://cdn/a.bin" } } },
      ],
    });
    assert.equal(seen.length, 1, "有媒体也应进入 agent");
    assert.match(seen[0], /用户发送了图片/);
    assert.match(seen[0], /media[\\\/]/);
    assert.ok(sent.some((s) => /已收到图片/.test(s)), "用户收到确认");
    const files = await readdir(path.join(dir, "media"), { recursive: true });
    assert.ok(files.some((f) => String(f).endsWith(".png")), "媒体落盘");
  } finally {
    delete process.env.WECHAT_STATE_DIR;
    await rm(dir, { recursive: true, force: true });
  }
});

test("dispatcher 出站 MEDIA：先文本后媒体，MEDIA 行不出现", async () => {
  const dir = await mkdtemp(path.join(tmpdir(), "wx-md2-"));
  process.env.WECHAT_STATE_DIR = dir;
  try {
    const { Dispatcher } = await import("../src/dispatcher.js");
    const sent = [];
    const mediaSent = [];
    const dispatcher = new Dispatcher({
      client: { chat: async () => "这是海报\nMEDIA:/tmp/poster.png" },
      transport: { typing: async () => ({}), send: async ({ body }) => { sent.push(body.content); } },
      mediaHooks: {
        sendMedia: async ({ filePath, to, text }) => { mediaSent.push({ filePath, to, text }); },
      },
    });
    await dispatcher.handle({ from_user_id: "u1", content: "做张海报" });
    assert.deepEqual(sent, ["这是海报"], "只发文本部分");
    assert.equal(mediaSent.length, 1);
    assert.equal(mediaSent[0].filePath, "/tmp/poster.png");
    assert.equal(mediaSent[0].to, "u1");
  } finally {
    delete process.env.WECHAT_STATE_DIR;
    await rm(dir, { recursive: true, force: true });
  }
});

test("dispatcher 媒体发送失败：文本照发，失败如实提示", async () => {
  const dir = await mkdtemp(path.join(tmpdir(), "wx-md3-"));
  process.env.WECHAT_STATE_DIR = dir;
  try {
    const { Dispatcher } = await import("../src/dispatcher.js");
    const sent = [];
    const dispatcher = new Dispatcher({
      client: { chat: async () => "文本\nMEDIA:/tmp/missing.png" },
      transport: { typing: async () => ({}), send: async ({ body }) => { sent.push(body.content); } },
      mediaHooks: {
        sendMedia: async () => { throw new Error("文件不存在"); },
      },
    });
    await dispatcher.handle({ from_user_id: "u1", content: "做张海报" });
    assert.deepEqual(sent[0], "文本");
    assert.ok(sent[1].includes("文件不存在"), "失败如实提示");
  } finally {
    delete process.env.WECHAT_STATE_DIR;
    await rm(dir, { recursive: true, force: true });
  }
});
