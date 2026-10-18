---
change: wechat-bridge-ops
design-doc: docs/openspec/changes/wechat-bridge-ops/design.md
base-ref: 6668d19
---

# Plan：群聊@触发 / 多账号 / 开机自驻

<!-- comet-task-authority: docs/openspec/changes/wechat-bridge-ops/tasks.md -->

## G1 群聊与多账号 <!-- comet-task-ref:431e8b3c-928f-4683-bb0e-9ddb851c9f06 --><!-- comet-task-ref:477fa86b-934f-4dec-a02c-c99fe223e6f4 -->

group.js（判定/@/前缀/清洗，字段名可配）+ dispatcher 接线（非@静默）；
start 多账号并行（单账号隔离）。

## G2 开机自驻 <!-- comet-task-ref:4d34bbf0-d08c-4442-888c-a9469a813fee --><!-- comet-task-ref:a295ac6e-65ba-4c0f-ad66-c3649fa4ef71 -->

services/ 模板 + install-service.sh；Python 单元守卫（13 项）；README 校准说明。

## G3 验证 <!-- comet-task-ref:5fa39c2c-0526-4811-85d3-c8271229f645 -->

node:test 36/36；make check 278 passed（含新守卫）；媒体探针 PASS；E2E 69/69。
