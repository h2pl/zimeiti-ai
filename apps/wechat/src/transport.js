/**
 * ilink 传输薄封装（可注入）。
 *
 * 直接调 vendor 的协议函数（零 openclaw 依赖）。默认实现走真实网络；
 * 测试注入 fake 驱动全流程。
 *
 * 联调修正：发送改用 vendor `sendMessageWeixin`（messaging/send.js）——它负责
 * buildTextMessageReq（contextToken/clientId/runId 的请求组装）。此前直接调
 * api.js sendMessage 传自造 body，协议形态不匹配（联调实测消息到不了微信）。
 */

import { getUpdates, sendTyping, getConfig, notifyStart } from "../vendor/openclaw-weixin/dist/src/api/api.js";
import { sendMessageWeixin } from "../vendor/openclaw-weixin/dist/src/messaging/send.js";
import { ILINK_BASE_URL } from "./config.js";

export class IlinkTransport {
  constructor({ baseUrl = ILINK_BASE_URL, token = "" } = {}) {
    this.baseUrl = baseUrl;
    this.token = token;
  }

  /** 激活推送（vendor channel 启动序列的一步；失败不致命）。 */
  async notifyStart() {
    return notifyStart({ baseUrl: this.baseUrl, token: this.token });
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

  /** 发文本。contextToken 来自入站消息（dispatcher 捕获）。 */
  async send({ to, body, contextToken, timeoutMs }) {
    return sendMessageWeixin({
      to,
      text: String(body?.content ?? ""),
      opts: { baseUrl: this.baseUrl, token: this.token, contextToken },
    });
  }

  async typing({ to, body }) {
    return sendTyping({ baseUrl: this.baseUrl, token: this.token, body: { ...body, to } });
  }

  async config({ ilinkUserId, contextToken }) {
    return getConfig({ baseUrl: this.baseUrl, token: this.token, ilinkUserId, contextToken });
  }
}

export default { IlinkTransport };
