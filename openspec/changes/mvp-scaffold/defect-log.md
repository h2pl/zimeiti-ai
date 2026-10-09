# 缺陷记录（Defect Log）——变更 mvp-scaffold

## DEF-001 真模型 resume 400（线程状态污染）
- 严重度：High ｜ 状态：已关闭
- 现象：DeepSeek resume 返回 400（tool_calls 后缺 ToolMessage）
- 根因：thread_id 跨测试运行复用，checkpoint 残留损坏消息历史
- 修复：run_hosted_cycle 自动生成唯一 thread_id；诊断脚本 scripts/debug_resume.py
- 证据：干净 thread 下 INTERRUPTED→RESUME OK→发布执行（scripts/debug_resume.py 输出）

## DEF-002 psycopg ProactorEventLoop 不兼容
- 严重度：Medium ｜ 状态：已关闭
- 现象：Windows async 模式 psycopg 报 InterfaceError
- 修复：conftest import 阶段全局设置 WindowsSelectorEventLoopPolicy

## DEF-003 uv 受管 Python 目录损坏（os error 448）
- 严重度：Medium ｜ 状态：已关闭（绕行）
- 现象：uv 无法查询/创建受管解释器（不受信装入点）
- 绕行：.python-version 指向系统 pythoncore 3.14.8；CI/生产仍以 3.12 为目标

## DEF-004 ASGI 模块路径错误
- 严重度：Medium ｜ 状态：已关闭
- 现象：`uvicorn app.main:app` ModuleNotFoundError / Attribute "app" not found
- 根因：src 布局下包名是 zimeiti_api，且 app.py 缺模块级 app 实例
- 修复：`zimeiti_api.app:app` + 模块级 app = create_app()（三处同步修正）

## DEF-005 langchain v1 fake 模型缺 bind_tools
- 严重度：Low ｜ 状态：已关闭
- 现象：create_agent 调用 bind_tools 抛 NotImplementedError
- 修复：测试 fake 模型子类恒等实现 bind_tools

## DEF-006 ChatOpenAI/ChatDeepSeek api_key 类型
- 严重度：Low ｜ 状态：已关闭
- 修复：pydantic SecretStr 包装
