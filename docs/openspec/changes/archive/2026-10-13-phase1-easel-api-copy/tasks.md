## 1. 复制后端源码与配置

- [x] 1.1 复制 Easel `easel/` → `apps/api/easel/`，`web/app.py` → `apps/api/app.py` <!-- comet-task:65e2be98-bbc9-4a5c-8beb-f5c85d1d2c4d -->
- [x] 1.2 复制依赖配置（pyproject.toml / requirements）→ `apps/api` <!-- comet-task:bcf52849-47e6-41d2-881c-ad3c1c5ca70d -->
- [x] 1.3 验证：文件与 Easel 逐行一致，包目录无遗漏 <!-- comet-task:03a1d2af-454f-4388-ac33-6fb0f8ef806a -->

## 2. 安装依赖并启动服务

- [x] 2.1 准备 Python 环境并安装依赖 <!-- comet-task:20b6208f-69c4-42e8-a771-8770399d564d -->
- [x] 2.2 启动服务（指定空闲端口） <!-- comet-task:6b69826e-57be-4534-a174-f485623810f0 -->
- [x] 2.3 验证：`/api/status` 返回响应，服务无致命启动报错 <!-- comet-task:92769b0c-8cd5-447c-9ee8-bcc00f7db679 -->

## 3. 登记 OpenClaw 依赖清单

- [x] 3.1 梳理后端中依赖 OpenClaw 的模块并写入变更记录 <!-- comet-task:1baf9c7f-2ed1-4a21-8e02-10e4f6ff3b1f -->
- [x] 3.2 验证：清单覆盖所有 import openclaw 或调用 OpenClaw 命令的文件 <!-- comet-task:679ef89c-5390-43a5-93a2-9fc7cb98bc9c -->
