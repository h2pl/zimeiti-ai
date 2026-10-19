/**
 * 入站分发（wechat-bridge-transport + media）：微信消息 → zimeiti → 微信。
 *
 * - 「新会话」指令：重置映射（不进 agent）
 * - 每用户 Promise 链串行（不同用户并行）
 * - 入站媒体：落盘 → agent 附注路径（不假装理解）→ 用户确认
 * - 出站媒体：agent 回复中独占一行 `MEDIA:<path|url>` → 先文本后媒体
 * - typing 先行；回复按协议上限 4000 字符分段
 * - 错误如实翻译成中文可行动提示，绝不静默丢弃
 */

import { sessionFor, resetSession } from "./sessions.js";
import { stateDir } from "./config.js";
import path from "node:path";
import { isGroupMessage, isBotMentioned, groupUserId, stripMention, requireMention } from "./group.js";
import { setContextToken, getContextToken } from "../vendor/openclaw-weixin/dist/src/messaging/inbound.js";
import {
  extractMediaItems,
  saveInboundMedia,
  buildInboundNote,
  buildInboundReceipt,
  parseMediaDirectives,
  defaultDownloadMedia,
  defaultSendMedia,
} from "./media.js";

const TEXT_CHUNK_LIMIT = 4000; // 协议码 outbound.textChunkLimit
const NEW_SESSION_CMDS = new Set(["新会话", "新建会话", "reset", "/reset"]);

// TEXT=1（vendor api/types.js MessageItemType）。真实 ilink 消息的文本在
// item_list[].text_item.text——联调实测 msg.content 形态不存在（曾静默丢消息）。
function extractInboundText(msg) {
  const list = Array.isArray(msg?.item_list) ? msg.item_list : [];
  for (const item of list) {
    if (Number(item?.type) === 1 && item?.text_item?.text != null) {
      return String(item.text_item.text);
    }
  }
  return String(msg?.content ?? msg?.text ?? "");
}

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
   * @param {object} [opts.mediaHooks]  媒体注入点（测试用）：
   *        { saveInbound, sendMedia }；另可用 ilinkOpts 传 baseUrl/token/cdnBaseUrl
   * @param {object} [opts.ilinkOpts]   { baseUrl, token, cdnBaseUrl }
   */
  constructor({ client, transport, mediaHooks, ilinkOpts, bot }) {
    this.client = client;
    this.transport = transport;
    this.ilinkOpts = ilinkOpts || {};
    this.bot = bot || { id: "", name: "" };
    this._saveInbound = mediaHooks?.saveInbound || saveInboundMedia;
    this._sendMedia = mediaHooks?.sendMedia || defaultSendMedia;
    this._downloadMedia = mediaHooks?.downloadMedia || defaultDownloadMedia;
    this._locks = new Map(); // wechatUserId -> Promise（链尾）
  }

  /** 处理一条入站消息。 */
  async handle(msg) {
    const userId = msg?.from_user_id || msg?.ilink_user_id || msg?.user_id || "unknown";
    const prev = this._locks.get(userId) ?? Promise.resolve();
    const run = prev.then(() => this._process(userId, msg), () => this._process(userId, msg));
    this._locks.set(userId, run.catch(() => {}));
    return run;
  }

  async _process(userId, msg) {
    // ── 群消息：默认仅在@bot 时响应（防骚扰）；非@静默跳过 ──────────────
    if (isGroupMessage(msg)) {
      if (requireMention() && !isBotMentioned(msg, this.bot)) return undefined;
      userId = groupUserId(msg);
    }
    let text = extractInboundText(msg).trim();
    if (isGroupMessage(msg)) text = stripMention(text, this.bot);

    // 捕获 context_token（vendor inbound.js 持久化存取）——回发时必需
    const accountId = this.ilinkOpts.accountId || "";
    if (accountId && msg?.context_token) {
      setContextToken(accountId, userId, String(msg.context_token));
    }
    const ctxToken = accountId ? getContextToken(accountId, userId) : undefined;

    if (text && NEW_SESSION_CMDS.has(text)) {
      await resetSession(userId);
      await this._send(userId, "已为你开启新会话——之前的上下文已清空，直接说新的话题吧。");
      return "已开新会话";
    }

    // ── 入站媒体：落盘 + 附注（失败隔离，不影响文本）────────────────────
    const mediaItems = extractMediaItems(msg);
    let note = "";
    let receipt = "";
    if (mediaItems.length) {
      const saved = await this._saveInbound(mediaItems, {
        downloadMedia: (it) => this._downloadMedia(it, { cdnBaseUrl: this.ilinkOpts.cdnBaseUrl }),
        dir: path.join(stateDir(), "media"),
      });
      note = buildInboundNote(saved);
      receipt = buildInboundReceipt(saved);
    }
    if (!text && !note) return undefined; // 空消息且无媒体

    const sessionId = await sessionFor(userId);
    try {
      await this.transport.typing({ to: userId, body: {} });
    } catch {
      /* typing 失败不影响主流程 */
    }

    const toAgent = [text, note].filter(Boolean).join("\n");
    let reply;
    try {
      reply = await this.client.chat({ sessionId, message: toAgent });
    } catch (err) {
      await this._send(userId, `⚠️ ${err?.message || "zimeiti 处理失败"}（会话保持，可直接重发）`, ctxToken);
      return undefined;
    }
    if (receipt) await this._send(userId, receipt, ctxToken);

    if (!reply || !reply.trim()) {
      await this._send(userId, "（agent 未产生文本回复）", ctxToken);
      return reply;
    }

    // ── 出站媒体：MEDIA: 指令（先文本后媒体；指令行剥离）────────────────
    const { text: bodyText, media: refs } = parseMediaDirectives(reply);
    for (const part of splitText(bodyText)) {
      await this._send(userId, part, ctxToken);
    }
    for (const ref of refs) {
      try {
        await this._sendMedia({
          filePath: ref,
          to: userId,
          text: "",
          contextToken: ctxToken,
          ...this.ilinkOpts,
        });
      } catch (err) {
        await this._send(userId, `⚠️ 媒体发送失败：${err?.message || err}（文本已送达）`, ctxToken);
      }
    }
    return reply;
  }

  async _send(userId, content, contextToken) {
    await this.transport.send({ to: userId, body: { content }, contextToken });
  }
}

export default { Dispatcher, splitText, extractInboundText };
export { extractInboundText };
