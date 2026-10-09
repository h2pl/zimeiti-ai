"""凭证加密存储（Task 6.4，宪法原则 II）。

Fernet 对称加密，主密钥来自环境变量 ZIMEITI_MASTER_KEY；
未设置时从 ZIMEITI_MASTER_KEY_FILE 读取；两者都没有则拒绝工作（fail-closed）。
"""

import base64
import os

from cryptography.fernet import Fernet

_MASTER_KEY_ENV = "ZIMEITI_MASTER_KEY"


def _load_master_key() -> bytes:
    key = os.environ.get(_MASTER_KEY_ENV)
    if not key:
        key_file = os.environ.get("ZIMEITI_MASTER_KEY_FILE")
        if key_file and os.path.exists(key_file):
            key = open(key_file, encoding="utf-8").read().strip()
    if not key:
        raise RuntimeError(
            "未设置主密钥：请设置 ZIMEITI_MASTER_KEY 环境变量"
            '（生成方式：python -c "import os,base64;'
            'print(base64.urlsafe_b64encode(os.urandom(32)).decode())"）'
        )
    # 允许用户直接粘贴 Fernet key（44 字符 urlsafe base64）
    try:
        Fernet(key.encode())
        return key.encode()
    except Exception:
        # 任意字符串主密钥 → 派生为合法 Fernet key
        digest = __import__("hashlib").sha256(key.encode()).digest()
        return base64.urlsafe_b64encode(digest)


def encrypt_secret(plaintext: str) -> str:
    """加密平台凭证，返回密文（Fernet token，含时间戳）。"""
    return Fernet(_load_master_key()).encrypt(plaintext.encode()).decode()


def decrypt_secret(sealed: str) -> str:
    """解密凭证；密文被篡改抛 InvalidToken。"""
    return Fernet(_load_master_key()).decrypt(sealed.encode()).decode()


def load_for_account(account: str, credentials_dir: str | None = None) -> str:
    """读取指定账号的解密凭证（密文文件由登录/配置流程以 encrypt_secret 落盘）。"""
    from pathlib import Path

    cred_dir = Path(
        credentials_dir
        or os.environ.get("ZIMEITI_CREDENTIALS_DIR")
        or __import__("zimeiti_api.config", fromlist=["CREDENTIALS_DIR"]).CREDENTIALS_DIR
    )
    f = cred_dir / f"{account}.sealed"
    if not f.exists():
        raise FileNotFoundError(f"账号 {account} 无已存凭证: {f}")
    return decrypt_secret(f.read_text(encoding="utf-8").strip())
