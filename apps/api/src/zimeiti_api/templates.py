"""模板库：成功内容结构沉淀与复用（P1⑫）。

参考: Easel template-library——把成功内容存为带变量的模板，`render` 填变量复用。
MVP：模板文本支持 {{变量}} 占位；来源可以是人工提炼或从已发布草稿保存。
存储：data/state/templates.json（自用期运行时沉淀；后续如需共享再迁 profiles）。

用法：
  python -m zimeiti_api.templates save --name 痛点开场 --text "{{hook}}\n\n{{body}}"
  python -m zimeiti_api.templates list
  python -m zimeiti_api.templates render --name 痛点开场 --var hook=... --var body=...
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

VAR_RE = re.compile(r"\{\{(\w+)\}\}")


def _store_path() -> Path:
    from zimeiti_api.config import DATA_DIR

    return Path(DATA_DIR) / "state" / "templates.json"


def _load(path: Path | None = None) -> dict[str, Any]:
    p = path or _store_path()
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (ValueError, OSError):
        return {}


def save(name: str, text: str, note: str = "", path: Path | None = None) -> None:
    """保存/覆盖模板（同名单向覆盖——沉淀由人工把关）。"""
    store = _load(path)
    store[name] = {
        "text": text,
        "note": note,
        "vars": sorted(set(VAR_RE.findall(text))),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    p = path or _store_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")


def list_templates(path: Path | None = None) -> list[dict[str, Any]]:
    return [
        {"name": k, "vars": v.get("vars", []), "note": v.get("note", "")}
        for k, v in _load(path).items()
    ]


def render(name: str, variables: dict[str, str], path: Path | None = None) -> str:
    """按变量填充模板；缺变量 fail-closed 报错（不静默留占位符）。"""
    tpl = _load(path).get(name)
    if not tpl:
        raise KeyError(f"模板不存在: {name}")
    missing = [v for v in tpl["vars"] if v not in variables]
    if missing:
        raise ValueError(f"缺少变量: {missing}")
    out = tpl["text"]
    for k, v in variables.items():
        out = out.replace("{{" + k + "}}", v)
    return out


def main(argv: list[str] | None = None) -> int:
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    parser = argparse.ArgumentParser(description="模板库：成功内容结构沉淀与复用")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_save = sub.add_parser("save")
    p_save.add_argument("--name", required=True)
    p_save.add_argument("--text", required=True)
    p_save.add_argument("--note", default="")
    sub.add_parser("list")
    p_render = sub.add_parser("render")
    p_render.add_argument("--name", required=True)
    p_render.add_argument("--var", action="append", default=[], help="key=value，可重复")
    args = parser.parse_args(argv)

    if args.cmd == "save":
        save(args.name, args.text, args.note)
        print(json.dumps({"saved": args.name}, ensure_ascii=False))
        return 0
    if args.cmd == "list":
        print(json.dumps(list_templates(), ensure_ascii=False))
        return 0
    variables = dict(v.split("=", 1) for v in args.var if "=" in v)
    print(render(args.name, variables))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
