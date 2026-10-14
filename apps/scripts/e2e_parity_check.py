"""zimeiti-ai 与 Easel 上游的 API 端到端对比验收。

对同一批只读端点分别请求两边服务，对比 HTTP 状态码与响应体结构
（dict 的键集合 / list 的长度），输出差异矩阵。

用法（两边服务均已启动）：
    python e2e_parity_check.py [--zimeiti http://127.0.0.1:8000] [--easel http://127.0.0.1:7860]

只覆盖 GET 只读端点与无副作用 POST：不触发登录、发布、LLM 对话、文件写入等行为。
已知有意差异（不算缺陷）：
    - /api/settings/local-agents、/api/settings/local-agents/enable：
      remove-openclaw 变更移除的 OpenClaw 本地代理端点
    - /api/skills 数量（1 vs 114）：zimeiti 仅移植 skill-wechat-publisher

Windows 注意：Easel 上游的 web/app.py 启动横幅含非 GBK 字符，且取数子进程
输出 UTF-8，若两边编码环境不一致会出现「 Easel 502 但手工跑脚本正常」的假象。
启动 Easel 时用 `PYTHONUTF8=1`（而非 PYTHONIOENCODING，后者会让父子编码不一致，
父进程 subprocess text=True 按 GBK 解码子进程 UTF-8 输出会崩读线程）。
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

TIMEOUT = 60  # analytics 走 Playwright 的端点约 20s，留足余量

# (名称, 路径模板, 是否对比 JSON 结构)
STATIC_GETS: list[tuple[str, str, bool]] = [
    ("页面", "/", False),
    ("单页", "/onepage", False),
    # 不存在的静态/构建资源必须两边同为 404（曾因 HTTPException 未导入 404→500，
    # 且不在常规覆盖面内——verify 轮独立验收发现的证据盲区，补此处防回归）
    ("静态资源-不存在", "/static/__no_such__.js", False),
    ("构建资源-不存在", "/assets/__no_such__.js", False),
    ("状态", "/api/status", False),  # 运行时不同（deepagents vs openclaw），仅比状态码
    ("画像列表", "/api/personas", True),
    ("技能列表", "/api/skills", False),  # 数量差异为有意裁剪（仅移植 wechat-publisher），只比状态码
    ("环境工具", "/api/env/tools", True),
    ("产物列表", "/api/outputs", True),
    ("账号列表", "/api/accounts", True),
    ("分析平台", "/api/analytics/platforms", True),
    ("趋势", "/api/trends", True),
    ("排期", "/api/schedule", True),
    ("选题", "/api/ideas", True),
    ("上传限制", "/api/upload/limits", True),
    ("模型设置", "/api/settings/models", True),
    ("会话回放-不存在", "/api/chat/last/__no_such_session__", False),
]


def get(base: str, path: str) -> tuple[int, object]:
    """GET 一个端点，返回 (状态码, 解析后的 JSON 或 None)。"""
    req = urllib.request.Request(base + path, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            body = resp.read()
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:  # noqa: BLE001 - 对比脚本需要兜底所有连接错误
        return -1, f"{type(e).__name__}: {e}"
    try:
        return 200, json.loads(body.decode("utf-8", "replace"))
    except Exception:  # noqa: BLE001 - HTML 等非 JSON 响应
        return 200, None


def post(base: str, path: str, payload: dict) -> tuple[int, object]:
    """POST 一个 JSON 端点（仅用于无副作用的查询类接口），返回 (状态码, JSON 或 None)。"""
    req = urllib.request.Request(
        base + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            body = resp.read()
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:  # noqa: BLE001
        return -1, f"{type(e).__name__}: {e}"
    try:
        return 200, json.loads(body.decode("utf-8", "replace"))
    except Exception:  # noqa: BLE001
        return 200, None


def shape(data: object) -> str:
    """响应的结构指纹：dict 比键集合，list 比长度，其余比类型。"""
    if isinstance(data, dict):
        return "keys:" + ",".join(sorted(data.keys()))
    if isinstance(data, list):
        return f"list[{len(data)}]"
    return type(data).__name__


def put(base: str, path: str, payload: dict) -> tuple[int, object]:
    """PUT 一个 JSON 端点，返回 (状态码, JSON 或 None)。"""
    req = urllib.request.Request(
        base + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="PUT",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            body = resp.read()
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:  # noqa: BLE001
        return -1, f"{type(e).__name__}: {e}"
    try:
        return 200, json.loads(body.decode("utf-8", "replace"))
    except Exception:  # noqa: BLE001
        return 200, None


def delete(base: str, path: str) -> int:
    req = urllib.request.Request(base + path, method="DELETE")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:  # noqa: BLE001
        return -1


def write_checks(args: argparse.Namespace, failures: list[str]) -> None:
    """写路径对比：schedule/ideas 增→改→删（两边各自创建、删除，不留测试数据）。

    另验对话契约：非流式 /api/chat 两边都应 200 且含 response 字段——
    内容允许不同（zimeiti 走 deepagents、easel 走 openclaw，且无密钥时应 graceful 降级）。
    """
    print("\n== 写路径对比（创建后删除，不留测试数据）==")
    for side, base in (("zimeiti", args.zimeiti), ("easel", args.easel)):
        sc, item = post(base, "/api/schedule",
                        {"title": "e2e-parity-test", "date": "2026-10-14", "note": "e2e"})
        sid = item.get("id") if isinstance(item, dict) else None
        pc = put(base, f"/api/schedule/{sid}", {"title": "e2e-parity-test-2", "date": "2026-10-15"})[0] if sid else -1
        dc = delete(base, f"/api/schedule/{sid}") if sid else -1
        print(f"  [{side}] schedule 增={sc} 改={pc} 删={dc}")
        if not (sc == 200 and pc == 200 and dc == 200):
            failures.append(f"[{side}] schedule CRUD 未全部 200：{sc}/{pc}/{dc}")

        sc, item = post(base, "/api/ideas", {"title": "e2e-parity-test", "note": "e2e"})
        iid = item.get("id") if isinstance(item, dict) else None
        pc = put(base, f"/api/ideas/{iid}", {"title": "e2e-parity-test-2"})[0] if iid else -1
        dc = delete(base, f"/api/ideas/{iid}") if iid else -1
        print(f"  [{side}] ideas    增={sc} 改={pc} 删={dc}")
        if not (sc == 200 and pc == 200 and dc == 200):
            failures.append(f"[{side}] ideas CRUD 未全部 200：{sc}/{pc}/{dc}")

    print("  chat 契约对比（非流式；内容允许不同，仅验 200 + response 字段）……")
    for side, base in (("zimeiti", args.zimeiti), ("easel", args.easel)):
        req = urllib.request.Request(
            base + "/api/chat",
            data=json.dumps({"message": "ping", "sessionId": "e2e-parity"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                body = json.loads(resp.read().decode("utf-8", "replace"))
                ok = resp.status == 200 and isinstance(body, dict) and "response" in body
                preview = ascii(str(body.get("response", ""))[:60]) if isinstance(body, dict) else ""
                print(f"  [{side}] chat -> {resp.status} response字段={'有' if ok else '无'} 预览: {preview!r}")
                if not ok:
                    failures.append(f"[{side}] /api/chat 契约不符：status={resp.status} body={str(body)[:80]}")
        except Exception as e:  # noqa: BLE001
            print(f"  [{side}] chat -> 异常 {type(e).__name__}: {e}")
            failures.append(f"[{side}] /api/chat 异常：{type(e).__name__}: {e}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zimeiti", default="http://127.0.0.1:8000")
    ap.add_argument("--easel", default="http://127.0.0.1:7860")
    ap.add_argument("--writes", action="store_true",
                    help="附带写路径对比（schedule/ideas 增改删 + chat 对话契约；会创建并删除测试数据）")
    args = ap.parse_args()

    failures: list[str] = []
    rows: list[tuple[str, str, int, int, str, str, str]] = []

    def compare(label: str, path: str, structural: bool = True) -> None:
        zc, zd = get(args.zimeiti, path)
        ec, ed = get(args.easel, path)
        if zc != ec:
            verdict = "状态码不一致"
            failures.append(f"{label} {path}: zimeiti={zc} easel={ec}")
        elif structural and shape(zd) != shape(ed):
            verdict = "结构不一致"
            failures.append(f"{label} {path}: zimeiti={shape(zd)} easel={shape(ed)}")
        else:
            verdict = "OK"
        rows.append((label, path, zc, ec, shape(zd), shape(ed), verdict))

    for label, path, structural in STATIC_GETS:
        compare(label, path, structural)

    # ---- 动态子资源：用同一标识符分别请求两边 ----
    code, data = get(args.zimeiti, "/api/personas")
    personas = [p.get("name") for p in data if isinstance(p, dict)] if isinstance(data, list) else []
    for name in personas[:3]:
        compare(f"画像详情[{name}]", f"/api/persona/{name}")
        compare(f"画像文件[{name}]", f"/api/persona/{name}/files")

    # ---- 技能详情：只对比交集（数量差异为有意裁剪，不算失败） ----
    _, z_skills = get(args.zimeiti, "/api/skills")
    _, e_skills = get(args.easel, "/api/skills")
    z_names = [s.get("name") for s in z_skills if isinstance(s, dict)] if isinstance(z_skills, list) else []
    e_names = [s.get("name") for s in e_skills if isinstance(s, dict)] if isinstance(e_skills, list) else []
    common = [n for n in z_names if n in e_names]
    for name in common[:5]:
        compare(f"技能详情[{name}]", f"/api/skill/{name}")
    for name in z_names[:3]:
        compare(f"技能自检[{name}]", f"/api/skill/{name}", structural=False)
    print(f"（技能数量：zimeiti={len(z_names)} easel={len(e_names)}，交集={len(common)}——"
          f"数量差异为有意裁剪：zimeiti 仅移植 skill-wechat-publisher，见 remove-openclaw 变更范围）")

    code, data = get(args.zimeiti, "/api/analytics/platforms")
    platforms = data if isinstance(data, list) else []
    for p in platforms:
        key = p.get("platform") if isinstance(p, dict) else p
        if isinstance(key, str):
            compare(f"分析[{key}]", f"/api/analytics/{key}", structural=False)

    # 登录/发布状态、凭证：均为只读查询，不起浏览器、不写文件
    for pf in ("xiaohongshu", "kuaishou", "weixin-channels", "zhihu", "bilibili", "douyin", "wechat-oa"):
        compare(f"登录状态[{pf}]", f"/api/login/{pf}/status", structural=False)
        compare(f"发布状态[{pf}]", f"/api/publish/{pf}/status", structural=False)
        compare(f"凭证[{pf}]", f"/api/accounts/{pf}/credentials")
    # wechat-oa 的 whoami 不走浏览器（按 mp 会话/AppID 配置判断），安全
    compare("whoami[wechat-oa]", "/api/accounts/wechat-oa/whoami")

    # 不存在的资源：两边应一致地返回 404/错误态
    compare("任务-不存在", "/api/env/job/__no_such_job__", structural=False)
    compare("画像构建-不存在", "/api/profile/build/status/__no_such__", structural=False)

    # 无副作用 POST：批量查 question 状态（空列表）
    zc, _ = post(args.zimeiti, "/api/chat/question/status", {"questionIds": []})
    ec, _ = post(args.easel, "/api/chat/question/status", {"questionIds": []})
    if zc != ec:
        failures.append(f"question状态: zimeiti={zc} easel={ec}")
        verdict = "状态码不一致"
    else:
        verdict = "OK"
    rows.append(("question状态", "POST /api/chat/question/status", zc, ec, "", "", verdict))

    code, data = get(args.zimeiti, "/api/outputs")
    outs = [o.get("path") for o in data if isinstance(o, dict)] if isinstance(data, list) else []
    for p in outs[:2]:
        if p:
            compare(f"产物内容[{p[:24]}]", f"/api/output/{p}")

    code, data = get(args.zimeiti, "/api/schedule")
    sched = data if isinstance(data, list) else []
    if sched:
        sid = sched[0].get("id")
        if sid:
            compare(f"排期上下文[{sid}]", "/api/schedule/context")

    if args.writes:
        write_checks(args, failures)

    # ---- 输出 ----
    width = max(len(r[0]) for r in rows) + 2
    print(f"{'端点':<{width}}{'路径':<44}{'zimeiti':>8}{'easel':>8}  结论")
    print("-" * (width + 70))
    for label, path, zc, ec, zs, es, verdict in rows:
        print(f"{label:<{width}}{path:<44}{zc:>8}{ec:>8}  {verdict}")

    print()
    if failures:
        print(f"不一致 {len(failures)} 项：")
        for f in failures:
            print("  -", f)
        return 1
    print(f"全部一致（{len(rows)} 项）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
