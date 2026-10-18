/**
 * 群消息判定与@触发（wechat-bridge-ops）。
 *
 * 取证说明：vendor 协议层（api/login/accounts）**不含群处理**——群语义属宿主
 * 职责，由本桥自定。ilink 群消息真实字段名无法从代码证实，故按最常见约定
 * （room_id/group_id/chat_type）实现，且全部可用环境变量覆盖，README 记录了
 * 联调校准方法（打日志看真实字段后改一处配置）。
 */

const DEFAULT_GROUP_FIELDS = ["room_id", "group_id"];
const DEFAULT_GROUP_TYPE_FIELD = "chat_type";
const DEFAULT_GROUP_TYPE_VALUE = "group";
const DEFAULT_AT_FIELDS = ["is_at_me", "at_users", "mentioned_users"];

function _envList(name, fallback) {
  const raw = process.env[name];
  if (!raw) return fallback;
  return raw
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

function _firstString(msg, fields) {
  for (const f of fields) {
    const v = msg?.[f];
    if (typeof v === "string" && v.trim()) return v.trim();
  }
  return "";
}

/** 是否群消息。 */
export function isGroupMessage(msg, opts = {}) {
  const groupFields = opts.groupFields || _envList("WECHAT_GROUP_ID_FIELDS", DEFAULT_GROUP_FIELDS);
  if (_firstString(msg, groupFields)) return true;
  const typeField = opts.groupTypeField || DEFAULT_GROUP_TYPE_FIELD;
  const typeValue = opts.groupTypeValue || DEFAULT_GROUP_TYPE_VALUE;
  return String(msg?.[typeField] ?? "").toLowerCase() === String(typeValue).toLowerCase();
}

/** 群会话用户键（wxg- 前缀，防与私聊 wx- 混）。 */
export function groupUserId(msg, opts = {}) {
  const groupFields = opts.groupFields || _envList("WECHAT_GROUP_ID_FIELDS", DEFAULT_GROUP_FIELDS);
  return "wxg-" + (_firstString(msg, groupFields) || "unknown");
}

/** 是否@到了 bot（文本含 id/名称，或服务端 at 标记）。 */
export function isBotMentioned(msg, bot, opts = {}) {
  const atFields = opts.atFields || _envList("WECHAT_GROUP_AT_FIELDS", DEFAULT_AT_FIELDS);
  for (const f of atFields) {
    const v = msg?.[f];
    if (v === true) return true;
    if (Array.isArray(v) && v.length) {
      if (bot?.id && v.some((x) => String(x) === String(bot.id))) return true;
      if (v.length) return true; // 非空 at 列表且未给 bot.id 时保守视为@到我
    }
  }
  const text = String(msg?.content ?? msg?.text ?? "");
  const needles = [bot?.id, bot?.name].filter(Boolean).map(String);
  return needles.some((n) => text.includes(n));
}

/** 去掉@前缀，给 agent 干净文本。 */
export function stripMention(text, bot) {
  let out = String(text ?? "");
  const needles = [bot?.name, bot?.id].filter(Boolean).map(String);
  for (const n of needles) {
    out = out.replace(new RegExp(`@?${n.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}`, "g"), "");
  }
  return out.replace(/^\s*[@＠\s]+/, "").trim();
}

/** 群内是否要求@（默认要求；WECHAT_GROUP_REQUIRE_MENTION=false 关闭）。 */
export function requireMention() {
  return String(process.env.WECHAT_GROUP_REQUIRE_MENTION ?? "true").toLowerCase() !== "false";
}
