/**
 * shim: openclaw/plugin-sdk/config-mutation — mutateConfigFile
 *
 * 依据（取证）：vendor 协议码中仅 accounts.js 引用，用途是「读 JSON 配置 →
 * 原地修改 → 原子写回」。语义等价实现：读（不存在给默认）→ mutate 回调 → 写临时
 * 文件 → rename 原子替换。串行队列防并发写丢更新。
 */

import { rename, writeFile, readFile, mkdir } from "node:fs/promises";
import { dirname } from "node:path";

const _locks = new Map(); // path -> Promise（串行队列）

async function _withLock(path, fn) {
  const prev = _locks.get(path) ?? Promise.resolve();
  const run = prev.then(fn, fn); // 前一个成败都不影响后续
  _locks.set(path, run.catch(() => {}));
  return run;
}

async function _readJson(path, fallback) {
  try {
    return JSON.parse(await readFile(path, "utf8"));
  } catch {
    return fallback;
  }
}

export async function mutateConfigFile(path, mutate, options = {}) {
  const fallback = options.defaultValue ?? {};
  return _withLock(path, async () => {
    const current = await _readJson(path, fallback);
    const next = await mutate(structuredClone(current));
    await mkdir(dirname(path), { recursive: true });
    const tmp = `${path}.tmp-${process.pid}-${Date.now()}`;
    await writeFile(tmp, `${JSON.stringify(next, null, 2)}\n`, "utf8");
    await rename(tmp, path); // 同目录原子替换
    return next;
  });
}

export default { mutateConfigFile };
