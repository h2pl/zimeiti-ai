"""双端观测值对齐比较。"""

from __future__ import annotations

import json


def compare(zo: dict, eo: dict) -> tuple[list[str], list[str]]:
    """比较两端观测值，返回 (diffs, notes)。

    规则（spec「双端行为一致性」）：
    - 结构级布尔/列表必须一致 → diffs
    - 环境性差异（回复文本 kind、外部数据条数）→ notes 只报告
    """
    diffs: list[str] = []
    notes: list[str] = []
    for key in sorted(set(zo) | set(eo)):
        zv, ev = zo.get(key), eo.get(key)
        # 场景键形如 S05——归一成 S5 再判断语义分支
        sid = key[0] + str(int(key[1:])) if len(key) > 2 and key[0] == "S" and key[1:].isdigit() else key
        if sid == "S5":
            for f in ("started", "completed", "has_reply"):
                if bool((zv or {}).get(f)) != bool((ev or {}).get(f)):
                    diffs.append(f"S5.{f}: zimeiti={zv} easel={ev}")
            if (zv or {}).get("reply_kind") != (ev or {}).get("reply_kind"):
                notes.append(
                    f"S5 回复形态（环境差异不判失败）: zimeiti={(zv or {}).get('reply_kind')} "
                    f"easel={(ev or {}).get('reply_kind')}"
                )
        elif sid == "S10":
            # 热点数据来自外部站点：页面渲染是结构事实必须一致；
            # 条目数与跳转与否随外部数据可用性浮动 → NOTE 不判失败（spec：数据条数只报告）
            if bool((zv or {}).get("rendered")) != bool((ev or {}).get("rendered")):
                diffs.append(f"S10.rendered: zimeiti={zv} easel={ev}")
            else:
                notes.append(f"S10 热点条目（环境差异）: zimeiti={(zv or {}).get('topics')} easel={(ev or {}).get('topics')}")
        elif key == "js_errors_total":
            if bool(zv) != bool(ev):
                diffs.append(f"JS 错误: zimeiti={zv} easel={ev}")
        elif key == "js_error_samples":
            continue  # 随 js_errors_total 判
        else:
            if zv != ev:
                diffs.append(f"{key}: zimeiti={_short(zv)} easel={_short(ev)}")
    return diffs, notes


def _short(v) -> str:
    s = json.dumps(v, ensure_ascii=False, default=str) if not isinstance(v, str) else v
    return s[:120]
