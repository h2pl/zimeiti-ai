"""Zimeiti AI 后端（backend-restructure：6 领域分包，对齐旧 zimeiti 规范化结构）。"""

import sys as _sys
from pathlib import Path as _Path

# 技能 shared 脚本与 apps/scripts 上级路径注入（model_registry 等按名 import）
# __init__.py 位于 apps/api/zimeiti_api/__init__.py：
#   parents[1]=apps/api, parents[2]=apps（数据目录与 skills 实际所在）
_API_DIR = _Path(__file__).resolve().parents[1]
_REPO_ROOT = _Path(__file__).resolve().parents[2]
for _p in (str(_API_DIR), str(_REPO_ROOT / "scripts"),
           str(_REPO_ROOT / "skills" / "shared" / "scripts")):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

from .core import dotenv as _dotenv  # noqa: E402,F401  包 import 即加载 .env
