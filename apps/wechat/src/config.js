/** 路径与常量（程序/数据分离：代码在 src/，运行态在 state/）。 */

import { fileURLToPath } from "node:url";
import path from "node:path";

const HERE = path.dirname(fileURLToPath(import.meta.url));

export const APP_DIR = path.resolve(HERE, "..");
export const VENDOR_DIR = path.join(APP_DIR, "vendor", "openclaw-weixin");

export const ILINK_BASE_URL = "https://ilinkai.weixin.qq.com";

/** zimeiti 后端（桥接目标）。 */
export function zimeitiBase() {
  return process.env.ZIMEITI_API || "http://127.0.0.1:8000";
}

/**
 * 运行态目录（惰性解析）：默认 apps/wechat/state，WECHAT_STATE_DIR 可覆盖。
 * 惰性而非常量——测试在不同用例里切换隔离目录，且生产上免「env 必须在 import
 * 前设好」的时序坑（config 被传递导入时尤其隐蔽）。
 */
let _stateDir;
export function stateDir() {
  if (!_stateDir) {
    _stateDir = process.env.WECHAT_STATE_DIR
      ? path.resolve(process.env.WECHAT_STATE_DIR)
      : path.join(APP_DIR, "state");
  }
  return _stateDir;
}

export function accountsFile() {
  return path.join(stateDir(), "accounts.json");
}

export function sessionsFile() {
  return path.join(stateDir(), "sessions.json");
}
