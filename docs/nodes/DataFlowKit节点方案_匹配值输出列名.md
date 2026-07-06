# 节点方案：LookupMatchedFieldNameNode

更新时间：2026-07-05

## 基本信息

DataFlowKit 来源：`core.match_value_output` / 匹配值输出列名

FlowWeaver 暂定类型名：`LookupMatchedFieldNameNode`

节点方向：数据处理 / 查找匹配

优先级：P2

当前状态：规划中，代码未实现

## 要解决的问题

用当前表字段值去查找另一张表的多个字段，输出命中的字段名、命中值、行号和状态。

用户看到的能力：选择源字段和 lookup 表字段，运行后得到匹配结果字段。

不解决的内容：不写 lookup 表，不做复杂 join 输出，不替代高级筛选节点。

## 输入输出

输入：主 `TableRef` 和 lookup `TableRef`。

输出：一个新的 `TableRef`。

输出行数与主表相同，可新增匹配字段名、匹配值、匹配行号和状态字段。

## 配置项草案

| 字段 | 含义 |
|---|---|
| `source_field` | 主表来源字段 |
| `lookup_table` | lookup 表引用或名称 |
| `lookup_fields` | lookup 字段列表 |
| `match_mode` | 完全相等等匹配模式 |
| `output_field` | 输出字段名 |
| `output_match_value` / `match_value_field` | 是否输出命中值 |
| `output_match_row` / `match_row_field` | 是否输出命中行号 |
| `output_status` / `status_field` | 是否输出状态 |
| `multi_match_policy` | 多命中处理 |
| `no_match_value` | 未匹配值 |

## 数据契约

节点读取主表每行源值，在 lookup 表指定字段集合中查找命中。

多命中策略必须明确，避免输出不稳定。

## 执行模式

支持普通运行和预览运行。

支持取消：建议支持。

支持进度：建议支持，记录主表处理行数和命中数量。

## 副作用与确认

副作用与外部资源说明：读取额外 `TableRef`，无外部写入。

是否需要用户确认：不需要；若 lookup 表来自外部只读资源，按来源节点处理确认。

## 主程序交互边界

节点不通过主程序全局表名查找业务表，必须通过标准输入引用或运行上下文引用。

不依赖 DataFlowKit 的多表 UI 服务。

## 运行记录

结果摘要建议包含 lookup 字段数、主表行数、命中行数、未命中行数、多命中行数。

失败提示应指出缺失字段或 lookup 输入不存在。

## 验收方式

单字段和多字段 lookup 均可输出命中字段名。

未匹配按配置输出。

多命中策略稳定。

## 实现前置依赖

需要多输入 `TableRef` 或 lookup 表引用机制。

需要字段多选配置。

## 简要模板补齐

节点名称：匹配值输出列名。

节点定位：数据处理 / 查找匹配。

优先级：P2。

当前状态：规划中，代码未实现。

要解决的问题：见上文“要解决的问题”章节。

用户看到的能力：见上文“用户看到的能力”描述。

第一版不解决的内容：见上文“不解决的内容”描述。

注册参数：
- node_type：LookupMatchedFieldNameNode
- node_version：1.0
- plugin_id：core
- provider_type：builtin
- category：数据处理
- ui_visibility：visible
- enabled：规划期为 false；实现和验收后再按节点成熟度设为 true。
- display_name：匹配值输出列名
- config_schema：沿用本文“配置项草案”，后续落到统一 config_schema。
- input_ports：一个标准 TableRef 输入。
- output_ports：一个新的标准 TableRef 输出。
- implementation_ref：builtin.LookupMatchedFieldNameNode（暂定内部执行入口，后续实现时绑定真实实现；不对普通 UI 暴露）。

输入说明：见上文“输入输出”章节；第一版按 input_ports 约束接收数据。

输出说明：见上文“输入输出”章节；输出必须使用标准引用或标准运行摘要。

配置说明：见上文“配置项草案”；配置只描述节点自身能力，不绑定具体 UI 控件。

数据流转方式：通过标准输入引用读取 TableRef，通过标准输出引用交付新的 TableRef。节点不直接读写主程序内部 Store，也不让主程序理解节点业务规则。

是否支持取消：支持；短耗时场景可在批处理边界检查取消，大表处理时按行或分批检查。

是否支持进度上报：支持低频进度上报，至少记录当前阶段、已处理数量和结果数量。

节点反馈：通过 NodeRun、RuntimeEvent 和结果摘要反馈开始、运行中、完成、失败、取消；摘要包含输入数量、输出数量、跳过数量和错误数量。

节点心跳：短耗时数据处理不强制主动心跳；处理大表或分批执行时按批次刷新 NodeRun.last_heartbeat。

心跳查询方式：通过 NodeRun.last_heartbeat、status、progress、current_stage、error 和 RuntimeEvent 查询节点活动状态。

后台极简模式：保留开始、结束、失败、取消和最终结果摘要；关闭逐行日志和高频 UI 刷新，大表场景保留低频进度和心跳。

外部资源与副作用：沿用本文“副作用与确认”章节；权限、审计、字段级追踪不写入默认节点方案。

性能影响等级：中。

主要性能消耗点：按行或按列扫描、复制或生成 TableRef。

失败场景：输入表不可读、字段不存在、配置不完整、数据类型不符合预期。

失败提示：提示缺失字段、非法配置项或失败阶段，并给出可修正的字段名、配置名和样例值。

验收方式：沿用本文“验收方式”章节，并补充校验运行记录、取消、进度、心跳和后台极简模式是否符合本节约束。
## 后续扩展
支持大小写、包含、正则等匹配模式。

支持输出全部命中详情为子表 DataRef。
