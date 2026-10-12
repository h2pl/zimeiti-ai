# web-workbench 能力增量（feat-skill-runner）

## MODIFIED Requirements

### Requirement: 运维操作页

运维操作页以技能卡片展示可手动运行的能力（名称/描述/参数表单/运行按钮）；
触发携带参数（账号 + 选题方向）写入标记文件，由常驻网关下一循环消费执行。

#### Scenario: 带参数触发托管循环
- **When** 用户在技能卡片填写账号与选题方向并运行
- **Then** 标记文件携带 params，网关消费时该轮托管循环使用指定账号与方向

#### Scenario: 参数白名单
- **When** trigger 提交未知 param 键或非法 account
- **Then** 返回 400，不写标记
