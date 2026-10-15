"""场景协议与上下文。

场景 = `run(page, ctx, check) -> dict`：
- 只做真实用户操作（浏览器点击/输入），数据清理可走 API
- check(name, ok, detail) 记录场景内断言（进入总表）
- 返回 dict：结构级观测值（供双端 parity 比较）
"""

from __future__ import annotations

import json
import urllib.request


class Ctx:
    def __init__(self, base: str, target: str) -> None:
        self.base = base
        self.target = target

    def api(self, method: str, path: str, payload: dict | None = None, timeout: int = 15):
        """数据清理用的直连 API（非用户路径断言）。

        必须带同源 Origin——否则写请求被 local_write_guard 403（与浏览器
        同源请求等价：Origin=base 是本服务托管的页面）。
        """
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(
            f"{self.base}{path}", data=data, method=method,
            headers={"Content-Type": "application/json", "Origin": self.base},
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8", "replace")
            return json.loads(body) if body and body.lstrip()[:1] in "[{" else None
