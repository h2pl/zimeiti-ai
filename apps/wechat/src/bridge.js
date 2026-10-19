/**
 * 宿主骨架（wechat-bridge-scaffold）：长轮询循环 + 入站分发钩子 + 发送封装。
 *
 * 联调修正：
 * - start 时调 notifyStart（vendor channel 启动序列的一步；失败不致命）
 * - 每次轮询结果落一行日志（此前完全静默，消息被吞无从排查）
 * - onMessage 钩子默认**自行负责回发**（dispatcher 内部发送）；仅当
 *   opts.sendReplies=true 时桥再代发（避免双重发送——联调实测会重复回复）
 */

import { IlinkTransport } from "./transport.js";

const BACKOFF_MS = [1000, 2000, 5000, 10000, 30000];

export class WechatBridge {
  /**
   * @param {object} opts
   * @param {string} opts.token       ilink bot token（登录态）
   * @param {string} opts.baseUrl     ilink 基础 URL
   * @param {(msg: object) => Promise<string|undefined>} [opts.onMessage]
   *        入站消息处理钩子（默认自行回发；返回文本仅作记录/桥代发用）
   * @param {boolean} [opts.sendReplies] 桥代发回复（默认 false，dispatcher 已发）
   * @param {IlinkTransport} [opts.transport] 注入用（测试）
   */
  constructor(opts = {}) {
    this.token = opts.token || "";
    this.transport = opts.transport || new IlinkTransport({ baseUrl: opts.baseUrl, token: this.token });
    this.onMessage = opts.onMessage || (async () => undefined);
    this.sendReplies = Boolean(opts.sendReplies);
    this.cursor = "";
    this.running = false;
    this.stats = { received: 0, replied: 0, errors: 0 };
    this._abort = null;
  }

  async start() {
    this.running = true;
    this._abort = new AbortController();
    try {
      const ns = await this.transport.notifyStart?.();
      if (ns && ns.ret !== undefined && ns.ret !== 0) {
        process.stderr.write(`[bridge] notifyStart ret=${ns.ret}（不致命，继续）\n`);
      }
    } catch (err) {
      process.stderr.write(`[bridge] notifyStart 失败（不致命）：${String(err).slice(0, 120)}\n`);
    }
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
        const msgs = resp?.msgs || [];
        if (msgs.length) {
          process.stderr.write(`[bridge] 收到 ${msgs.length} 条消息\n`);
        }
        for (const msg of msgs) {
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
    const to = msg?.from_user_id || msg?.ilink_user_id || msg?.user_id;
    let reply;
    try {
      reply = await this.onMessage(msg);
    } catch (err) {
      process.stderr.write(`[bridge] 消息处理失败：${String(err)}\n`);
      reply = undefined;
    }
    if (this.sendReplies && reply && to) {
      await this.transport.send({ to, body: { content: reply } });
      this.stats.replied += 1;
    }
  }
}
