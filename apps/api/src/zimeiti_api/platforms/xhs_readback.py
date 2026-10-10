"""读回对账子进程 CLI。

为何独立子进程：litellm 模型调用会在进程内残留事件循环状态，导致 sync
Playwright 报「Sync API inside the asyncio loop」（A3 实测，线程隔离无效）；
子进程保证干净的循环环境。由 walkthrough/托管流程以 subprocess 调用。

用法：
    uv run python -m zimeiti_api.platforms.xhs_readback --title "标题" [--debug-dir DIR]
输出：JSON {"outcome": "verified|unverified"}
"""

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="小红书笔记管理读回对账")
    parser.add_argument("--title", required=True, help="待核验的笔记标题")
    parser.add_argument("--debug-dir", default=None, help="页面快照落盘目录")
    args = parser.parse_args(argv)

    from zimeiti_api.platforms.xhs import XhsPublisher

    pub = XhsPublisher()
    outcome = pub.readback(args.title, debug_dir=args.debug_dir)
    print(json.dumps({"outcome": outcome}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
