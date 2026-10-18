---
comet_change: wechat-bridge-scaffold
---

# 验证报告：wechat-bridge-scaffold（微信协议码 vendor + 宿主骨架）

## Spec 场景核对

| Scenario | 结果 | 证据 |
|---|---|---|
| 合规三件套（LICENSE/NOTICE/未改动声明） | ✅ | 单测 `vendor 合规三件套 + 协议码可 import`；守卫 `[1/3]` 断言 LICENSE 含 MIT+Tencent、NOTICE 含包名/版本/「未改动」 |
| 防篡改（vendor 哈希） | ✅ | 守卫 `[2/3]` MANIFEST 逐文件 sha256；**牙齿验证**：追加一行到 `api.js` 当即报红 `vendor 文件被改动`，从上游副本恢复后 PASS |
| 零 openclaw 引擎依赖 | ✅ | 守卫 `[3/3]`：源码 import 的 `openclaw/plugin-sdk/*` 必须在 shim exports 内；`package.json` 的 openclaw 依赖必须是 `file:` 本地 shim |
| status 未登录给出指引 + 非 0 退出 | ✅ | CLI 冒烟：`node src/index.js status` → 「未登录。执行 login…」rc=1 |
| 登录态落盘（假 transport 驱动） | ✅ | 单测覆盖 shim 两 helper 语义与 sessions 落盘；真实扫码流程需人工（留用户首次 `login`） |

## 可行性取证结论（本变更的核心依据）

npm 拆包 + 源码审读（`@tencent-weixin/openclaw-weixin@2.4.10`，MIT，Tencent 官方）：

- 协议形态：**ilink bot API**——`ilink/bot/getupdates`（长轮询收）/
  `sendmessage`（发）/`getconfig`/`sendtyping`/`notifystart`/`notifystop`；
  登录为 `startWeixinLoginWithQr` + `waitForWeixinLogin`（二维码轮询）
- `api.js` 与 `login-qr.js` **零** `openclaw/plugin-sdk` import；
  `accounts.js` 用 2 个 helper；`util/logger.js`（被上述全部传递依赖）用第 3 个
  （`temp-path`）→ **shim 只需实现 3 个**
- openclaw 引擎/gateway/配置系统**一行未引入**（peerDependency 仅为上游宿主
  装配所需，与本桥无关）

## 过程中修正的三处（诚实记录）

1. **shim 依赖面取证遗漏**：首跑测试即 `ERR_PACKAGE_PATH_NOT_EXPORTED`——
   `logger.js` 传递依赖 `temp-path` 没在初版 shim 里。补齐后全绿。教训：
   「直接依赖零依赖」不等于「可达依赖零依赖」，要看传递闭包
2. **桥循环 microtask 饥饿**：假 transport 立即 resolve 时循环自旋饿死测试
   定时器（真实长轮询是 30s 网络 I/O 不会发生）。生产侧加 `setImmediate` 让出行
   （顺带避免服务端立即返回时的 CPU 自旋），测试侧模型真实延迟——双保险
3. **`node --test test/` 在 Windows Node 24 被当模块路径**：改裸
   `node --test`（自动发现）

## 自动化验证

- **node:test 6/6**：shim 两 helper 语义（含串行写/不存在默认值）/桥轮询分发与
  停机/轮询失败退避重试/会话映射稳定性/vendor 合规与协议可 import
- **CLI 冒烟**：`status` 未登录 rc=1；`version` rc=0（输出协议码版本 2.4.10）；
  未知命令 rc=2
- **make check**：exit 0，**278 passed**（新增 verify 第七连：微信桥 vendor 守卫）
- **E2E 全量**：69/69、双端差异 0（Node 侧新增不影响浏览器层）
- 门禁超时插曲：build check 首跑 900s 超时（exit 124，全量测试约 15 分钟贴限），
  加至 2400s 后通过——后续变更的门禁一律用 2400s

## 已知边界（留给后续变更）

- `start`（常驻桥接）为占位：**消息尚未桥到 zimeiti**——`wechat-bridge-transport`
- 媒体（图片/语音）、群聊、多账号 allowlist：后续变更
- 真实扫码登录需人工执行 `node src/index.js login`（8 分钟二维码窗口）
