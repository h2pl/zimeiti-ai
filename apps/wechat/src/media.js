/**
 * 微信媒体收发（wechat-bridge-media）。
 *
 * 入站：item_list 提取媒体项 → vendor `downloadMediaFromItem`（字段名/AES 解密/
 *       silk 转码的权威实现）下载解密 → 落盘 → 告知 agent 路径（不假装理解）。
 * 出站：解析 agent 回复中独占一行的 `MEDIA:<path|url>` 指令（openclaw 同款约定）
 *       → vendor `sendWeixinMediaFile`（按 MIME 路由 image/video/file）。
 * 下载/发送均可注入——默认惰性加载 vendor 函数（真实环境），测试注入 fake。
 */

import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { stateDir } from "./config.js";

// vendor api/types.js 的 MessageItemType（字节级一致，勿改）
const ITEM = { NONE: 0, TEXT: 1, IMAGE: 2, VOICE: 3, FILE: 4, VIDEO: 5 };

const EXT_BY_TYPE = { [ITEM.IMAGE]: "png", [ITEM.VOICE]: "silk", [ITEM.FILE]: "bin", [ITEM.VIDEO]: "mp4" };

// vendor auth/accounts.js 的 CDN_BASE_URL 默认值（登录态未显式配置时兜底）
const VENDOR_CDN_BASE_URL = "https://novac2c.cdn.weixin.qq.com/c2c";

export function mediaLabel(type, saved) {
  switch (type) {
    case ITEM.IMAGE:
      return "图片";
    case ITEM.VOICE:
      return saved?.voiceMediaType === "audio/wav"
        ? "语音（已转码为 WAV）"
        : "语音消息（silk 格式，暂不支持转码）";
    case ITEM.FILE:
      return "文件";
    case ITEM.VIDEO:
      return "视频";
    default:
      return "媒体";
  }
}

/** 从入站消息提取媒体项（TEXT 不计；保留原始 item 供 vendor 下载器解析）。 */
export function extractMediaItems(msg) {
  const list = Array.isArray(msg?.item_list) ? msg.item_list : [];
  const out = [];
  list.forEach((item, idx) => {
    const type = Number(item?.type);
    if (type === ITEM.TEXT || type === ITEM.NONE) return;
    out.push({
      type,
      idx,
      msgId: String(msg?.msg_id || msg?.message_id || `m-${Date.now()}`),
      name: String(item?.file_item?.file_name || item?.name || ""),
      item, // 原始 item：vendor downloadMediaFromItem 的输入
    });
  });
  return out;
}

/** 默认入站下载器：vendor media-download（权威字段名 + AES 解密 + silk 转码尝试）。 */
export async function defaultDownloadMedia(item, opts = {}) {
  const { downloadMediaFromItem } = await import(
    "../vendor/openclaw-weixin/dist/src/media/media-download.js"
  );
  let captured = null;
  const result = await downloadMediaFromItem(item.item, {
    cdnBaseUrl: opts.cdnBaseUrl || "",
    saveMedia: async (buf, _mime, _subdir, _max, fileName) => {
      captured = { buf, fileName };
      return { path: fileName || "captured" };
    },
    log: () => {},
    errLog: () => {},
    label: "inbound",
  });
  if (!captured) {
    throw new Error("媒体下载失败（无可下载内容或字段缺失）");
  }
  return { buffer: captured.buf, fileName: captured.fileName, meta: result };
}

/** 下载解密落盘。downloadMedia 可注入；失败逐项隔离。 */
export async function saveInboundMedia(items, { downloadMedia, dir } = {}) {
  if (!items?.length) return [];
  const base = dir || path.join(stateDir(), "media");
  const today = new Date().toISOString().slice(0, 10);
  const outDir = path.join(base, today);
  await mkdir(outDir, { recursive: true });
  const results = [];
  for (const it of items) {
    const ext = EXT_BY_TYPE[it.type] || "bin";
    const name = it.name || `${it.msgId}-${it.idx}.${ext}`;
    const filePath = path.join(outDir, name);
    try {
      const dl = await downloadMedia(it);
      const buf = Buffer.isBuffer(dl) ? dl : dl?.buffer;
      if (!buf) throw new Error("下载器未返回内容");
      await writeFile(filePath, buf);
      results.push({
        ...it,
        path: filePath,
        ok: true,
        error: "",
        voiceMediaType: dl?.meta?.voiceMediaType,
      });
    } catch (err) {
      results.push({ ...it, path: "", ok: false, error: String(err?.message || err).slice(0, 200) });
    }
  }
  return results;
}

/** 喂给 agent 的媒体附注（类型/路径；silk 如实标注不支持转码）。 */
export function buildInboundNote(saved) {
  return saved
    .filter((s) => s.ok)
    .map((s) => `用户发送了${mediaLabel(s.type, s)}，已保存到 ${s.path}`)
    .join("\n");
}

/** 用户侧的入站确认（含 silk 提示）。 */
export function buildInboundReceipt(saved) {
  const ok = saved.filter((s) => s.ok);
  const bad = saved.filter((s) => !s.ok);
  const parts = [];
  if (ok.length) {
    const labels = ok.map((s) => mediaLabel(s.type, s).replace(/（.*/, ""));
    parts.push(`已收到${labels.join("、")}`);
    const voice = ok.find((s) => s.type === ITEM.VOICE && s.voiceMediaType !== "audio/wav");
    if (voice) parts.push("语音暂不支持转码，已保存原文件");
  }
  if (bad.length) parts.push(`有 ${bad.length} 个媒体下载失败`);
  return parts.join("；") || "（无媒体）";
}

/**
 * 解析出站 MEDIA: 指令（独占一行；路径含空格保真；file:// 剥离）。
 * 返回 { text（剥离指令行）, media[] }。
 */
export function parseMediaDirectives(text) {
  const lines = String(text ?? "").split("\n");
  const media = [];
  const kept = [];
  for (const line of lines) {
    const m = line.match(/^\s*MEDIA:\s*(.+?)\s*$/);
    if (m) {
      let ref = m[1];
      if (ref.startsWith("file://")) ref = ref.slice("file://".length);
      media.push(ref);
      continue;
    }
    kept.push(line);
  }
  // 折叠因剥离产生的连续空行（保留段落结构）
  const out = kept.join("\n").replace(/\n{3,}/g, "\n\n").trim();
  return { text: out, media };
}

/** 默认出站发送器：vendor send-media（按 MIME 路由 image/video/file）。 */
export async function defaultSendMedia({ filePath, to, text, baseUrl, token, cdnBaseUrl }) {
  const { sendWeixinMediaFile } = await import(
    "../vendor/openclaw-weixin/dist/src/messaging/send-media.js"
  );
  return sendWeixinMediaFile({
    filePath,
    to,
    text,
    opts: { baseUrl, token },
    cdnBaseUrl: cdnBaseUrl || VENDOR_CDN_BASE_URL,
  });
}

export { ITEM as MessageItemType };
