/**
 * wechat-bridge-ops 单测（node:test，零网络）：
 * 群判定（字段名可配）/@检测/群会话前缀/非@静默/多账号遍历 + 服务单元内容校验。
 */

import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";

const group = await import("../src/group.js");

// ── 群判定 ────────────────────────────────────────────────────────────────
test("isGroupMessage：room_id/group_id/chat_type 任一命中", () => {
  assert.equal(group.isGroupMessage({ room_id: "r1" }), true);
  assert.equal(group.isGroupMessage({ group_id: "g1" }), true);
  assert.equal(group.isGroupMessage({ chat_type: "group" }), true);
  assert.equal(group.isGroupMessage({ from_user_id: "u1" }), false);
  assert.equal(group.isGroupMessage({}), false);
});

test("isGroupMessage：字段名可配（联调校准用）", () => {
  const msg = { conversation_id: "c1" };
  assert.equal(group.isGroupMessage(msg), false, "默认字段名不认");
  assert.equal(
    group.isGroupMessage(msg, { groupFields: ["conversation_id"] }),
    true,
    "配置后认",
  );
});

// ── @检测 ────────────────────────────────────────────────────────────────
test("isBotMentioned：文本含 bot id/名称，或服务端 at 标记", () => {
  const bot = { id: "hex@im.bot", name: "小贝" };
  assert.equal(group.isBotMentioned({ content: "@小贝 今天的选题" }, bot), true);
  assert.equal(group.isBotMentioned({ content: "hex@im.bot 在吗" }, bot), true);
  assert.equal(group.isBotMentioned({ content: "今天天气不错" }, bot), false);
  assert.equal(group.isBotMentioned({ content: "在吗", is_at_me: true }, bot), true);
  assert.equal(group.isBotMentioned({ content: "在吗", at_users: ["hex@im.bot"] }, bot), true);
});

test("isBotMentioned：at 字段名可配", () => {
  const bot = { id: "b1", name: "" };
  assert.equal(group.isBotMentioned({ content: "x", mentioned: ["b1"] }, bot), false);
  assert.equal(
    group.isBotMentioned({ content: "x", mentioned: ["b1"] }, bot, { atFields: ["mentioned"] }),
    true,
  );
});

// ── 群会话前缀与清洗 ──────────────────────────────────────────────────────
test("groupKey/groupUserId：wxg- 前缀防与私聊混", () => {
  assert.equal(group.groupUserId({ room_id: "r1" }), "wxg-r1");
  assert.equal(group.groupUserId({ group_id: "g1@room" }), "wxg-g1@room");
});

test("stripMention 去掉@前缀给 agent 干净文本", () => {
  const bot = { id: "hex@im.bot", name: "小贝" };
  assert.equal(group.stripMention("@小贝 帮我找选题", bot), "帮我找选题");
  assert.equal(group.stripMention("hex@im.bot 在吗", bot), "在吗");
  assert.equal(group.stripMention("没有@的普通消息", bot), "没有@的普通消息");
});

// ── dispatcher：非@群消息静默 ─────────────────────────────────────────────
test("dispatcher 群内未@：静默跳过（不回复、不进 agent、不计错）", async () => {
  const dir = await mkdtemp(path.join(tmpdir(), "wx-grp-"));
  process.env.WECHAT_STATE_DIR = dir;
  try {
    const { Dispatcher } = await import("../src/dispatcher.js");
    const seen = [];
    const sent = [];
    const dispatcher = new Dispatcher({
      client: { chat: async (o) => { seen.push(o.message); return "回复"; } },
      transport: { typing: async () => ({}), send: async ({ body }) => { sent.push(body.content); } },
      bot: { id: "hex@im.bot", name: "小贝" },
    });
    await dispatcher.handle({
      from_user_id: "ignored-in-groups",
      room_id: "room-1",
      content: "群里闲聊，没@机器人",
    });
    assert.equal(seen.length, 0, "不进 agent");
    assert.equal(sent.length, 0, "不回复");
  } finally {
    delete process.env.WECHAT_STATE_DIR;
    await rm(dir, { recursive: true, force: true });
  }
});

test("dispatcher 群内@bot：进 agent 且会话带 wxg- 前缀", async () => {
  const dir = await mkdtemp(path.join(tmpdir(), "wx-grp2-"));
  process.env.WECHAT_STATE_DIR = dir;
  try {
    const { Dispatcher } = await import("../src/dispatcher.js");
    const seen = [];
    const sent = [];
    const dispatcher = new Dispatcher({
      client: { chat: async (o) => { seen.push(o); return "回复"; } },
      transport: { typing: async () => ({}), send: async ({ body }) => { sent.push(body.content); } },
      bot: { id: "hex@im.bot", name: "小贝" },
    });
    await dispatcher.handle({
      from_user_id: "u-in-room",
      room_id: "room-1",
      content: "@小贝 帮我找今天的选题",
    });
    assert.equal(seen.length, 1);
    assert.match(seen[0].sessionId, /^wxg-room-1$/, "群会话前缀");
    assert.equal(seen[0].message, "帮我找今天的选题", "@前缀被清洗");
    assert.equal(sent.length, 1);
  } finally {
    delete process.env.WECHAT_STATE_DIR;
    await rm(dir, { recursive: true, force: true });
  }
});

test("dispatcher 私聊仍无需@（行为不回退）", async () => {
  const dir = await mkdtemp(path.join(tmpdir(), "wx-grp3-"));
  process.env.WECHAT_STATE_DIR = dir;
  try {
    const { Dispatcher } = await import("../src/dispatcher.js");
    const seen = [];
    const dispatcher = new Dispatcher({
      client: { chat: async (o) => { seen.push(o); return "回复"; } },
      transport: { typing: async () => ({}), send: async () => ({}) },
      bot: { id: "hex@im.bot", name: "小贝" },
    });
    await dispatcher.handle({ from_user_id: "u1", content: "你好" });
    assert.equal(seen.length, 1);
    assert.match(seen[0].sessionId, /^wx-/);
  } finally {
    delete process.env.WECHAT_STATE_DIR;
    await rm(dir, { recursive: true, force: true });
  }
});

test("dispatcher 群@检测可关闭（WECHAT_GROUP_REQUIRE_MENTION=false）", async () => {
  const dir = await mkdtemp(path.join(tmpdir(), "wx-grp4-"));
  process.env.WECHAT_STATE_DIR = dir;
  process.env.WECHAT_GROUP_REQUIRE_MENTION = "false";
  try {
    const { Dispatcher } = await import("../src/dispatcher.js");
    const seen = [];
    const dispatcher = new Dispatcher({
      client: { chat: async (o) => { seen.push(o); return "回复"; } },
      transport: { typing: async () => ({}), send: async () => ({}) },
      bot: { id: "hex@im.bot", name: "小贝" },
    });
    await dispatcher.handle({ from_user_id: "u", room_id: "r", content: "没@也回" });
    assert.equal(seen.length, 1, "关闭后群内无需@");
  } finally {
    delete process.env.WECHAT_STATE_DIR;
    delete process.env.WECHAT_GROUP_REQUIRE_MENTION;
    await rm(dir, { recursive: true, force: true });
  }
});

// ── 服务单元内容校验 ──────────────────────────────────────────────────────
test("systemd 单元含自恢复与启动前等待", async () => {
  const { readFile } = await import("node:fs/promises");
  const { APP_DIR } = await import("../src/config.js");
  const unit = await readFile(path.join(APP_DIR, "services/zimeiti-wechat.service"), "utf8");
  assert.match(unit, /Restart=always/);
  assert.match(unit, /ExecStart=.*index\.js start/);
  assert.match(unit, /api\/status/, "启动前应等待 zimeiti 就绪");
});

test("launchd plist 含 KeepAlive 与启动参数", async () => {
  const { readFile } = await import("node:fs/promises");
  const { APP_DIR } = await import("../src/config.js");
  const plist = await readFile(path.join(APP_DIR, "services/com.zimeiti.wechat.plist"), "utf8");
  assert.match(plist, /<key>KeepAlive<\/key>\s*<true\/>/);
  assert.match(plist, /index\.js/);
  assert.match(plist, /start/);
});


// ── 联调修复回归：登录态落盘字段契约 ───────────────────────────────────────
test("login 落盘用 vendor 契约字段 token（联调首扫 bug 回归，源码契约）", async () => {
  const { readFile } = await import("node:fs/promises");
  const { APP_DIR } = await import("../src/config.js");
  const src = await readFile(`${APP_DIR}/src/login.js`, "utf8");
  // save 调用必须是 token（vendor accounts.js 读 update.token）；不得出现 botToken 传入
  assert.match(src, /token: result\.botToken/, "落盘必须用 vendor 契约字段 token");
  const saveCall = src.slice(src.indexOf("const save = opts.saveAccount"));
  assert.ok(!/botToken:/.test(saveCall.split("});")[0]), "save 入参不得再用 botToken");
});

test("账号读取侧读 token 而非 botToken（vendor 契约 roundtrip）", async () => {
  const { loadWeixinAccount, saveWeixinAccount } = await import(
    "../vendor/openclaw-weixin/dist/src/auth/accounts.js"
  );
  const { mkdtemp } = await import("node:fs/promises");
  const { join } = await import("node:path");
  const { tmpdir } = await import("node:os");
  const dir = await mkdtemp(join(tmpdir(), "wx-acct-"));
  process.env.OPENCLAW_STATE_DIR = dir;
  try {
    saveWeixinAccount("acct-1", { token: "tk", baseUrl: "https://x", userId: "u1" });
    const acc = await loadWeixinAccount("acct-1");
    assert.equal(acc.token, "tk", "读取字段名是 token");
    assert.equal(acc.baseUrl, "https://x");
  } finally {
    delete process.env.OPENCLAW_STATE_DIR;
  }
});

test("index.js 读取侧用 acc.token（不是 botToken）", async () => {
  const { readFile } = await import("node:fs/promises");
  const { APP_DIR } = await import("../src/config.js");
  const src = await readFile(`${APP_DIR}/src/index.js`, "utf8");
  assert.ok(!/botToken/.test(src), "index.js 不应再出现 botToken");
});
