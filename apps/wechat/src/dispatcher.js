/**
 * 入站分发（wechat-bridge-transport）：微信消息 → zimeiti → 微信。
 *
 * - 「新会话」指令：重置映射（不进 agent）
 * - 每用户 Promise 链串行（不同用户并行）
 * - typing 先行（长耗时有反馈）
 * - 回复按协议上限 4000 字符分段
 * - 错误如实翻译成中文可行动提示，绝不静默丢弃
 */

import { sessionFor, resetSession } from "./sessions.js";

const TEXT_CHUNK_LIMIT = 4000; // 协议码 outbound.textChunkLimit
const NEW_SESSION_CMDS = new Set(["新会话", "新建会话", "reset", "/reset"]);

function splitText(text, limit = TEXT_CHUNK_LIMIT) {
  const out = [];
  let rest = String(text ?? "");
  while (rest.length > limit) {
    let cut = rest.lastIndexOf("\n", limit);
    if (cut < limit / 2) cut = rest.lastIndexOf("。", limit);
    if (cut < limit / 2) cut = limit;
    out.push(rest.slice(0, cut));
    rest = rest.slice(cut);
  }
  if (rest) out.push(rest);
  return out.length ? out : [""];
}

export class Dispatcher {
  /**
   * @param {object} opts
   * @param {{chat: Function, ping?: Function}} opts.client     zimeiti 客户端
   * @param {{typing: Function, send: Function}} opts.transport ilink transport
   */
  constructor({ client, transport }) {
    this.client = client;
    this.transport = transport;
    this._locks = new Map(); // wechatUserId -> Promise（链尾）
  }

  /** 处理一条入站消息（返回给桥的回复文本，桥不再重复发送）。 */
  async handle(msg) {
    const userId = msg?.from_user_id || msg?.ilink_user_id || msg?.user_id || "unknown";
    const text = String(msg?.content ?? msg?.text ?? "").trim();
    if (!text) return undefined;

    // 每用户串行：把本轮挂到该用户链尾
    const prev = this._locks.get(userId) ?? Promise.resolve();
    const run = prev.then(() => this._process(userId, text), () => this._process(userId, text));
    this._locks.set(userId, run.catch(() => {}));
    return run;
  }

  async _process(userId, text) {
    if (NEW_SESSION_CMDS.has(text)) {
      await resetSession(userId);
      await this._send(userId, "已为你开启新会话——之前的上下文已清空，直接说新的话题吧。");
      return "已开新会话";
    }

    const sessionId = await sessionFor(userId);
    try {
      await this.transport.typing({ to: userId, body: {} });
    } catch {
      /* typing 失败不影响主流程 */
    }

    let reply;
    try {
      reply = await this.client.chat({ sessionId, message: text });
    } catch (err) {
      await this._send(userId, `⚠️ ${err?.message || "zimeiti 处理失败"}（会话保持，可直接重发）`);
      return undefined;
    }
    if (!reply || !reply.trim()) {
      await this._send(userId, "（agent 未产生文本回复）");
      return reply;
    }
    for (const part of splitText(reply)) {
      await this._send(userId, part);
    }
    return reply;
  }

  async _send(userId, content) {
    await this.transport.send({ to: userId, body: { content } });
  }
}

export default { Dispatcher, splitText };
