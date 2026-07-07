# 节点方案：LoopJudgeNode

更新时间：2026-07-05

## 基本信息

DataFlowKit 来源：`core.loop_judge` / 循环判断回跳

FlowWeaver 暂定类型名：`LoopJudgeNode`

节点方向：流程控制 / 循环

优先级：P4

当前状态：后端预览版已实现。已进入默认注册表，读取输入表并输出统一控制状态表；不改变 DAG 执行路径，不执行真实回跳。

## 要解决的问题

第一版根据输入表生成循环判断计划，记录继续循环或结束循环的预览动作。

用户看到的能力：配置循环 ID、判断条件、成功/失败策略和结果表名，并产出可预览的循环判断状态。

不解决的内容：不在当前 DAG 上硬插回跳逻辑，不负责执行循环体内节点，不更新真实循环队列。

## 输入输出

输入：一个当前循环体输出 `TableRef`。

输出：一个 `status` 控制状态表。

## 配置项草案

| 字段 | 含义 |
|---|---|
| `loop_id` | 绑定循环起点 |
| `condition_source` | 条件来源 |
| `condition_mode` | 始终成功、按字段判断等 |
| `condition_field` / `condition_op` / `condition_value` | 条件表达式 |
| `condition_value_source` | 条件值来源，固定值、当前循环项字段、当前结果表字段、指定单元格、表达式 |
| `condition_value_field` | 条件值来自字段时的来源字段 |
| `on_success` | 成功时队列标记策略 |
| `on_fail` | 失败时队列标记策略 |
| `end_output_mode` | 结束输出模式 |
| `result_table_name` | 结果表名 |

## 动态值来源补充

循环判断经常需要用“当前循环项”或“当前结果表”的字段作为比较值。

实际使用中可能需要：

```text
当前结果表字段 A 等于当前循环项字段 B 时，标记完成。
当前结果表字段 A 包含当前循环项字段 B 时，继续下一条。
当前结果表行数大于当前循环项字段 C 指定的数量时，判定成功。
```

建议第一版值来源至少支持：

```text
固定值：condition_value 来自配置。
当前循环项字段：从 loop state 当前项读取。
当前结果表字段：从本节点输入 TableRef 读取。
指定单元格：从指定行字段读取。
```

表达式值可后置，用于组合当前循环项和结果表字段。

## 数据契约

第一版不读取或更新真实循环状态，只读取输入表并输出统一控制状态表。

```text
signal_type=loop_decision
signal_status=matched / not_matched
condition_result=true / false
selected_branch=continue_loop / end_loop
action=continue_loop_preview / end_loop_preview
actual_control=false
```

## 执行模式

普通运行：生成循环判断状态表。

预览运行：只记录判断结果和计划动作，不执行回跳。

支持取消：必须支持。

支持进度：必须支持。

## 副作用与确认

副作用与外部资源说明：第一版不改变运行结构，只输出状态表。

是否需要用户确认：后置讨论。

## 主程序交互边界

节点不应直接操作调度器 program counter。

应通过通用循环运行模型表达“继续下一轮”或“循环结束”。

## 运行记录

结果表包含循环 ID、判断结果、成功/失败策略、选中动作和 `actual_control=false`。

RuntimeEvent 需要记录每轮判断结果。

## 验收方式

后端能注册 `LoopJudgeNode`。

支持 `always_success`、`row_count`、`field_value` 三类预览判断。

成功和失败策略能映射为 `continue_loop_preview` 或 `end_loop_preview`。

条件字段缺失时返回验证错误。

## 实现前置依赖

需要标准输入表。

真实回跳仍需要动态调度或循环节点协议。

## 简要模板补齐

节点名称：循环判断回跳。

节点定位：流程控制 / 循环。

优先级：P4。

当前状态：后端预览版已实现，真实循环语义后置。

要解决的问题：见上文“要解决的问题”章节。

用户看到的能力：见上文“用户看到的能力”描述。

第一版不解决的内容：见上文“不解决的内容”描述。

注册参数：
- node_type：LoopJudgeNode
- node_version：1.0
- plugin_id：core
- provider_type：builtin
- category：流程控制
- ui_visibility：visible
- enabled：后端预览版已可注册使用；真实回跳仍后置。
- display_name：循环判断回跳
- config_schema：沿用本文“配置项草案”，后续落到统一 config_schema。
- input_ports：必填 `in`。
- output_ports：`status`，输出统一控制状态表。
- implementation_ref：builtin.LoopJudgeNode（暂定内部执行入口，后续实现时绑定真实实现；不对普通 UI 暴露）。

输入说明：见上文“输入输出”章节；第一版接收一个输入表用于预览判断。

输出说明：见上文“输入输出”章节；输出必须使用标准引用或标准运行摘要。

配置说明：见上文“配置项草案”；配置只描述节点自身能力，不绑定具体 UI 控件。

数据流转方式：只输出标准控制状态表；不在 WorkflowRunProcess 中增加节点专用回跳分支，真实循环需接入通用循环或动态调度能力。

是否支持取消：必须支持；每轮或每批次检查取消，并保证循环状态可解释。

是否支持进度上报：必须支持，记录当前轮次、总轮次、当前项和中止原因。

节点反馈：反馈循环初始化、每轮进度、子工作流阶段、完成、失败、取消和是否达到上限。

节点心跳：必须保留低频心跳，每轮或每批次刷新 NodeRun.last_heartbeat。

心跳查询方式：通过 NodeRun.last_heartbeat、status、progress、current_stage、error 和 RuntimeEvent 查询节点活动状态。

后台极简模式：后台极简模式保留循环开始、每批次低频进度、结束、失败、取消、心跳和最终摘要，避免记录每个子节点的重复细节。

外部资源与副作用：沿用本文“副作用与确认”章节；权限、审计、字段级追踪不写入默认节点方案。

性能影响等级：高。

主要性能消耗点：循环状态维护、重复调度、子工作流执行、结果合并和恢复状态记录。

失败场景：循环边界配置错误、最大次数超限、循环状态不可恢复、子工作流失败或取消后状态不一致。

失败提示：提示 loop_id、当前轮次、失败子节点、最大次数、恢复状态和建议缩小循环范围。

验收方式：沿用本文“验收方式”章节，并补充校验运行记录、取消、进度、心跳和后台极简模式是否符合本节约束。
## 后续扩展
支持失败重试。

支持循环结果汇总输出。

支持表达式条件值来源。
