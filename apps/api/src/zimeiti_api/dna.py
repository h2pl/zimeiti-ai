"""风格 DNA 载体与回写工具（P1⑩）。

参考: xiaobei expert-xhs style-dna——每账号一份结构化风格 DNA 文档
（人可读、进 git），创作时注入 prompt；表现评估的改进建议**不得自动回写**
（xiaobei 纪律：Agent 不得自动更新 DNA），只生成建议清单，人工确认后编辑。

载体：profiles/dna/{account}.dna.md
结构约定（frontmatter+正文）：
---
version: 1
---
## 语气
...
## 结构套路
...
## 禁忌
...

用法：
  python -m zimeiti_api.dna show --account xhs-main
  python -m zimeiti_api.dna suggest --platform xhs-main   # 从最新校准/复盘报告提炼建议清单
"""

import argparse
import json
import sys
from pathlib import Path

DNA_DIR_NAME = "dna"


def dna_path(account: str) -> Path:
    from zimeiti_api.profiles import DEFAULT_BASE_DIR

    return Path(DEFAULT_BASE_DIR) / DNA_DIR_NAME / f"{account}.dna.md"


def load_dna(account: str) -> str:
    f = dna_path(account)
    if not f.exists():
        return ""
    return f.read_text(encoding="utf-8")


def inject_dna(profile_context: str, account: str) -> str:
    """把 DNA 正文拼接到画像上下文后（无 DNA 文件则原样返回）。"""
    dna = load_dna(account).strip()
    if not dna:
        return profile_context
    return f"{profile_context}\n\n## 风格 DNA（人工沉淀，优先级高于默认风格）\n\n{dna}"


def suggest_from_reports(platform: str) -> list[str]:
    """从最新校准/复盘报告提取改进建议（确定性规则，只列不做）。

    规则：校准报告「基线异常」段落 + 复盘报告的低于均值条目 → 建议清单。
    人工确认后编辑 DNA 文档——本函数绝不写 DNA。
    """
    from zimeiti_api.config import DATA_DIR

    suggestions: list[str] = []
    metrics_dir = Path(DATA_DIR) / "metrics"
    eval_files = sorted((metrics_dir / "evals").glob(f"{platform}-*.eval.md"))
    if eval_files:
        text = eval_files[-1].read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.startswith("- ") and "低于均值" in line:
                suggestions.append(f"（校准）{line[2:].strip()}")
    pm_files = sorted((metrics_dir / "postmortems").glob(f"{platform}-*.md"))
    if pm_files:
        text = pm_files[-1].read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.startswith("- 同期对照") and "低于均值" in line:
                suggestions.append(f"（复盘）{line[2:].strip()}")
    return suggestions


def main(argv: list[str] | None = None) -> int:
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    parser = argparse.ArgumentParser(description="风格 DNA：查看与建议（回写走人工）")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_show = sub.add_parser("show", help="查看 DNA 文档")
    p_show.add_argument("--account", required=True)
    p_sug = sub.add_parser("suggest", help="从报告生成建议清单（不回写）")
    p_sug.add_argument("--platform", required=True)
    args = parser.parse_args(argv)

    if args.cmd == "show":
        dna = load_dna(args.account)
        print(dna if dna else f"（{args.account} 尚无 DNA 文档：{dna_path(args.account)}）")
        return 0
    suggestions = suggest_from_reports(args.platform)
    print(
        json.dumps(
            {
                "suggestions": suggestions,
                "note": "人工确认后请编辑 " + str(dna_path(args.platform)),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
