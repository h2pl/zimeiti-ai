"""兼容 shim：入口已迁入包内（zimeiti_api/__main__.py）。

保留以兼容既有脚本（apps/scripts/verify_pg_data_layer.py）与习惯；
等价命令：python -m zimeiti_api
"""

from zimeiti_api.__main__ import main

if __name__ == "__main__":
    main()
