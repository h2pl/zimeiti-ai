"""静态路由不得被同前缀动态路由吞掉（cli-entry-point 抓出的真 bug）。

背景：`/api/flows/{flow_id}` 注册在 `/api/flows/runs` 与
`/api/flows/steps/catalog` **之前**——FastAPI 按注册顺序匹配，动态路由先命中，
静态路由永远 404「流程不存在」。Web 页面 `.catch(() => [])` 静默吞掉，
执行记录面板从未出现过；CLI 探针直连才暴露。

遍历方式沿用 test_app_routes.py（`_IncludedRouter.original_router.routes`）。
守卫有效性已验证：改回旧顺序本测试即红。
"""

from __future__ import annotations

from fastapi.routing import APIRoute, _IncludedRouter

from zimeiti_api import app as app_module

app = app_module.app


def _ordered_api_routes() -> list[tuple[str, frozenset[str]]]:
    """按注册顺序展开全部 API 路由（method, path）。"""
    out: list[tuple[str, frozenset[str]]] = []

    def walk(rs) -> None:
        for r in rs:
            if isinstance(r, _IncludedRouter):
                walk(r.original_router.routes)
            elif isinstance(r, APIRoute):
                for m in sorted(r.methods - {"HEAD", "OPTIONS"}):
                    out.append((m, r.path))

    walk(app.routes)
    return [x for x in out if x[1].startswith("/api/")]


def _matches(dynamic: str, static: str) -> bool:
    d, s = dynamic.strip("/").split("/"), static.strip("/").split("/")
    if len(d) != len(s):
        return False
    return all(a == b or a.startswith("{") for a, b in zip(d, s, strict=True))


def test_static_paths_not_shadowed_by_dynamic():
    routes = _ordered_api_routes()
    problems: list[str] = []
    for i, (m, path) in enumerate(routes):
        if "{" in path:
            continue
        for j in range(i):
            m2, dpath = routes[j]
            if "{" in dpath and m2 == m and _matches(dpath, path):
                problems.append(f"{m} {path} 被更早注册的 {m2} {dpath} 遮蔽（静态路由不可达）")
    assert not problems, "\n".join(sorted(set(problems)))
