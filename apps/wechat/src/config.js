/** 路径与常量（程序/数据分离：代码在 src/，运行态在 state/）。 */

import { fileURLToPath } from "node:url";
import path from "node:path";

const HERE = path.dirname(fileURLToPath(import.meta.url));

export const APP_DIR = path.resolve(HERE, "..");
export const VENDOR_DIR = path.join(APP_DIR, "vendor", "openclaw-weixin");
export const STATE_DIR = path.join(APP_DIR, "state");
export const ACCOUNTS_FILE = path.join(STATE_DIR, "accounts.json");
export const SESSIONS_FILE = path.join(STATE_DIR, "sessions.json");

export const ILINK_BASE_URL = "https://ilinkai.weixin.qq.com";

/** zimeiti 后端（桥接目标，变更 wechat-bridge-transport 启用）。 */
export const ZIMEITI_BASE =
  process.env.ZIMEITI_API || "http://127.0.0.1:8000";
