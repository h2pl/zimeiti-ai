"""多账号 alias 机制（P1⑭）。

参考: xiaobei wx-mp-publisher accounts.json（alias/appId + default 指针）。
zimeiti-ai 的账号体系已按 {account} 维度隔离（profiles/<account>/ + 凭证
{account}.sealed + 运营数据 platform 列）；本模块补 alias：同一账号的多个
别名（如矩阵号「主号」「备用号」）映射到真实 account，读取端统一解析。

配置：data/state/account-alias.json（运行时映射，不进 git）：
  {"主号": "xhs-main", "备用号": "xhs-main"}
"""

import json
from pathlib import Path

from zimeiti_api.core import audit


def alias_path() -> Path:
    from zimeiti_api.config import DATA_DIR

    return Path(DATA_DIR) / "state" / "account-alias.json"


def resolve(account_or_alias: str) -> str:
    """别名 → 真实 account（无映射原样返回；损坏映射 fail-closed 原样返回并留痕）。"""
    p = alias_path()
    if not p.exists():
        return account_or_alias
    try:
        mapping = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        audit.record("alias_map_corrupt")
        return account_or_alias
    target = mapping.get(account_or_alias)
    if isinstance(target, str) and target:
        return target
    return account_or_alias


def set_alias(alias: str, account: str) -> None:
    p = alias_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    mapping: dict[str, str] = {}
    if p.exists():
        try:
            mapping = json.loads(p.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            mapping = {}
    mapping[alias] = account
    p.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
    audit.record("alias_set", alias=alias, account=account)
