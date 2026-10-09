"""集中配置：从环境变量/.env 读取（Task 2.1 前置）。"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# 仓库根（config.py = apps/api/src/zimeiti_api/config.py → parents[4]）
REPO_ROOT = Path(__file__).resolve().parents[4]

# 运行时数据唯一归宿：apps/api/data/（以 __file__ 绝对锚定，根治 cwd 依赖；
# 环境变量 ZIMEITI_DATA_DIR 可整体重定向）
DATA_DIR = Path(
    os.environ.get("ZIMEITI_DATA_DIR", str(Path(__file__).resolve().parents[2] / "data"))
)
AUDIT_PATH: str = os.environ.get("AUDIT_PATH", str(DATA_DIR / "audit" / "audit.jsonl"))
PENDING_PATH: str = os.environ.get(
    "PENDING_PATH", str(DATA_DIR / "state" / "pending_approvals.json")
)
CREDENTIALS_DIR: str = os.environ.get("ZIMEITI_CREDENTIALS_DIR", str(DATA_DIR / "credentials"))
LOGIN_STATE_PATH: str = os.environ.get(
    "XHS_LOGIN_STATE", str(DATA_DIR / "login" / "xhs_state.json")
)
OUTPUTS_DIR: str = os.environ.get("ZIMEITI_OUTPUTS_DIR", str(DATA_DIR / "outputs"))
PROFILES_DIR: str = os.environ.get("PROFILES_DIR", str(REPO_ROOT / "profiles"))
DATABASE_URL: str = os.environ.get(
    "DATABASE_URL",
    "postgresql://zimeiti:zimeiti_dev@localhost:5432/zimeiti",
)
