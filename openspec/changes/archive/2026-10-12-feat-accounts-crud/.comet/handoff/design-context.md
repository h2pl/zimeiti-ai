# Comet Design Handoff

- Change: feat-accounts-crud
- Phase: design
- Mode: compact
- Context hash: 95a01d4107075369280d0889b00d455e1314302a2108231472c03a59e55897a7

Generated-by: comet-handoff.sh
Task hash policy: task-content-v1. Read tasks.md for live completion; excerpts are design-time context.

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## openspec/changes/feat-accounts-crud/proposal.md

- Source: openspec/changes/feat-accounts-crud/proposal.md
- Lines: 1-29
- SHA256: 6796e21b3eeffd5b1aacc71e82e3b67119c915a954402cf3577e083fda892059

```md
# 提案：账号增删管理（feat-accounts-crud）

## Why

对齐缺口矩阵 ⚠ 第 3 项：AccountsPage 只有状态管理；Easel 有账号增删 UI。
当前加账号=手工建 profile.yaml+seal，删账号无入口。

## What Changes

- 后端：
  - `POST /api/accounts`：创建账号（body = 画像全量数据；account 白名单 +
    不存在校验 + validate_profile；创建 profile.yaml + platform_state 启用）
  - `DELETE /api/accounts/{account}`：删除账号（profile.yaml + platform_state
    状态 + 凭证文件一并删除，全部写入审计；不存在 404）
- 前端 AccountsPage：「新建账号」表单（含必填字段校验提示）+ 删除按钮
  （二次确认）

## Capabilities

- **Modified Capabilities**: `web-workbench`（ADDED：账号创建/删除需求）

## Non-Goals

- 凭证采集 UI（创建后凭证状态显示缺失，用户走 seal CLI 补齐——发布门禁会拦）

## 关键决策

- 删除是危险操作：凭证文件一并删（避免孤儿凭证残留）但全程审计
  （account_deleted 事件记录删除清单）

```

## openspec/changes/feat-accounts-crud/design.md

- Source: openspec/changes/feat-accounts-crud/design.md
- Lines: 1-19
- SHA256: b674e44ad8285cac95b623b15636b41d1fabab74f160b8d960e6a0b0c3620747

```md
---
comet_change: feat-accounts-crud
role: technical-design
canonical_spec: openspec
---

# 设计：feat-accounts-crud

## 决策记录

- **D1 创建**：`operations/workbench.py` 增 `create_account(data, profiles_dir)`——
  account 白名单 + 目录不存在校验（409 由端点转）+ validate_profile +
  `yaml.safe_dump` 落盘 + platform_state.ensure_defaults（新键启用）。
- **D2 删除**：`delete_account(account, profiles_dir, credentials_dir, state_path)`
  ——shutil.rmtree 删账号画像目录 + platform_state 移除键（新 helper
  `platform_state.remove_account`）+ 凭证文件删除；每步审计。
  platform_state 删键需新方法 `remove_account(account)`（容错：键不存在跳过）。
- **D3 端点**：POST /api/accounts（201）；DELETE /api/accounts/{account}（200/404）。
  两者审计 account_created / account_deleted。

```

## openspec/changes/feat-accounts-crud/tasks.md

- Source: openspec/changes/feat-accounts-crud/tasks.md
- Lines: 1-6
- SHA256: b512ed4586f9d90f285862af03f5221b6c7a8ba22d15fbfcf8c62823598aa1b3

```md
# 任务：feat-accounts-crud

- [ ] T1 后端：create_account/delete_account + platform_state.remove_account
      + POST/DELETE 端点 + 测试
- [ ] T2 前端：AccountsPage 新建表单 + 删除按钮（二次确认）
- [ ] T3 make check + npm build + spec 场景核对

```

## openspec/changes/feat-accounts-crud/.openspec.yaml

- Source: openspec/changes/feat-accounts-crud/.openspec.yaml
- Lines: 1-2
- SHA256: 1dfdca412094f24473d8b842866201ec26f200b29b17064b03f1e4982c35a7b9

```md
schema: spec-driven
created: 2026-10-12

```

## openspec/changes/feat-accounts-crud/specs/web-workbench/spec.md

- Source: openspec/changes/feat-accounts-crud/specs/web-workbench/spec.md
- Lines: 1-26
- SHA256: 0057965c41b7b4a4a667fe1bce0ba2660bb1cb234f7ddea9384fc644c0ef8238

```md
# web-workbench 能力增量（feat-accounts-crud）

## ADDED Requirements

### Requirement: 账号创建

`POST /api/accounts` 创建账号：account 白名单 + 不存在校验（409）+ 画像数据
validate_profile（400）；成功创建 profile.yaml 并启用。前端提供新建表单。

#### Scenario: 创建合法账号
- **When** POST 合法画像数据
- **Then** profile.yaml 生成、账号出现在列表且为启用态

#### Scenario: 重复创建被拒绝
- **When** POST 已存在的 account
- **Then** 返回 409，原画像不变

### Requirement: 账号删除

`DELETE /api/accounts/{account}`：删除 profile.yaml + platform_state 记录 +
凭证文件（避免孤儿凭证），全程审计（account_deleted）；不存在 404。前端
删除按钮需二次确认。

#### Scenario: 删除账号清理凭证
- **When** 删除带 .sealed 凭证的账号
- **Then** 画像文件与凭证文件均消失，审计记录 account_deleted

```
