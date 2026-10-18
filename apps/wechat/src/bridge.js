/**
 * 宿主骨架（wechat-bridge-scaffold）。
 *
 * 本期只到「能收能发」的骨架：长轮询循环 + 入站分发钩子 + 发送封装。
 * 真正把入站消息桥到 zimeiti agent 是变更 wechat-bridge-transport——
 * 届时只需实现 onMessage 钩子（POST zimeiti /api/chat/stream 拿回复），
 * 循环/游标/退避/优雅停机本期全部就位。
 */

import { IlinkTransport } from "./transport.js";

const BACKOFF_MS = [1000, 2000, 5000, 10000, 30000];

export class WechatBridge {
  /**
   * @param {object} opts
   * @param {string} opts.token       ilink bot token（登录态）
   * @param {string} opts.baseUrl     ilink 基础 URL
   * @param {(msg: object) => Promise<string|undefined>} [opts.onMessage]
   *        入站消息处理钩子，返回要回复的文本（undefined = 不回复）
   * @param {IlinkTransport} [opts.transport] 注入用（测试）
   */
  constructor(opts = {}) {
    this.token = opts.token || "";
    this.transport = opts.transport || new IlinkTransport({ baseUrl: opts.baseUrl, token: this.token });
    this.onMessage = opts.onMessage || (async () => undefined);
    this.cursor = "";
    this.running = false;
    this.stats = { received: 0, replied: 0, errors: 0 };
    this._abort = null;
  }

  async start() {
    this.running = true;
    this._abort = new AbortController();
    let failStreak = 0;
    while (this.running) {
      try {
        const resp = await this.transport.poll({
          cursor: this.cursor,
          timeoutMs: 30000,
          abortSignal: this._abort.signal,
        });
        failStreak = 0;
        if (resp?.get_updates_buf) this.cursor = resp.get_updates_buf;
        for (const msg of resp?.msgs || []) {
          this.stats.received += 1;
          await this._handle(msg);
        }
        // 让出事件循环：服务端立即返回（空批或带消息）时避免 microtask 自旋
        // 饿死定时器/其他 I/O（测试中以立即 resolve 的假 transport 复现过）。
        await new Promise((r) => setImmediate(r));
      } catch (err) {
        if (!this.running) break; // 停机中：正常退出
        this.stats.errors += 1;
        const wait = BACKOFF_MS[Math.min(failStreak, BACKOFF_MS.length - 1)];
        process.stderr.write(`[bridge] 轮询失败（第 ${failStreak + 1} 次）：${String(err)}\n`);
        await new Promise((r) => setTimeout(r, wait));
        failStreak += 1;
      }
    }
  }

  async stop() {
    this.running = false;
    this._abort?.abort();
  }

  async _handle(msg) {
    const text = String(msg?.content ?? msg?.text ?? "").trim();
    const to = msg?.from_user_id || msg?.ilink_user_id || msg?.user_id;
    let reply;
    try {
      reply = await this.onMessage(msg);
    } catch (err) {
      process.stderr.write(`[bridge] 消息处理失败：${String(err)}\n`);
      reply = undefined;
    }
    if (reply && to) {
      await this.transport.send({ to, body: { msg: text ? undefined : undefined, content: reply } });
      this.stats.replied += 1;
    }
  }
}
