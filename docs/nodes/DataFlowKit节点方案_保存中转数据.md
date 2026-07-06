# 节点方案：SaveRunTableNode

更新时间：2026-07-05

## 基本信息

DataFlowKit 来源：`core.save_transit` / 保存中转数据

FlowWeaver 暂定类型名：`SaveRunTableNode` / `LabelTableOutputNode`

节点方向：输出 / 运行内命名输出

优先级：P2/P3

当前状态：规划中，代码未实现

## 要解决的问题

把当前输入表保存为运行内可识别的命名输出，必要时再扩展到 SQLite 或 xlsx 导出。

用户看到的能力：给当前表起一个运行内名称，供后续节点、运行摘要或共享发布使用。

不解决的内容：第一版不直接照搬 DataFlowKit 的全局 `transit_tables` 字典，不默认写 SQLite 或 xlsx。

## 输入输出

输入：一个 `TableRef`。

输出：默认透传输入 `TableRef`，并产生命名运行输出记录。

外部导出模式可后置拆为 `ExportRunTableNode`。

## 配置项草案

| 字段 | 含义 |
|---|---|
| `transit_name` | 运行内名称 |
| `save_memory` | 是否保存为运行内命名输出 |
| `save_sqlite` | 是否写 SQLite，后置 |
| `sqlite_table` / `sqlite_mode` | SQLite 目标和模式 |
| `save_xlsx` / `xlsx_path` | 是否导出 xlsx 和路径 |
| `stop_after_save` | 保存后是否停止，后置讨论 |

## 数据契约

第一版建议只规划运行内命名输出，不创建新的全局中转表机制。

命名输出应与 `TableRef`、`NodeRun` 和运行摘要关联。

## 执行模式

支持普通运行和预览运行。

运行内命名输出可在预览中产生；外部 SQLite/xlsx 写入只能在正式确认后执行。

支持取消：低优先级。

支持进度：低优先级。

## 副作用与确认

副作用与外部资源说明：写运行数据；若启用 SQLite/xlsx 则写外部资源。

是否需要用户确认：运行内命名输出不需要；外部导出必须确认。

## 主程序交互边界

节点不直接操作 `RuntimeStore` 内部结构。

如果需要命名运行输出，应通过通用 `NodeRuntimeContext` 能力发布。

不要求 `WorkflowRunProcess` 为中转表增加节点专用逻辑。

## 运行记录

结果摘要建议包含命名输出名称、输入表引用、是否外部导出、导出路径。

外部写入被跳过时应明确记录原因。

## 验收方式

运行内命名输出可在 run 结果中查询到。

预览模式不写外部文件。

命名冲突按配置处理。

## 实现前置依赖

需要确定 FlowWeaver 运行内命名输出模型。

外部导出需要用户确认机制。

## 简要模板补齐

节点名称：保存中转数据。

节点定位：输出 / 运行内命名输出。

优先级：P2/P3。

当前状态：规划中，代码未实现。

要解决的问题：见上文“要解决的问题”章节。

用户看到的能力：见上文“用户看到的能力”描述。

第一版不解决的内容：见上文“不解决的内容”描述。

注册参数：
- node_type：SaveRunTableNode
- node_version：1.0
- plugin_id：core
- provider_type：builtin
- category：输出
- ui_visibility：visible
- enabled：规划期为 false；实现和验收后再按节点成熟度设为 true。
- display_name：保存中转数据
- config_schema：沿用本文“配置项草案”，后续落到统一 config_schema。
- input_ports：一个标准 TableRef 输入。
- output_ports：默认透传 TableRef，并产生命名运行输出或外部导出状态。
- implementation_ref：builtin.SaveRunTableNode（暂定内部执行入口，后续实现时绑定真实实现；不对普通 UI 暴露）。

输入说明：见上文“输入输出”章节；第一版按 input_ports 约束接收数据。

输出说明：见上文“输入输出”章节；输出必须使用标准引用或标准运行摘要。

配置说明：见上文“配置项草案”；配置只描述节点自身能力，不绑定具体 UI 控件。

数据流转方式：通过标准输入读取 TableRef，通过运行上下文发布命名输出；不直接操作 RuntimeStore 内部结构。外部导出后置到确认链路。

是否支持取消：支持；运行内命名输出通常很快，外部导出时按批次检查取消。

是否支持进度上报：支持低频进度，至少区分命名输出、外部导出和完成阶段。

节点反馈：反馈命名输出名称、输入表引用、是否外部导出、导出路径、跳过原因和失败原因。

节点心跳：运行内保存可只依赖开始和结束；外部 SQLite/xlsx 导出时保留低频心跳。

心跳查询方式：通过 NodeRun.last_heartbeat、status、progress、current_stage、error 和 RuntimeEvent 查询节点活动状态。

后台极简模式：后台极简模式只保留命名输出摘要、外部导出摘要、失败原因和低频心跳。

外部资源与副作用：沿用本文“副作用与确认”章节；权限、审计、字段级追踪不写入默认节点方案。

性能影响等级：中。

主要性能消耗点：运行输出登记、可选外部序列化和文件写入。

失败场景：命名冲突、输入表不可读、外部导出路径不可写或导出格式失败。

失败提示：提示命名冲突处理方式、导出路径、跳过原因和失败配置项。

验收方式：沿用本文“验收方式”章节，并补充校验运行记录、取消、进度、心跳和后台极简模式是否符合本节约束。
## 后续扩展
拆分 `ExportRunTableNode`。

与 SharedPublication 发布节点联动。
