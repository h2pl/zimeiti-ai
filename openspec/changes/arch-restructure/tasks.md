# 任务：arch-restructure

> 模板任务引用 comet-task-ref 惯例；tdd_mode=direct，验证=全量回归+冒烟+grep。

## 1. 停机与骨架

- [x] T1 停止 :8000 网关进程（Windows 文件锁规避），确认 MCP 不受影响 <!-- comet-task:d99041b1-6ff9-4595-bcd0-52d3d378619c -->
- [x] T2 `git mv` 建六个子包骨架并移动模块（含 `__init__.py`）： <!-- comet-task:8daa8fe8-3f6b-41f0-b09e-1ced71bcb140 -->
      core/ governance/ platforms/（移入 xhs_readback, themes）/ content/
      operations/（ops_* 去 4 前缀）/ runtime/

## 2. 导入重写

- [x] T3 src 全量导入更新（`zimeiti_api.X` → 子包路径），含 config 锚点不动 <!-- comet-task:cf823d95-b612-4be4-b19c-e082ff5ffaa0 -->
- [x] T4 循环导入排查：`uv run python -c "import zimeiti_api.app"` 全链导入通过 <!-- comet-task:5bc82ca5-e11f-401f-a66e-8c0d6bb5c2f6 -->
- [x] T5 8 个 `python -m` 入口更新：Makefile / scripts/run_ops_daily.bat / <!-- comet-task:e2564449-d736-4b3e-bfc4-07651264618d -->
      run_hosted_daily.bat / scripts/walkthrough_*.py / xhs_readback 调用点

## 3. 测试镜像

- [x] T6 tests 按子包目录归位（27 个文件 git mv） <!-- comet-task:03f90c4d-1839-43af-a05a-d06e2a67ee0c -->
- [x] T7 test_p1_batch1/2 按被测模块拆分归位（postmortem/dna/templates/alias/themes） <!-- comet-task:9b7de973-c7fc-4629-b82d-5bf2ed564f88 -->
- [x] T8 conftest.py 与测试内部导入路径更新 <!-- comet-task:d8e7cd19-6de3-424a-9e62-1aac66b3bed5 -->

## 4. 验收

- [x] T9 make check 全绿（等价测试集 174 项，覆盖率 ≥80%） <!-- comet-task:70797527-1e2f-4c71-aaa4-f77125c9adbc -->
- [x] T10 入口冒烟：8 个 `python -m --help` 全部可用 + `zimeiti_api.app:app` 可导入 <!-- comet-task:ae2e6ed4-818d-4657-962f-fc639f0efd03 -->
- [x] T11 grep 验收：`zimeiti_api\.(ops_metrics|ops_daily|ops_calibration|ops_report_page|credentials_alias|publish_queue)` 零残留 <!-- comet-task:37e3703c-0b7f-4f11-a559-18d47dec1b02 -->
- [x] T12 AGENTS.md 目录结构段更新 <!-- comet-task:e31eafe3-7514-45f2-b278-8bb9adae1e57 -->
