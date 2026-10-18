/**
 * ilink 传输薄封装（可注入）。
 *
 * 直接调 vendor 的 api.js（getUpdates 长轮询 / sendMessage / sendTyping）——
 * 这些函数零 openclaw 依赖。默认实现走真实网络；测试注入 fake 驱动全流程。
 */

import { getUpdates, sendMessage, sendTyping, getConfig } from "../vendor/openclaw-weixin/dist/src/api/api.js";
import { ILINK_BASE_URL } from "./config.js";

export class IlinkTransport {
  constructor({ baseUrl = ILINK_BASE_URL, token = "" } = {}) {
    this.baseUrl = baseUrl;
    this.token = token;
  }

  /** 长轮询一批消息。cursor 为服务端游标（get_updates_buf）。 */
  async poll({ cursor = "", timeoutMs = 30000, abortSignal } = {}) {
    return getUpdates({
      baseUrl: this.baseUrl,
      token: this.token,
      get_updates_buf: cursor,
      timeoutMs,
      abortSignal,
    });
  }

  /** 发文本。to 为 ilink user id；body 由调用方按协议组装。 */
  async send({ to, body, timeoutMs }) {
    return sendMessage({
      baseUrl: this.baseUrl,
      token: this.token,
      body: { ...body, to },
      timeoutMs,
    });
  }

  async typing({ to, body }) {
    return sendTyping({ baseUrl: this.baseUrl, token: this.token, body: { ...body, to } });
  }

  async config({ ilinkUserId, contextToken }) {
    return getConfig({ baseUrl: this.baseUrl, token: this.token, ilinkUserId, contextToken });
  }
}
