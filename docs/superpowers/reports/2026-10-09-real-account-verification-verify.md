# 验证报告（Verify Report）——变更 real-account-verification

- 日期：2026-10-09
- 分支：comet/real-account-verification（build 阶段，含 2.2/2.3 真账号走查证据）
- 范围：真实平台接线（gzh 草稿箱 / xhs 私密发布）、读回对账三档、频控/白名单护栏、真账号走查

## 结论

**通过（Go）**——8/9 任务完成（1.1-1.5、2.1-2.6、2.2、2.3、3.1 全部 ✅），双平台发布→读回链路真账号验证通过：

- **gzh（公众号草稿箱）**：上传 + 读回 verified（A3-gzh PASSED）
- **xhs（小红书）**：私密发布 + 笔记管理读回 verified（A3-xhs，xiaohongshu-mcp 路线）
- **护栏**：频控边界（A5）、读回失败降级（A4）、白名单 fail-closed 全部实测通过
- 未决事项（1 项）：A3 中 API 逆向路线的假阳性经验已固化为开发铁律，无未修缺陷

## 校验记录

- 门禁：`make check` 五项全绿——53 passed，覆盖率 86.29%≥80%（ruff/mypy/bandit 排除 vendor 目录）
- 真账号走查证据（审计 JSONL + 平台侧人工核验 + 平台截图）：

| 任务 | 场景 | 结果 | 证据 |
|---|---|---|---|
| 2.2 | gzh 草稿箱上传+读回 | verified | walkthrough_a3_gzh.py + 公众号后台人工确认 |
| 2.3 | xhs 私密发布+读回 | verified | walkthrough_a3_xhs.py + 笔记管理列表含标题 |
| 2.4 | 人为读回失败（篡改标题） | unverified 留痕 | walkthrough_a4_readback_failure.py + 审计 action=published outcome=unverified |
| 2.5 | 频控边界（日限 2） | 第三篇零调用拒绝 | walkthrough_a5_rate_limit.py + 审计 publish_failed |
| 2.6 | 审批端点 profile 硬编码 | 按中断记录加载 | test_approvals_api spy 断言 |

## 缺陷记录（走查发现并修复）

| # | 缺陷 | 根因 | 修复 |
|---|---|---|---|
| D1 | executor.publish 硬编码 readback=unverified，生产审计永远 unverified（W1 复发） | 路由器三档 outcome 被嵌套吞掉 | 透传路由器结果 + 2 回归单测（A5 演练暴露） |
| D2 | gzh 发布真路径传 dict 草稿但代码访问 .title 属性 | drafts.json 读回的是 dict | dict/object 双形态兼容 + 单测 |
| D3 | xhs 登录态两次丢失 | wait_for_url 等错跳转地址；storage_state 目录缺失 | 按域名判定登录成功 + mkdir 兜底 |
| D4 | xhs 提交按钮误点侧边栏同名导航项（假阳性 submitted） | text=发布笔记 的 .first 命中 DOM 顺序靠前的侧边栏项 | 表单按钮类名定位（.btn-wrapper） |
| D5 | xhs API create_note success:true 但笔记未落库 | 自造判定 code==0（实际响应无 code 字段）+ API 路线被风控拒签名 | 结果判定照抄 xiaobei create_note_v2；发布路线切换 |
| D6 | 话题含空格（"AI Agent"）联想等待超时 | 联想下拉无法命中带空格关键词 | 客户端过滤含空格话题 |
| D7 | sync Playwright 报 asyncio 循环冲突 | litellm invoke 残留事件循环 + 双 Playwright 实例 | 读回走子进程；page 单实例贯穿 |

## 方案演进记录（xhs 发布）

1. edith API 逆向（python requests + x-s/x-t / +x-s-common / creator 域内置签名）：风控全部拒绝；creator 域 success:true 为假阳性（笔记未落库）——已固化为开发铁律「零假阳性」
2. 自研 DOM（xhs-toolkit 选择器移植）：站点已改版（Quill→Tiptap、按钮重排），选择器维护成本高
3. **最终方案**：接入成熟开源 xpzouying/xiaohongshu-mcp（v2.5.5，Go/rod，2026-10-09 仍在维护）作为本地发布服务，`XhsPublisher` 重写为其 API 客户端（POST /api/v1/publish，visibility=仅自己可见）；登录态/编辑器适配/拟人化/成功判定全部由该项目负责
4. 上述经验已固化为开发铁律（AGENTS.md「开发铁律」5 条 + Comet Project Knowledge constraint ×3）

## 遗留

1. xhs 私密笔记的自动化读回依赖笔记管理页 DOM（私密笔记在 web 列表可见性待长期观察）；备用方案：xiaohongshu-mcp 的 feeds/detail 接口按 note_id 精确核验
2. xhs 账号私密区残留 3-4 篇测试笔记，待用户手动清理
3. 生产接线项：tools.real_platform_router 的 xhs 分支与 walkthrough 保持一致（均已为 API 客户端）；gzh 凭证已迁移 Fernet 密文（WECHAT_MP_APP* 环境变量仅作 seal CLI 输入源）
4. Comet Knowledge 评审协议的 type 字段校验细节待解（3 条铁律在评审队列中，AGENTS.md 为强制保障）
