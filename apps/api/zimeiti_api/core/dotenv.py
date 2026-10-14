""".env 加载（pg-data-layer 变更引入，零依赖实现）。

在包 import 时执行一次：已存在的环境变量优先，.env 损坏不阻断启动。
"""

from __future__ import annotations

import os
from pathlib import Path


def _load_dotenv(path: Path) -> None:
    """把 .env 文件加载进 os.environ（已存在的环境变量优先，不覆盖）。

    参考: Easel 的 .env 由 OpenClaw 网关进程自行读取（上游 openclaw 网关启动
    时加载项目根 .env）；zimeiti 移除 openclaw 后模型配置改为本进程直读
    os.environ（见 zimeiti_api/runtime/agent_runtime.py 的 OPENAI_API_KEY 读取），故需在此
    补齐加载，否则 apps/api/.env 不生效、对话恒走「未配置模型」降级分支。
    零依赖实现：项目未引入 python-dotenv，.env 格式简单（KEY=VALUE + # 注释）。
    """
    try:
        if not path.is_file():
            return
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    except Exception:
        pass  # .env 损坏不应阻断服务启动（模型未配置时有优雅降级分支）


_load_dotenv(Path(__file__).resolve().parent / ".env")
