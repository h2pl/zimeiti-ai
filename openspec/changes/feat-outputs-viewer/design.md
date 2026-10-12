---
comet_change: feat-outputs-viewer
role: technical-design
canonical_spec: openspec
---

# 设计：feat-outputs-viewer

## 决策记录

- **D1 单篇产物读取**：`operations/workbench.py` 增 `output_detail(account, slug,
  outputs_dir)`——白名单校验 + 读 `OUTPUTS_DIR/<account>/<slug>/drafts.json`
  全量返回（正文是产物本体，量可控，不裁剪）。
- **D2 封面图**：端点直接 `FileResponse`（cover.png 存在判定；不存在 404）。
  路径拼接全部用 Path + 白名单，防 `../` 穿越。
- **D3 前端**：OutputsPage 条目展开面板（标题/正文/封面 + 合规徽章），
  api.ts 增 fetchOutputDetail / coverUrl helper。
