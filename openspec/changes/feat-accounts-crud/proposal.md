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
