---
comet_change: agent-shell-exec
---

# 设计：白名单命令执行器

## 高层方案

```
agent 调用 exec_script(name="ai_score", args={...})
        │
ExecTool（apps/api/zimeiti_api/runtime/exec_tool.py）
  ├─ 注册表查名（不在 → 拒绝，列出可用脚本）
  ├─ 参数校验（脚本声明的 schema；含 ../ 绝对路径 $ ` | → 拒绝）
  ├─ subprocess.run([python, <绝对脚本路径>, *参数], cwd=数据根,
  │                timeout=120, capture_output, env=PYTHONUTF8=1)
  └─ 返回 {exit_code, stdout(尾部8KB), stderr(尾部2KB)}
        │
注册表（静态 dict）：ai_score / render_card / …（首批既有脚本盘点后登记）
```

## 关键决策

### D1：自写 ExecTool 而非 deepagents SandboxBackend
deepagents 的 `execute` 工具走 SandboxBackendProtocol（LocalShellBackend = 任意命令，违安全约束；Docker 沙箱过重）。自写一个 LangChain `@tool`，注册表+校验+资源约束全在 80 行内可控。

### D2：参数校验策略
白名单脚本统一约定 `--flag value` 形态（无位置参数、无 shell 语法）。ExecTool 校验：每个 flag 在脚本 schema 内；每个 value 不含 `..`、不以 `/` 或盘符开头、不含 `$ \` \` | ; &`。脚本路径本身来自注册表常量，不受参数影响。

### D3：超时与输出
timeout 120s（渲染类脚本足够）；stdout 尾部 8KB + stderr 尾部 2KB（质检报告通常在尾部汇总）。环境变量强制 `PYTHONUTF8=1`，规避 Windows GBK 子进程解码坑（同 ripgrep 补丁的教训）。

### D4：注册表首批盘点
实现时盘点 `skills/shared/scripts/` 下可独立运行、无交互的脚本（ai_score.py / render_card.py 等），逐个登记并写明参数 schema；需要 TTY/凭据的脚本不注册。

## 风险与对策

- **风险**：脚本自身不幂等或写坏数据 → 对策：首批只注册只读质检类与确定性渲染类脚本；写操作类（如 draft 上传）暂不注册
- **风险**：agent 用 ExecTool 绕过文件写权限 → 对策：脚本以数据根为 cwd，其自身写盘行为由脚本作者负责；注册表评审时把关

## Open Questions

无。
