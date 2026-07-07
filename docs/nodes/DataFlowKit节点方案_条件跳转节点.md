# 节点方案：ConditionalJumpNode

更新时间：2026-07-05

## 基本信息

DataFlowKit 来源：`core.conditional_jump` / 条件跳转节点

FlowWeaver 暂定类型名：`ConditionalJumpNode`

节点方向：流程控制 / 条件路径跳转

优先级：P4

当前状态：后端预览版已实现。已进入默认注册表，读取条件状态表并输出统一控制状态表；不改变 DAG 执行路径。

## 要解决的问题

第一版根据条件状态表选择目标锚点或目标节点，生成条件跳转计划。

用户看到的能力：读取 `ConditionFlagNode` 的结果表，为 true/false 分支配置目标锚点或目标节点，并产出可预览的跳转计划。

不解决的内容：第一版不执行真实跳转，不修改 ready 队列，不跳过未选分支节点，不计算复杂路由表达式。

## 输入输出

输入：一个条件状态 `TableRef`，通常来自 `ConditionFlagNode` 的 `status` 输出。

输出：一个 `status` 控制状态表。

## 配置项草案

| 字段 | 含义 |
|---|---|
| `condition_field` | 条件结果字段，默认 `result` |
| `true_target_mode` | true 分支目标类型，`anchor` 或 `node` |
| `true_target_anchor` | true 分支目标锚点 |
| `true_target_node_id` | true 分支目标节点 |
| `false_target_mode` | false 分支目标类型，`anchor` 或 `node` |
| `false_target_anchor` | false 分支目标锚点 |
| `false_target_node_id` | false 分支目标节点 |
| `default_branch` | 条件值缺失或无法解析时使用的分支，默认 `false` |

## 数据契约

节点读取标准条件结果表，而不是依赖不可见的进程内状态。

状态表字段遵循 `FlowWeaver_控制信号协议与预览控制节点实施计划.md`：

```text
signal_type=conditional_jump
signal_status=matched / not_matched
condition_result=true / false / 空
selected_branch=true / false
target_anchor=<selected_target_anchor>
target_node_id=<selected_target_node_id>
actual_control=false
```

第一版只校验被选分支目标是否填写，不校验目标是否真实存在。

## 执行模式

普通运行：读取条件状态表并生成条件跳转计划。

预览运行：展示选中分支、目标和 `actual_control=false`。

支持取消：低优先级。

支持进度：不需要。

## 副作用与确认

副作用与外部资源说明：第一版不改变执行路径，无外部写入。

是否需要用户确认：后置讨论；如果可能跳过高风险确认节点，需要额外路径校验。

## 主程序交互边界

不应让 `WorkflowRunProcess` 为条件跳转增加节点专用分支。

应先设计通用条件边或动态调度协议。

## 运行记录

结果表包含条件字段、解析结果、命中分支、目标锚点或目标节点，以及 `actual_control=false`。

RuntimeEvent 必须记录条件跳转动作。

## 验收方式

后端能注册 `ConditionalJumpNode`。

读取 `ConditionFlagNode result=true` 时选择 true 分支。

读取 `ConditionFlagNode result=false` 时选择 false 分支。

条件字段缺失时返回验证错误。

被选分支目标为空时返回验证错误。

## 实现前置依赖

需要 `ConditionFlagNode` 或其他同协议条件结果表。

真实调度仍需要锚点和控制流调度模型。

## 简要模板补齐

节点名称：条件跳转节点。

节点定位：流程控制 / 条件路径跳转。

优先级：P4。

当前状态：后端预览版已实现，真实调度语义后置。

要解决的问题：见上文“要解决的问题”章节。

用户看到的能力：见上文“用户看到的能力”描述。

第一版不解决的内容：见上文“不解决的内容”描述。

注册参数：
- node_type：ConditionalJumpNode
- node_version：1.0
- plugin_id：core
- provider_type：builtin
- category：流程控制
- ui_visibility：visible
- enabled：后端预览版已可注册使用；真实跳转仍后置。
- display_name：条件跳转节点
- config_schema：沿用本文“配置项草案”，后续落到统一 config_schema。
- input_ports：必填 `condition`。
- output_ports：`status`，输出统一控制状态表。
- implementation_ref：builtin.ConditionalJumpNode（暂定内部执行入口，后续实现时绑定真实实现；不对普通 UI 暴露）。

输入说明：见上文“输入输出”章节；第一版接收一个条件状态表。

输出说明：见上文“输入输出”章节；输出必须使用标准引用或标准运行摘要。

配置说明：见上文“配置项草案”；配置只描述节点自身能力，不绑定具体 UI 控件。

数据流转方式：只产出标准控制状态或条件结果；真实跳转必须由通用调度能力解释，不让主程序为单个跳转节点写专用分支。

是否支持取消：支持；通常为短耗时节点，执行前后检查取消即可。

是否支持进度上报：支持基础阶段进度，通常只需要开始、判断完成和结果摘要。

节点反馈：反馈条件求值、命中分支、目标锚点、跳过原因、失败和取消。

节点心跳：短耗时控制节点不强制主动心跳；复杂条件或等待调度时可刷新 NodeRun.last_heartbeat。

心跳查询方式：通过 NodeRun.last_heartbeat、status、progress、current_stage、error 和 RuntimeEvent 查询节点活动状态。

后台极简模式：后台极简模式保留开始、判断结果、目标锚点、失败和取消，不记录高频细节。

外部资源与副作用：沿用本文“副作用与确认”章节；权限、审计、字段级追踪不写入默认节点方案。

性能影响等级：低到中。

主要性能消耗点：条件求值、锚点解析和调度状态记录。

失败场景：条件配置不完整、目标锚点不存在、表达式非法、流程图形成不可执行路径。

失败提示：提示缺失的条件字段、目标锚点、非法表达式和当前可用锚点列表。

验收方式：沿用本文“验收方式”章节，并补充校验运行记录、取消、进度、心跳和后台极简模式是否符合本节约束。
## 后续扩展
支持多条件路由。

支持画布路径可视化。
