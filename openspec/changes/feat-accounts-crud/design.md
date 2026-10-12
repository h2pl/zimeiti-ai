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
