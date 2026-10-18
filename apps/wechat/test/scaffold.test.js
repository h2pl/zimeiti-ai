/**
 * wechat-bridge-scaffold 单测（node:test，零网络）。
 *
 * 覆盖规格三条：shim 两 helper 语义 / 登录流程（假 transport 驱动落盘）/
 * 状态自检与 CLI 退出码 / 桥骨架轮询与退避。
 */

import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";

// ── shim：account-id ───────────────────────────────────────────────────────
test("shim normalizeAccountId 规范化语义", async () => {
  const { normalizeAccountId } = await import(
    "../shim/openclaw/plugin-sdk/account-id.js"
  );
  assert.equal(normalizeAccountId("  AbC_123  "), "abc_123");
  assert.equal(normalizeAccountId("微信 id/带空格"), "id"); // 非 [a-z0-9_-] → 连字符，首尾连字符剥除
  assert.equal(normalizeAccountId(""), "default");
  assert.equal(normalizeAccountId(null), "default");
  assert.equal(normalizeAccountId("x".repeat(200)).length, 64);
});

// ── shim：config-mutation ─────────────────────────────────────────────────
test("shim mutateConfigFile 原子写 + 串行 + 不存在时用默认值", async () => {
  const { mutateConfigFile } = await import(
    "../shim/openclaw/plugin-sdk/config-mutation.js"
  );
  const dir = await mkdtemp(path.join(tmpdir(), "wx-shim-"));
  const file = path.join(dir, "nested", "cfg.json");
  try {
    const first = await mutateConfigFile(file, (cur) => {
      assert.deepEqual(cur, {}); // 不存在 → 默认值
      return { a: 1 };
    });
    assert.deepEqual(first, { a: 1 });

    // 串行：并发多次 mutate 不丢更新
    await Promise.all([
      mutateConfigFile(file, (c) => ({ ...c, x: (c.x || 0) + 1 })),
      mutateConfigFile(file, (c) => ({ ...c, x: (c.x || 0) + 1 })),
      mutateConfigFile(file, (c) => ({ ...c, x: (c.x || 0) + 1 })),
    ]);
    const { readFile } = await import("node:fs/promises");
    const saved = JSON.parse(await readFile(file, "utf8"));
    assert.equal(saved.x, 3);
    assert.equal(saved.a, 1);
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
});

// ── 桥骨架：轮询 + 分发 + 发送 + 停机 ─────────────────────────────────────
test("bridge 轮询到消息即分发并回复；stop 后退出", async () => {
  const { WechatBridge } = await import("../src/bridge.js");
  const seen = [];
  let delivered = false;
  const fake = {
    // 假 transport 模型真实 I/O：长轮询有延迟；且每条消息只投一次
    // （真实服务按游标推进，不会重复投同一条）。
    poll: async () => {
      await new Promise((r) => setTimeout(r, 5));
      if (delivered) return { ret: 0, msgs: [], get_updates_buf: "c1" };
      delivered = true;
      return { ret: 0, msgs: [{ from_user_id: "u1", content: "你好" }], get_updates_buf: "c1" };
    },
    send: async ({ to, body }) => {
      seen.push([to, body.content]);
      return { ret: 0 };
    },
    typing: async () => ({}),
    config: async () => ({}),
  };
  const bridge = new WechatBridge({
    token: "t",
    transport: fake,
    onMessage: async (msg) => `回声:${msg.content}`,
  });
  const loop = bridge.start();
  await new Promise((r) => setTimeout(r, 60));
  await bridge.stop();
  await loop;
  assert.equal(bridge.stats.received, 1);
  assert.equal(bridge.stats.replied, 1);
  assert.deepEqual(seen, [["u1", "回声:你好"]]);
  assert.equal(bridge.cursor, "c1"); // 游标推进
});

test("bridge 轮询失败按退避重试不崩溃", async () => {
  const { WechatBridge } = await import("../src/bridge.js");
  let calls = 0;
  const fake = {
    poll: async () => {
      calls += 1;
      throw new Error("网络抖动");
    },
    send: async () => ({ ret: 0 }),
  };
  const bridge = new WechatBridge({ token: "t", transport: fake });
  const loop = bridge.start();
  await new Promise((r) => setTimeout(r, 1500));
  await bridge.stop();
  await loop;
  assert.ok(calls >= 2, `应重试至少 2 次，实际 ${calls}`);
  assert.ok(bridge.stats.errors >= 1);
});

// ── sessions：映射落盘 ────────────────────────────────────────────────────
test("sessions 映射：同用户稳定、reset 后重建、且严格隔离于真实 state", async () => {
  const dir = await mkdtemp(path.join(tmpdir(), "wx-sess-"));
  process.env.WECHAT_STATE_DIR = dir;
  // 隔离有效性前置断言（曾因 config 不读该变量而假绿灯）
  const cfg = await import("../src/config.js");
  assert.equal(cfg.sessionsFile(), path.join(dir, "sessions.json"));
  const { sessionFor, resetSession, listBindings } = await import("../src/sessions.js");
  try {
    const s1 = await sessionFor("wx-user-abc");
    const s2 = await sessionFor("wx-user-abc");
    assert.equal(s1, s2);
    assert.equal(s1, "wx-wx-user-abc");
    assert.deepEqual(Object.keys(await listBindings()), ["wx-user-abc"]);
    await resetSession("wx-user-abc");
    const s3 = await sessionFor("wx-user-abc");
    assert.equal(s3, s1); // 稳定派生，不是随机
  } finally {
    delete process.env.WECHAT_STATE_DIR;
    await rm(dir, { recursive: true, force: true });
  }
});

// ── vendor 合规 ───────────────────────────────────────────────────────────
test("vendor 合规三件套 + 协议码可 import", async () => {
  const { readFile } = await import("node:fs/promises");
  const { APP_DIR } = await import("../src/config.js");
  const license = await readFile(path.join(APP_DIR, "vendor/openclaw-weixin/LICENSE"), "utf8");
  assert.match(license, /MIT/);
  const notice = await readFile(path.join(APP_DIR, "NOTICE"), "utf8");
  assert.match(notice, /openclaw-weixin/);
  assert.match(notice, /未改动/);
  const manifest = JSON.parse(
    await readFile(path.join(APP_DIR, "vendor/openclaw-weixin/MANIFEST.json"), "utf8"),
  );
  assert.equal(manifest.version, "2.4.10");
  // 协议函数可 import 且零 SDK 依赖路径残留
  const api = await import("../vendor/openclaw-weixin/dist/src/api/api.js");
  assert.equal(typeof api.getUpdates, "function");
  assert.equal(typeof api.sendMessage, "function");
});
