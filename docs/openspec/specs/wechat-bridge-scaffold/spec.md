# wechat-bridge-scaffold Specification

## Purpose
合规地 vendor 腾讯官方 ilink 微信协议码，并提供不依赖 openclaw 的 Node 宿主
骨架，使「扫码登录 + 长轮询收 + 发送」能力可在 zimeiti 部署中独立运行。

## Requirements

### Requirement: 协议码合规 vendor

`apps/wechat/vendor/openclaw-weixin/` SHALL 原样收录 `@tencent-weixin/openclaw-weixin`
的 MIT 协议码，MUST NOT 修改其源码；仓库 MUST 含 NOTICE 记录来源、版本、许可与
「未改动」声明；`make check` MUST 断言 LICENSE/NOTICE 存在且 vendor 文件与上游
tarball 内容哈希一致（防偷偷改动）。

#### Scenario: 合规三件套
- **WHEN** 检查 `apps/wechat/`
- **THEN** 存在 `vendor/openclaw-weixin/LICENSE`、`NOTICE`，且 NOTICE 含包名、
  版本号、MIT 声明与「未改动」说明

#### Scenario: 防篡改
- **WHEN** 任何人修改了 vendor 内任一协议码文件
- **THEN** `make check` 的 vendor 完整性断言失败（哈希不一致）

### Requirement: 零 openclaw 依赖

宿主与 shim MUST NOT 依赖 openclaw 引擎：不得安装 `openclaw` 包、不得 import
其 gateway/配置系统；对 `openclaw/plugin-sdk/*` 的引用 MUST 由本地 shim 满足。
`make check` MUST 有断言扫描 `apps/wechat/`（vendor 除外）无 openclaw 引擎依赖。

#### Scenario: 依赖面
- **WHEN** 检查 `apps/wechat/package.json` 与全部源码 import
- **THEN** dependencies 不含 `openclaw`；源码 import 的 `openclaw/plugin-sdk/*`
  全部经 shim 的 exports 映射解析

### Requirement: 宿主骨架可用

CLI SHALL 提供 `login`（终端二维码 + 扫码轮询，落盘登录态）、`status`（登录态
与配置自检）、`version`（协议码版本）；长轮询与发送封装 MUST 以可注入的
transport 实现（单测不触网）。

#### Scenario: 状态自检
- **WHEN** 未登录时执行 `node src/index.js status`
- **THEN** 输出「未登录」并给出 `login` 指引，退出码非 0

#### Scenario: 登录态落盘
- **WHEN** 完成一次登录流程（单测以假 transport 驱动）
- **THEN** 登录态写入 `apps/wechat/state/`（gitignore），`status` 识别为已登录
