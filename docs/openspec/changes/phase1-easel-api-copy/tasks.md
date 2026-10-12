## 1. 复制后端源码与配置

- [ ] 1.1 复制 Easel `easel/` → `apps/api/easel/`，`web/app.py` → `apps/api/app.py`
- [ ] 1.2 复制依赖配置（pyproject.toml / requirements）→ `apps/api`
- [ ] 1.3 验证：文件与 Easel 逐行一致，包目录无遗漏

## 2. 安装依赖并启动服务

- [ ] 2.1 准备 Python 环境并安装依赖
- [ ] 2.2 启动服务（指定空闲端口）
- [ ] 2.3 验证：`/api/status` 返回响应，服务无致命启动报错

## 3. 登记 OpenClaw 依赖清单

- [ ] 3.1 梳理后端中依赖 OpenClaw 的模块并写入变更记录
- [ ] 3.2 验证：清单覆盖所有 import openclaw 或调用 OpenClaw 命令的文件
