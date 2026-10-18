/**
 * zimeiti HTTP 客户端（零三方依赖，Node ≥18 fetch）。
 *
 * 只消费既有端点：POST /api/chat/stream（SSE）与 GET /api/status。
 * **不持有任何模型凭据**——key 轮换/fallback/门禁全在服务端。
 */

import { zimeitiBase } from "./config.js";

const DEFAULT_TIMEOUT_MS = Number(process.env.WECHAT_ZIMEITI_TIMEOUT_MS || 180_000);

export class ZimeitiClient {
  constructor({ baseUrl = zimeitiBase(), timeoutMs = DEFAULT_TIMEOUT_MS } = {}) {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
    this.timeoutMs = timeoutMs;
  }

  /**
   * 跑一轮对话，读 SSE 累积全文。
   * @returns {Promise<string>} 完整回复
   * @throws Error 带中文可行动摘要（error 帧 / 连接失败 / 超时）
   */
  async chat({ sessionId, message, onProgress }) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);
    try {
      const res = await fetch(`${this.baseUrl}/api/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, sessionId }),
        signal: controller.signal,
      });
      if (!res.ok || !res.body) {
        throw new Error(`zimeiti 后端不可达（HTTP ${res.status}），请检查服务是否启动`);
      }
      return await this._readSse(res.body, onProgress);
    } catch (err) {
      if (err?.name === "AbortError") {
        throw new Error(`zimeiti 后端响应超时（${Math.round(this.timeoutMs / 1000)}s），请稍后再试`);
      }
      if (err?.name === "TypeError" || /fetch failed|ECONNREFUSED/i.test(String(err?.cause || err))) {
        throw new Error("zimeiti 后端暂时不可达，请检查服务（make api）后重试");
      }
      throw err;
    } finally {
      clearTimeout(timer);
    }
  }

  async _readSse(body, onProgress) {
    const reader = body.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    let text = "";
    let event = "message";
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      let idx;
      while ((idx = buf.indexOf("\n")) >= 0) {
        const line = buf.slice(0, idx).replace(/\r$/, "");
        buf = buf.slice(idx + 1);
        if (!line) continue;
        if (line.startsWith("event:")) {
          event = line.slice(6).trim();
          continue;
        }
        if (!line.startsWith("data:")) continue;
        const payload = line.slice(5).trim();
        if (payload === "[DONE]") return text;
        const chunk =
          payload.startsWith('"') && payload.endsWith('"')
            ? payload.slice(1, -1)
            : payload;
        if (event === "token") {
          text += chunk;
        } else if (event === "activity" && onProgress) {
          onProgress(chunk);
        } else if (event === "error") {
          throw new Error(chunk || "zimeiti 返回未知错误");
        }
        event = "message";
      }
    }
    return text;
  }

  /** 连通性自检。 */
  async ping() {
    try {
      const res = await fetch(`${this.baseUrl}/api/status`, {
        headers: { Origin: this.baseUrl },
        signal: AbortSignal.timeout(5000),
      });
      return res.ok;
    } catch {
      return false;
    }
  }
}

export default { ZimeitiClient };
