/**
 * wechat-bridge-transport 单测（node:test，零外部网络）。
 *
 * 客户端测试用 node:http 起本地 SSE 服务器（真实 HTTP，仅环回）；
 * 分发测试用假 transport + 假客户端（零网络）。
 */

import test from "node:test";
import assert from "node:assert/strict";
import http from "node:http";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";

// ── 本地 SSE 服务器（客户端测试用）──────────────────────────────────────────
async function withSseServer(handler, fn) {
  const server = http.createServer(handler);
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  const port = server.address().port;
  try {
    await fn(`http://127.0.0.1:${port}`);
  } finally {
    await new Promise((r) => server.close(r));
  }
}

function sseRes(res) {
  res.writeHead(200, { "Content-Type": "text/event-stream" });
}

test("zimeiti-client chat 累积 token 全文", async () => {
  await withSseServer((req, res) => {
    sseRes(res);
    res.write('event: token\ndata: "你好"\n\n');
    res.write('event: token\ndata: "，世界"\n\n');
    res.write('event: activity\ndata: "思考中"\n\n');
    res.write("data: [DONE]\n\n");
    res.end();
  }, async (base) => {
    const { ZimeitiClient } = await import("../src/zimeiti-client.js");
    const client = new ZimeitiClient({ baseUrl: base, timeoutMs: 5000 });
    const progresses = [];
    const text = await client.chat({
      sessionId: "s1",
      message: "hi",
      onProgress: (p) => progresses.push(p),
    });
    assert.equal(text, "你好，世界");
    assert.deepEqual(progresses, ["思考中"]);
  });
});

test("zimeiti-client chat 遇 error 帧抛出带摘要的异常", async () => {
  await withSseServer((req, res) => {
    sseRes(res);
    res.write('event: error\ndata: "后端代码已变更——请重启后端"\n\n');
    res.write("data: [DONE]\n\n");
    res.end();
  }, async (base) => {
    const { ZimeitiClient } = await import("../src/zimeiti-client.js");
    const client = new ZimeitiClient({ baseUrl: base, timeoutMs: 5000 });
    await assert.rejects(
      () => client.chat({ sessionId: "s1", message: "hi" }),
      /请重启后端/,
    );
  });
});

test("zimeiti-client chat 连接失败抛可行动错误", async () => {
  const { ZimeitiClient } = await import("../src/zimeiti-client.js");
  const client = new ZimeitiClient({ baseUrl: "http://127.0.0.1:1", timeoutMs: 2000 });
  await assert.rejects(
    () => client.chat({ sessionId: "s1", message: "hi" }),
    /不可达|无法连接/,
  );
});

test("zimeiti-client ping 布尔化", async () => {
  await withSseServer((req, res) => {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ ok: true }));
  }, async (base) => {
    const { ZimeitiClient } = await import("../src/zimeiti-client.js");
    const client = new ZimeitiClient({ baseUrl: base, timeoutMs: 5000 });
    assert.equal(await client.ping(), true);
  });
});

// ── 分发：指令 / 锁 / 分段 / 错误翻译 ───────────────────────────────────────
test("dispatcher「新会话」指令重置映射且不进 agent", async () => {
  const dir = await mkdtemp(path.join(tmpdir(), "wx-disp-"));
  process.env.WECHAT_STATE_DIR = dir;
  try {
    const { Dispatcher } = await import("../src/dispatcher.js");
    const calls = [];
    const dispatcher = new Dispatcher({
      client: { chat: async (o) => { calls.push(o); return "回复"; } },
      transport: { typing: async () => ({}), send: async () => ({ ret: 0 }) },
    });
    const out = await dispatcher.handle({ from_user_id: "u1", content: "新会话" });
    assert.match(out, /新会话/);
    assert.equal(calls.length, 0, "指令不得进入 agent");
    const { listBindings } = await import("../src/sessions.js");
    assert.equal(Object.keys(await listBindings()).length, 0);
  } finally {
    delete process.env.WECHAT_STATE_DIR;
    await rm(dir, { recursive: true, force: true });
  }
});

test("dispatcher 正常消息带稳定 sessionId 进 agent 并回发", async () => {
  const dir = await mkdtemp(path.join(tmpdir(), "wx-disp2-"));
  process.env.WECHAT_STATE_DIR = dir;
  try {
    const { Dispatcher } = await import("../src/dispatcher.js");
    const sent = [];
    const seen = [];
    const dispatcher = new Dispatcher({
      client: { chat: async (o) => { seen.push(o); return " agent 回复 "; } },
      transport: { typing: async () => ({}), send: async ({ to, body }) => { sent.push([to, body.content]); } },
    });
    await dispatcher.handle({ from_user_id: "u1", content: "你好" });
    await dispatcher.handle({ from_user_id: "u1", content: "在吗" });
    assert.equal(seen.length, 2);
    assert.equal(seen[0].sessionId, seen[1].sessionId, "同用户会话稳定");
    assert.match(seen[0].sessionId, /^wx-/);
    assert.deepEqual(sent, [["u1", " agent 回复 "], ["u1", " agent 回复 "]]);
  } finally {
    delete process.env.WECHAT_STATE_DIR;
    await rm(dir, { recursive: true, force: true });
  }
});

test("dispatcher 同用户串行、不同用户并行", async () => {
  const dir = await mkdtemp(path.join(tmpdir(), "wx-disp3-"));
  process.env.WECHAT_STATE_DIR = dir;
  try {
    const { Dispatcher } = await import("../src/dispatcher.js");
    const order = [];
    let release;
    const gate = new Promise((r) => { release = r; });
    const dispatcher = new Dispatcher({
      client: {
        chat: async (o) => {
          order.push(`start:${o.message}`);
          await gate;
          order.push(`end:${o.message}`);
          return "ok";
        },
      },
      transport: { typing: async () => ({}), send: async () => ({ ret: 0 }) },
    });
    const p1 = dispatcher.handle({ from_user_id: "u1", content: "A" });
    const p2 = dispatcher.handle({ from_user_id: "u1", content: "B" });
    const p3 = dispatcher.handle({ from_user_id: "u2", content: "C" });
    await new Promise((r) => setTimeout(r, 30));
    release();
    await Promise.all([p1, p2, p3]);
    // u1 的 B 必须等 A 结束才开始；u2 的 C 与 u1 并行
    assert.ok(order.indexOf("start:B") > order.indexOf("end:A"), "同用户串行");
    assert.ok(order.indexOf("start:C") < order.indexOf("end:A"), "不同用户并行");
  } finally {
    delete process.env.WECHAT_STATE_DIR;
    await rm(dir, { recursive: true, force: true });
  }
});

test("dispatcher 后端不可达 → 用户收到可行动提示（不静默）", async () => {
  const dir = await mkdtemp(path.join(tmpdir(), "wx-disp4-"));
  process.env.WECHAT_STATE_DIR = dir;
  try {
    const { Dispatcher } = await import("../src/dispatcher.js");
    const sent = [];
    const dispatcher = new Dispatcher({
      client: { chat: async () => { throw new Error("zimeiti 后端暂时不可达，请检查服务（make api）后重试"); } },
      transport: { typing: async () => ({}), send: async ({ body }) => { sent.push(body.content); } },
    });
    await dispatcher.handle({ from_user_id: "u1", content: "你好" });
    assert.equal(sent.length, 1);
    assert.match(sent[0], /不可达|稍后/);
  } finally {
    delete process.env.WECHAT_STATE_DIR;
    await rm(dir, { recursive: true, force: true });
  }
});

test("dispatcher 长回复按 4000 分段不丢内容", async () => {
  const dir = await mkdtemp(path.join(tmpdir(), "wx-disp5-"));
  process.env.WECHAT_STATE_DIR = dir;
  try {
    const { Dispatcher } = await import("../src/dispatcher.js");
    const sent = [];
    const long = "x".repeat(9500);
    const dispatcher = new Dispatcher({
      client: { chat: async () => long },
      transport: { typing: async () => ({}), send: async ({ body }) => { sent.push(body.content); } },
    });
    await dispatcher.handle({ from_user_id: "u1", content: "写长的" });
    assert.ok(sent.length >= 3, `应分多段，实际 ${sent.length}`);
    assert.equal(sent.join(""), long, "分段拼接后内容不丢");
    assert.ok(sent.every((s) => s.length <= 4000), "每段不超协议上限");
  } finally {
    delete process.env.WECHAT_STATE_DIR;
    await rm(dir, { recursive: true, force: true });
  }
});
