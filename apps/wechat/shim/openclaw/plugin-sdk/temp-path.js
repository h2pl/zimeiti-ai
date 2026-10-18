/**
 * shim: openclaw/plugin-sdk/temp-path — resolvePreferredOpenClawTmpDir
 *
 * 依据（取证）：vendor 协议码中 util/logger.js 用它取「日志目录」（MAIN_LOG_DIR），
 * api.js/accounts.js/login-qr.js 均经 logger 传递依赖。语义等价实现：优先环境变量
 * WECHAT_LOG_DIR，否则 <os.tmpdir()>/zimeiti-wechat/logs。不创建目录（logger 侧
 * 自行 mkdir），只解析路径。
 */

import { tmpdir } from "node:os";
import path from "node:path";

export function resolvePreferredOpenClawTmpDir() {
  const base = process.env.WECHAT_LOG_DIR || path.join(tmpdir(), "zimeiti-wechat");
  return path.join(base, "logs");
}

export default { resolvePreferredOpenClawTmpDir };
