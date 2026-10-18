/**
 * 微信用户 ↔ zimeiti 会话映射（wechat-bridge-scaffold：落盘骨架）。
 *
 * 策略（用户确认「同上」= 按推荐：私聊优先、一个微信 = 一个 zimeiti 会话）：
 * 每个 ilink user id 绑定一个 zimeiti session id，跨天连续；支持「新会话」指令
 * 解绑重建（指令解析在 transport 变更实现，此处先落数据结构与存取）。
 */

import { readFile, writeFile, mkdir } from "node:fs/promises";
import path from "node:path";
import { sessionsFile } from "./config.js";

async function _load() {
  try {
    return JSON.parse(await readFile(sessionsFile(), "utf8"));
  } catch {
    return { version: 1, bindings: {} };
  }
}

async function _save(data) {
  const file = sessionsFile();
  await mkdir(path.dirname(file), { recursive: true });
  await writeFile(file, `${JSON.stringify(data, null, 2)}\n`, "utf8");
}

/** 取（必要时创建）某微信用户的 zimeiti session id。 */
export async function sessionFor(wechatUserId) {
  const data = await _load();
  const existing = data.bindings[wechatUserId];
  if (existing?.sessionId) return existing.sessionId;
  const sessionId = `wx-${wechatUserId.slice(0, 24)}`;
  data.bindings[wechatUserId] = { sessionId, createdAt: Date.now() };
  await _save(data);
  return sessionId;
}

/** 「新会话」：解绑，下次说话时重建。 */
export async function resetSession(wechatUserId) {
  const data = await _load();
  delete data.bindings[wechatUserId];
  await _save(data);
}

/** 映射全貌（status 用）。 */
export async function listBindings() {
  const data = await _load();
  return data.bindings;
}
