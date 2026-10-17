# stale-process-guard Specification

## Purpose
代码在进程启动后被变更（重构/移动模块/拉取更新）时，用户得到可行动的重启提示，
而不是 `No module named ...` 这类无法定位的模块解析异常。

## Requirements

### Requirement: 启动指纹与运行时守卫

系统 SHALL 在进程启动时对后端源码（zimeiti_api/ 与 zimeiti_harness/ 的 .py）
计算内容哈希快照；chat 类入口（run_turn / ask / ask_sync / chat_structured）
MUST 在执行前比对当前磁盘指纹，不一致时 SHALL 抛出含重启指引的中文错误，
且 MUST NOT 尝试继续执行可能触发 ImportError 的懒加载路径。

#### Scenario: 指纹一致放行
- **WHEN** 源码未变更（正常情况）
- **THEN** 守卫为 no-op，对话正常进行

#### Scenario: 指纹不一致拦截
- **WHEN** 进程启动后源码被移动/修改（如分层重构、git pull）
- **THEN** 返回「❌ 后端代码已变更（进程启动于旧版）——请重启后端
  （Ctrl+C 后重新 make api / make dev）再试」，不出现 ImportError 文本

### Requirement: verify 脚本随分层更新且收编进门禁

`verify_openclaw_removal.py` MUST 跟随 harness 分层后的路径；`make verify`
SHALL 接入 make check，防止验收脚本悄悄失效。

#### Scenario: make verify 通过
- **WHEN** 运行 make verify（或 make check）
- **THEN** openclaw 归零校验、路由数、runtime API 完整性检查全部通过
