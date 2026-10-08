"""集中配置：从环境变量/.env 读取（Task 2.1 前置）。"""

import os

from dotenv import load_dotenv

load_dotenv()

AUDIT_PATH: str = os.environ.get("AUDIT_PATH", "outputs/_audit/audit.jsonl")
DATABASE_URL: str = os.environ.get(
    "DATABASE_URL",
    "postgresql://zimeiti:zimeiti_dev@localhost:5432/zimeiti",
)
