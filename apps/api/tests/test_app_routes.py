"""app 路由表完整性测试：重复路由 / 方法冲突防回归。

背景：backend-restructure 拆包时 DELETE /api/output/{path} 在 outputs.py 与
uploads.py 各注册了一份（实现相同）——后注册者是永远不可达的死代码，且
恰好躲在测试盲区里（行为不受影响、静态审计按路径匹配判为已覆盖）。由
coverage 驱动的 handler 执行审计抓出。本测试保证路由表不再出现重复。
"""

from __future__ import annotations

from fastapi.routing import APIRoute, _IncludedRouter

from zimeiti_api import app


def _api_routes() -> list[APIRoute]:
    routes: list[APIRoute] = []

    def walk(rs):
        for r in rs:
            if isinstance(r, _IncludedRouter):
                walk(r.original_router.routes)
            elif isinstance(r, APIRoute):
                routes.append(r)

    walk(app.app.routes)
    return [r for r in routes if r.path.startswith("/api/")]


def test_no_duplicate_method_path():
    seen: dict[tuple[str, str], str] = {}
    dupes = []
    for r in _api_routes():
        for meth in r.methods - {"HEAD", "OPTIONS"}:
            key = (meth, r.path)
            if key in seen and seen[key] != r.endpoint.__code__.co_filename:
                dupes.append((meth, r.path, seen[key], r.endpoint.__code__.co_filename))
            seen.setdefault(key, r.endpoint.__code__.co_filename)
    assert not dupes, f"重复路由（后者不可达）: {dupes}"


def test_route_table_shape():
    routes = _api_routes()
    assert len(routes) >= 59  # 59 条 API 路由基准（曾因重复注册虚增为 60）
    # 全部路由都有 handler 且非空方法集
    assert all(r.endpoint is not None and r.methods for r in routes)
