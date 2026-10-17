"""zimeiti_autonomous：自主运营闭环（autonomous-flow）。

第三包，与 zimeiti_harness（agent 运行时）/ zimeiti_api（业务与接口）并列：

- harness 不知道业务的存在（contract 注入）
- api 承载页面、路由与领域逻辑
- autonomous 承载「无人值守把运营链路跑完」的编排层

纪律：本包不 import harness 的 agent 入口——入口由组装层注入（set_agent_entry），
对齐 personas / scheduler 既有范式（tests/test_autonomous_flow.py 机械守卫）。
"""

from __future__ import annotations
