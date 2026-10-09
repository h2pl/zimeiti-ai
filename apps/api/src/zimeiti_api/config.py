"""集中配置：从环境变量/.env 读取（Task 2.1 前置）。"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

AUDIT_PATH: str = os.environ.get("AUDIT_PATH", "outputs/_audit/audit.jsonl")
# 仓库根（config.py = apps/api/src/zimeiti_api/config.py → parents[4]）
REPO_ROOT = Path(__file__).resolve().parents[4]
PROFILES_DIR: str = os.environ.get("PROFILES_DIR", str(REPO_ROOT / "profiles"))
DATABASE_URL: str = os.environ.get(
    "DATABASE_URL",
    "postgresql://zimeiti:zimeiti_dev@localhost:5432/zimeiti",
)
