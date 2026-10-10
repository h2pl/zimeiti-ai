# Brainstorm Summary

- Change: arch-restructure
- Date: 2026-10-10

## Confirmed Technical Approach

用户已在 Open 工件确认（含设计）：35 个平铺模块按领域分 6 子包
（core/governance/platforms/content/operations/runtime），分层单向依赖
runtime→{governance,platforms,content,operations}→core；ops_ 前缀去除
（metrics/daily/calibration/report_page）；credentials_alias→core/alias；
8 个 python -m 入口全量更新不留垫片；测试镜像同构 + test_p1_batch1/2 拆分归位；
tdd_mode=direct（174 项全量回归等价性 + 入口冒烟 + grep 零残留）。

## Key Tradeoffs and Risks

- 不留 re-export 双轨：仓库内闭环无外部消费者，避免两套真相
- 循环导入可能被平铺结构掩盖 → 移动后立即全链 import 检查，就地局部导入化解
- Windows 文件锁（网关运行中）→ 重构前停 :8000 进程
- diff 半径控制：类名/函数名不改，仅模块移动与 ops_ 前缀去除

## Test Strategy

tdd_mode=direct：不新增测试；验收=make check 全绿（测试集合等价）+ 8 入口
冒烟（python -m --help）+ 旧路径残留 grep 为零 + zimeiti_api.app 可导入。

## Spec Patch

None（skip_specs: true——纯重构无行为规格变化）
