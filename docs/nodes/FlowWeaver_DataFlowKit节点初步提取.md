# FlowWeaver DataFlowKit 节点初步提取

更新时间：2026-07-05

## 文档定位

本文件用于从 `C:\Users\12650\桌面\工具\PythonProject\DataFlowKit` 初步提取可迁移到 FlowWeaver 的节点能力。

当前阶段只做节点规划与方案拆分，不修改 FlowWeaver 代码，也不要求 DataFlowKit 节点马上进入实现。

本次提取的重点是：

```text
提取节点能力。
提取输入、输出、配置和副作用事实。
判断与 FlowWeaver 当前主程序的耦合风险。
形成后续逐个撰写节点方案的优先级。
```

本次不做：

```text
不直接搬运 DataFlowKit 的执行代码。
不继承 DataFlowKit 的 table_access / audit 体系。
不把 DataFlowKit 的 window / Tkinter 运行依赖写入 FlowWeaver。
不要求 EngineHost 或 WorkflowRunProcess 为每个节点新增专用 if 分支。
不把外部写入节点视为第一批默认可后台执行节点。
```

## 提取来源

| 来源 | 用途 |
|---|---|
| `workflow/protocol_nodes.py` | 稳定 `node_type_id`、中文显示名、分类、headless 支持清单 |
| `docs/workflow_protocol.md` | 工作流 JSON 协议、预览/执行语义、插件与 runtime action 说明 |
| `workflow/default_configs.py` | 每个节点默认配置字段，适合提炼第一版配置面 |
| `workflow/node_ui_schema.py` | 节点摘要、风险标记、表单分组、字段选择器提示 |
| `workflow/node_dispatch.py` | 旧 UI 运行分派方式，用于识别不能继承的窗口耦合 |
| `engine/headless.py` | UI-free 运行支持、`execute_actions` 副作用开关、控制流状态处理 |
| `workflow/nodes/*` | 纯表格处理算法、输出节点和文件节点的实际行为参考 |

DataFlowKit 当前协议目录内置 33 个节点类型：

| 分类 | 数量 | 说明 |
|---|---:|---|
| 文件处理 | 2 | 读取文件列表、批量重命名 |
| 数据处理 | 20 | 列、行、文本、日期、填充、去重、筛选等表格处理 |
| 输出 | 3 | 中转保存、选定列写入、字段映射写回 |
| 流程控制 | 7 | 节点组、循环、跳转、条件判断 |
| 插件 | 1 | 兼容旧计划的 `core.plugin` 入口 |

其中 `protocol_nodes.py` 标记 32 个内置节点可走 headless 路径；`core.plugin` 本身是兼容入口，实际插件推荐使用 `plugin.<plugin_id>`。

## FlowWeaver 当前承接状态

### 已适合承接的基础

FlowWeaver 当前已经具备以下承接条件：

```text
NodeDefinitionSpec
node_type / node_version
input_ports / output_ports
config_schema
WorkflowRun / NodeRun
NodeTask / NodeTaskResult
input_refs / output_refs
TableRef
RuntimeEvent
DAG 调度
运行到选中节点 preview_to_node
节点取消、超时、进度、心跳主链路
```

这些能力足以先规划大部分纯表格节点。

### 正在变化的前提

当前迁移 `migrations/versions/20260705_0012_remove_permission_audit_runtime.py` 已经删除：

```text
node_tasks.permission_handle_id
permission_grants
audit_events
```

因此 DataFlowKit 节点方案不要再围绕权限句柄、权限授权、权限撤销、AuditEvent 写设计。

后续节点方案应改用：

```text
副作用与外部资源说明
是否需要用户确认
主程序交互边界
RuntimeEvent / NodeRun / NodeTaskResult 运行记录
```

### 仍需避免扩大的耦合

FlowWeaver 当前仍有一些开发期耦合需要在规划中规避：

```text
WorkflowRunProcess 的默认 executor owner 仍按内置表节点、共享表节点、普通 executor 分流。
BuiltinTableNodeRunner 内部仍按 GenerateTestTableNode / FilterRowsNode 做专用判断。
默认节点注册表仍集中列出内置节点。
Avalonia UI 已有部分内置节点编辑器与通用配置表单并存。
```

这些不是阻塞规划的问题，但说明 DataFlowKit 节点迁移不能继续扩大这种模式。

推荐方向：

```text
先规划通用 NodeRunner / NodeRuntimeContext。
节点通过注册表或节点包提供定义与执行入口。
WorkflowRunProcess 只提交 NodeTask，不理解节点业务。
UI 优先使用节点定义、config_schema 和通用表单。
专用编辑器只能作为增强，不能作为节点可运行前提。
```

## 迁移原则

### 1. 只提取能力，不继承主程序耦合

DataFlowKit 的旧运行分派存在 `window` 参数和窗口服务依赖，例如文件节点、筛选节点、输出节点、插件节点会从窗口对象读取服务。

FlowWeaver 方案中应写成：

```text
节点读取 NodeTask.config。
节点读取 input_refs。
节点通过 NodeRuntimeContext 读取 TableRef。
节点通过 NodeRuntimeContext 写入新的 TableRef / DataRef。
节点通过 NodeRuntimeContext 检查取消和上报进度。
节点返回 NodeTaskResult。
```

不应写成：

```text
节点调用 EngineHost。
节点调用 MainWindowViewModel。
节点直接访问 RuntimeStore 内部结构。
WorkflowRunProcess 针对该节点增加专用 if。
UI 必须提供某个专用窗口后节点才可执行。
```

### 2. `execute_actions` 只作为副作用设计参考

DataFlowKit 的 headless runtime 用 `execute_actions=false` 表示预览或 dry-run，高风险动作需要同时满足配置开关，例如：

```text
core.batch_rename: execute_actions=true 且 actual_rename=true 才真实重命名。
core.selected_columns_write: SQLite 写入需要 execute_actions=true 且 enable_write=true。
core.writeback: SQLite 更新需要 execute_actions=true 且 enable_write=true。
core.save_transit: 内存中转可写，SQLite / xlsx 需要 execute_actions=true。
外部插件数据库请求只有 execute_actions=true 才执行。
```

FlowWeaver 不需要照搬字段名，但可以吸收这个分层：

```text
预览运行：不产生外部写入。
正式运行：仍需节点配置允许。
高风险动作：必须有用户确认或运行来源明确允许。
节点结果：必须能说明实际执行了什么、跳过了什么。
```

### 3. 表格节点优先映射到 TableRef

DataFlowKit 的多数数据节点以 `headers, rows -> headers, rows` 形式工作。

FlowWeaver 中应统一写成：

```text
输入：一个 TableRef。
输出：一个新的 TableRef。
副作用：无外部副作用，只写本次运行输出。
```

即使节点语义是“删除行”“覆盖字段”“移动列”，第一版也不应原地修改输入 TableRef，而应产出新的 TableRef。

### 4. 中转表概念需要谨慎改名

DataFlowKit 的 `transit_tables` 是运行上下文里的命名副表。

FlowWeaver 已有 `TableRef`、DAG 边、共享表发布读取能力。迁移时不宜直接照搬一个全局 `transit_tables` 字典。

建议第一版将相关能力拆成两类：

```text
普通节点输出：通过 output_refs 沿 DAG 传递。
命名运行输出：后续规划为 PublishRunTableNode / LabelTableOutputNode 一类节点。
跨工作流共享：继续用 SharedPublication 类能力承接。
```

因此 `core.save_transit` 不建议第一批直接照搬，应先规划 FlowWeaver 自己的“运行内命名输出 / 共享发布”边界。

### 5. 控制流节点不能直接套进当前 DAG

DataFlowKit 的流程控制偏“有序计划 + 跳转 + 循环状态”。

FlowWeaver 当前主链路是 DAG 调度，天然不等同于 ordered program counter。

因此以下节点应后置：

```text
core.group
core.loop_start
core.loop_judge
core.jump_anchor
core.unconditional_jump
core.condition_check
core.conditional_jump
```

后续如果规划，应先讨论：

```text
DAG 是否支持条件边。
是否需要子工作流运行关系。
是否需要循环节点拥有队列状态。
是否允许工作流运行中动态决定下一个节点。
NodeRun 和 RuntimeEvent 如何记录跳转/循环路径。
```

## 风险标记转译

DataFlowKit 的 UI schema 中有 `risk` 字段。FlowWeaver 不需要照搬字段名，但可以转译成节点方案里的副作用和确认等级。

| DataFlowKit risk | FlowWeaver 规划含义 | 用户确认建议 |
|---|---|---|
| `safe_transform` | 只读输入表，写本次运行输出 | 不需要 |
| `schema_transform` | 改变输出表结构，但无外部副作用 | 不需要，预览建议 |
| `row_transform` | 增减或重排输出行，但无外部副作用 | 不需要，预览建议 |
| `file_read` | 读取外部文件系统 | 建议确认 |
| `file_action` | 写入或移动外部文件 | 必须确认 |
| `state_write` | 写运行状态或命名输出，可能扩展到外部存储 | 视目标而定 |
| `database_write` | 写数据库或外部表 | 必须确认 |
| `control_flow` | 改变执行路径 | 后置讨论 |
| `workflow_control` | 子流程、循环或执行结构控制 | 后置讨论 |
| `plugin_external` | 插件可能访问外部环境或启动进程 | 必须确认 |
| `unsupported_headless` | DataFlowKit UI schema 的提示偏旧，需要按实际 headless 支持重新评估 | 单独评估 |

## 推荐优先级

### P0：第一批纯表结构节点

适合先写节点方案，也最适合验证 FlowWeaver 的通用节点模板。

| DataFlowKit ID | 中文名 | FlowWeaver 暂定节点名 | 迁移理由 |
|---|---|---|---|
| `core.new_columns` | 新建列 | `AddColumnsNode` | 配置面小，纯输出新 TableRef |
| `core.delete_columns` | 删除列 | `DropColumnsNode` | 与字段选择器、schema 输出关系清楚 |
| `core.move_columns` | 移动列 | `ReorderColumnsNode` | 主要是 schema 顺序变换 |
| `core.copy_column` | 复制列 | `CopyColumnNode` | 输入/输出简单，适合样板 |
| `core.rename_columns` | 批量更改列名 | `RenameColumnsNode` | 字段冲突策略可形成通用模式 |
| `core.merge_columns` | 合并列 | `MergeColumnsNode` | 常用字段组合能力，副作用低 |
| `core.current_datetime_column` | 新建日期时间列 | `AddCurrentDateTimeColumnNode` | 需要明确“整次运行固定时间”语义 |

### P1：第一批纯表内容节点

这些节点仍是 TableRef 到 TableRef，但配置和边界更复杂。

| DataFlowKit ID | 中文名 | FlowWeaver 暂定节点名 | 迁移关注点 |
|---|---|---|---|
| `core.replace` | 批量替换 | `ReplaceTextNode` | 匹配模式、正则、空匹配、替换次数 |
| `core.extract` | 数据提取 | `ExtractTextNode` | 正则/固定位置/分隔符等方法需分层 |
| `core.datetime_format` | 格式规范化 / 日期时间解析 | `ParseDateTimeNode` | 歧义日期、状态列、模板输出 |
| `core.numeric_column` | 列数字运算 | `NumericColumnOperationNode` | 非数字、除零、行范围 |
| `core.dedupe` | 去重 / 重复数据处理 | `DeduplicateRowsNode` | 保留策略、标记列、行数变化 |
| `core.copy_row` | 复制行 | `CopyRowsNode` | 行号、插入位置、行数上限 |
| `core.delete_rows` | 删除行 | `DeleteRowsNode` | 条件删除、空行判断、预览提示 |
| `core.fill_value` | 填充值 | `FillCellsNode` | 填充范围、覆盖策略、单元格上限 |
| `core.sequence_fill` | 序列填充 | `FillSequenceNode` | 计数来源、方向、格式化 |
| `core.area_fill` | 区域填充 | `FillRangeNode` | 区域过大风险、字段范围 |
| `core.row_data_mapping` | 行数据映射填充 | `UnpivotRowsNode` | 行展开语义、保留字段、状态列 |

### P2：多表、运行状态和只读外部资源

这些节点值得规划，但不适合作为第一批最小实现。

| DataFlowKit ID | 中文名 | FlowWeaver 暂定节点名 | 后置原因 |
|---|---|---|---|
| `core.filter` | 高级筛选 | `AdvancedFilterRowsNode` | 条件语法、多表关联、配置 UI 更复杂；可先从现有 `FilterRowsNode` 增强 |
| `core.match_value_output` | 匹配值输出列名 | `LookupMatchedFieldNameNode` | 需要 lookup table 来源和多表读取能力 |
| `core.file_list` | 获取文件列表 | `ListFilesNode` | 只读外部文件系统，需要路径访问说明和数量上限 |
| `core.save_transit` | 保存中转数据 | `SaveRunTableNode` / `LabelTableOutputNode` | 需要先确定 FlowWeaver 的运行内命名输出语义 |
| `core.selected_columns_write` | 选定列写入指定表 | `WriteSelectedColumnsNode` | current/transit 可规划，SQLite 写入属于 P3 |

### P3：外部写入和高风险输出

这些节点应等通用用户确认机制、运行来源策略和结果摘要约定后再实现。

| DataFlowKit ID | 中文名 | FlowWeaver 暂定节点名 | 高风险点 |
|---|---|---|---|
| `core.batch_rename` | 批量重命名 | `BatchRenameFilesNode` | 修改真实文件名，可创建目录和写日志 |
| `core.writeback` | 字段映射写入表 | `WriteBackTableNode` | 修改 SQLite / 外部表，需要备份和匹配规则摘要 |
| `core.selected_columns_write` | 选定列写入指定表 | `WriteSelectedColumnsNode` | SQLite 目标写入需要强确认 |
| `core.save_transit` | 保存中转数据 | `ExportRunTableNode` | SQLite / xlsx 导出属于外部写入 |

### P4：控制流与插件生态

这些节点可能很有价值，但需要先扩展 FlowWeaver 的运行模型，不应混在第一批表处理节点里。

| DataFlowKit ID | 中文名 | FlowWeaver 暂定方向 | 后置原因 |
|---|---|---|---|
| `core.group` | 节点组 / 子工作流 | 子工作流 / 复合节点 | 需要父子 run、输入映射、输出映射、隔离状态 |
| `core.loop_start` | 循环执行起点 | 循环控制节点 | 当前 DAG 不直接支持 program counter 循环 |
| `core.loop_judge` | 循环判断回跳 | 循环控制节点 | 需要循环队列、结果表、回跳记录 |
| `core.jump_anchor` | 跳转锚点节点 | 控制流标签 | 当前 DAG 没有跳转锚点语义 |
| `core.unconditional_jump` | 无条件跳转节点 | 路径控制 | 会改变执行路径，需要调度模型支持 |
| `core.condition_check` | 条件判断节点 | 条件表达式节点 | 可先抽象为条件结果输出，暂不驱动调度 |
| `core.conditional_jump` | 条件跳转节点 | 条件路径控制 | 需要条件边或动态调度 |
| `core.plugin` / `plugin.<id>` | 插件节点 | 节点包 / 外部插件 | 需要插件清单、依赖隔离、外部进程和副作用策略 |

## 完整初提清单

| 分类 | DataFlowKit ID | 中文名 | FlowWeaver 暂定节点名 | 优先级 | 输入/输出 | 副作用等级 | 确认建议 | 实现前置 |
|---|---|---|---|---|---|---|---|---|
| 文件处理 | `core.file_list` | 获取文件列表 | `ListFilesNode` | P2 | 目录配置 -> TableRef | 只读外部资源 | 建议确认 | 文件路径配置、数量上限、DataRef/TableRef 输出约定 |
| 文件处理 | `core.batch_rename` | 批量重命名 | `BatchRenameFilesNode` | P3 | TableRef -> TableRef 状态表 | 写入外部文件 | 必须确认 | 用户确认、dry-run、文件冲突策略、日志输出 |
| 数据处理 | `core.new_columns` | 新建列 | `AddColumnsNode` | P0 | TableRef -> TableRef | 无外部副作用 | 不需要 | 通用表格变换 Runner |
| 数据处理 | `core.delete_columns` | 删除列 | `DropColumnsNode` | P0 | TableRef -> TableRef | 无外部副作用 | 不需要 | 字段选择器、schema 输出 |
| 数据处理 | `core.move_columns` | 移动列 | `ReorderColumnsNode` | P0 | TableRef -> TableRef | 无外部副作用 | 不需要 | 字段排序配置 |
| 数据处理 | `core.copy_column` | 复制列 | `CopyColumnNode` | P0 | TableRef -> TableRef | 无外部副作用 | 不需要 | 字段选择器、冲突策略 |
| 数据处理 | `core.rename_columns` | 批量更改列名 | `RenameColumnsNode` | P0 | TableRef -> TableRef | 无外部副作用，schema 变化 | 不需要 | 字段映射、重名策略 |
| 数据处理 | `core.merge_columns` | 合并列 | `MergeColumnsNode` | P0 | TableRef -> TableRef | 无外部副作用 | 不需要 | 多字段选择、输出字段冲突策略 |
| 数据处理 | `core.current_datetime_column` | 新建日期时间列 | `AddCurrentDateTimeColumnNode` | P0 | TableRef -> TableRef | 无外部副作用 | 不需要 | 运行时间来源约定 |
| 数据处理 | `core.replace` | 批量替换 | `ReplaceTextNode` | P1 | TableRef -> TableRef | 无外部副作用 | 不需要，建议预览 | 匹配/正则配置、错误提示 |
| 数据处理 | `core.extract` | 数据提取 | `ExtractTextNode` | P1 | TableRef -> TableRef | 无外部副作用 | 不需要，建议预览 | 多提取方法配置、状态列 |
| 数据处理 | `core.datetime_format` | 格式规范化 / 日期时间解析 | `ParseDateTimeNode` | P1 | TableRef -> TableRef | 无外部副作用 | 不需要，建议预览 | 日期解析策略、歧义提示 |
| 数据处理 | `core.numeric_column` | 列数字运算 | `NumericColumnOperationNode` | P1 | TableRef -> TableRef | 无外部副作用 | 不需要 | 数字解析、除零/非数字策略 |
| 数据处理 | `core.dedupe` | 去重 / 重复数据处理 | `DeduplicateRowsNode` | P1 | TableRef -> TableRef | 无外部副作用，行数变化 | 不需要，建议预览 | 去重键、保留策略、标记列 |
| 数据处理 | `core.copy_row` | 复制行 | `CopyRowsNode` | P1 | TableRef -> TableRef | 无外部副作用，行数增加 | 不需要，建议预览 | 行号解析、行数上限 |
| 数据处理 | `core.delete_rows` | 删除行 | `DeleteRowsNode` | P1 | TableRef -> TableRef | 无外部副作用，行数减少 | 不需要，建议预览 | 条件表达式、空行判断 |
| 数据处理 | `core.fill_value` | 填充值 | `FillCellsNode` | P1 | TableRef -> TableRef | 无外部副作用 | 不需要，建议预览 | 填充范围、覆盖策略、单元格上限 |
| 数据处理 | `core.sequence_fill` | 序列填充 | `FillSequenceNode` | P1 | TableRef -> TableRef | 无外部副作用 | 不需要 | 序列生成、范围控制 |
| 数据处理 | `core.area_fill` | 区域填充 | `FillRangeNode` | P1 | TableRef -> TableRef | 无外部副作用 | 不需要，建议预览 | 区域解析、单元格上限 |
| 数据处理 | `core.row_data_mapping` | 行数据映射填充 | `UnpivotRowsNode` | P1 | TableRef -> TableRef | 无外部副作用，行数变化 | 不需要，建议预览 | 行展开语义、字段保留 |
| 数据处理 | `core.filter` | 高级筛选 | `AdvancedFilterRowsNode` | P2 | TableRef + 可选外部表 -> TableRef | 无外部副作用 | 不需要，建议预览 | 条件 DSL、多表来源、现有 FilterRowsNode 升级路径 |
| 数据处理 | `core.match_value_output` | 匹配值输出列名 | `LookupMatchedFieldNameNode` | P2 | TableRef + lookup TableRef -> TableRef | 读取额外表 | 不需要或建议确认 | 多输入 TableRef、lookup 表选择 |
| 输出 | `core.save_transit` | 保存中转数据 | `SaveRunTableNode` / `LabelTableOutputNode` | P2/P3 | TableRef -> 命名运行输出 / 外部文件 | 写运行数据或外部资源 | 视目标而定 | 运行内命名输出、外部导出确认 |
| 输出 | `core.selected_columns_write` | 选定列写入指定表 | `WriteSelectedColumnsNode` | P2/P3 | TableRef -> 目标表/状态表 | 写运行数据或数据库 | SQLite 必须确认 | 目标表抽象、写入模式、备份策略 |
| 输出 | `core.writeback` | 字段映射写入表 | `WriteBackTableNode` | P3 | TableRef -> 目标表/状态表 | 写数据库 | 必须确认 | 用户确认、事务、备份、匹配摘要 |
| 流程控制 | `core.group` | 节点组 / 子工作流 | `SubWorkflowNode` / `CompositeNode` | P4 | TableRef -> 子流程输出 | 改变运行结构 | 后置讨论 | 父子 run、输入输出映射 |
| 流程控制 | `core.loop_start` | 循环执行起点 | `LoopStartNode` | P4 | TableRef -> 循环项/队列 | 改变运行结构 | 后置讨论 | 循环状态、动态调度 |
| 流程控制 | `core.loop_judge` | 循环判断回跳 | `LoopJudgeNode` | P4 | TableRef -> 循环结果/跳转 | 改变运行结构 | 后置讨论 | 循环状态、回跳语义 |
| 流程控制 | `core.jump_anchor` | 跳转锚点节点 | `JumpAnchorNode` | P4 | 无或透传 | 改变执行路径标记 | 后置讨论 | 控制流模型 |
| 流程控制 | `core.unconditional_jump` | 无条件跳转节点 | `UnconditionalJumpNode` | P4 | 无或透传 | 改变执行路径 | 后置讨论 | 动态调度/条件边 |
| 流程控制 | `core.condition_check` | 条件判断节点 | `ConditionFlagNode` | P4 | TableRef -> 条件结果 | 可仅产出结果，也可驱动控制流 | 后置讨论 | 条件结果 DataRef、控制边语义 |
| 流程控制 | `core.conditional_jump` | 条件跳转节点 | `ConditionalJumpNode` | P4 | 条件结果 -> 跳转 | 改变执行路径 | 后置讨论 | 条件边、跳转记录 |
| 插件 | `core.plugin` / `plugin.<id>` | 插件节点 | `PluginNode` / 节点包机制 | P4 | 取决于插件 | 取决于插件，可外部进程 | 必须确认高风险插件 | 插件清单、隔离、依赖、外部副作用策略 |

## 默认配置字段提取

以下字段不代表 FlowWeaver 最终配置契约，只是后续逐节点写方案时的参考。

### P0 节点字段

| DataFlowKit ID | 默认配置字段 |
|---|---|
| `core.new_columns` | `columns_text`, `value_mode`, `default_value`, `conflict_mode`, `strip_column_name`, `allow_empty_name` |
| `core.delete_columns` | `fields` |
| `core.move_columns` | `order` |
| `core.copy_column` | `source_field`, `output_mode`, `new_field`, `target_field`, `trim_value`, `empty_default` |
| `core.rename_columns` | `mode`, `mappings`, `prefix`, `suffix`, `replace_match`, `replace_value`, `scope`, `scope_fields`, `duplicate_policy`, `missing_policy`, `trim_names` |
| `core.merge_columns` | `fields`, `separators`, `output_field`, `skip_empty`, `trim_value`, `empty_placeholder` |
| `core.current_datetime_column` | `output_mode`, `new_field`, `target_field`, `time_mode`, `format_mode`, `template`, `strftime_template` |

### P1 节点字段

| DataFlowKit ID | 默认配置字段 |
|---|---|
| `core.replace` | `target_field`, `match_mode`, `match_value`, `replace_value`, `replace_mode`, `case_sensitive`, `match_value_source`, `replace_value_source`, `match_value_field`, `replace_value_field`, `match_row_policy`, `match_row_index`, `replace_row_policy`, `replace_row_index`, `replace_count`, `skip_empty_match_value` |
| `core.extract` | `source_field`, `method`, `output_mode`, `new_field`, `unmatched_mode`, `unmatched_fixed`, `case_sensitive`, `strip_result`, `regex_pattern`, `regex_group`, `regex_find_all`, `regex_joiner`, `start_pos`, `extract_len`, `position_base`, `n_chars`, `delimiter`, `part_index`, `ignore_empty_part`, `before_key`, `after_key`, `between_occurrence`, `marker`, `find_mode`, `prefix`, `suffix` |
| `core.datetime_format` | `source_field`, `time_source_field`, `use_separate_time_field`, `parse_type`, `input_structure`, `position_base`, `year_start`, `year_len`, `month_start`, `month_len`, `day_start`, `day_len`, `hour_start`, `hour_len`, `minute_start`, `minute_len`, `second_start`, `second_len`, `date_delimiter`, `time_delimiter`, `custom_date_delimiter`, `custom_time_delimiter`, `date_order`, `ambiguous_date_policy`, `year_rule`, `auto_window_pivot`, `output_template`, `time_output_template`, `datetime_output_template`, `output_mode`, `new_field`, `unmatched_mode`, `unmatched_fixed`, `strip_value`, `output_status`, `status_field`, `component_prefix` |
| `core.numeric_column` | `target_field`, `operation`, `operand_source`, `operand_value`, `operand_field`, `row_offset`, `sequence_start`, `sequence_step`, `output_mode`, `output_field`, `non_number_policy`, `non_number_fixed`, `divide_zero_policy`, `divide_zero_fixed`, `decimal_places`, `range_mode`, `start_row`, `end_row`, `reference_field` |
| `core.dedupe` | `dedupe_mode`, `key_fields`, `trim`, `ignore_case`, `empty_key_policy`, `keep_policy`, `output_mode`, `add_marker_columns`, `duplicate_group_field`, `duplicate_status_field`, `duplicate_index_field`, `duplicate_count_field`, `keep_flag_field` |
| `core.copy_row` | `source_row`, `copy_count`, `insert_mode`, `insert_row` |
| `core.delete_rows` | `delete_mode`, `row_spec`, `start_row`, `end_row`, `condition_field`, `condition_op`, `condition_value`, `case_sensitive`, `empty_mode`, `empty_field` |
| `core.fill_value` | `target_field`, `start_row`, `direction`, `value_source`, `manual_value`, `source_field`, `source_end_field`, `source_row`, `multi_field_fill_direction`, `source_start_row`, `source_end_row`, `source_range_mode`, `start_row_mode`, `end_mode`, `count`, `end_row`, `end_field`, `reference_field`, `overwrite_rule` |
| `core.sequence_fill` | `target_field`, `start_row`, `direction`, `start_row_mode`, `start_value`, `step`, `count_source_mode`, `end_mode`, `count`, `end_row`, `end_field`, `reference_field`, `overwrite_rule`, `zero_pad`, `prefix`, `suffix` |
| `core.area_fill` | `start_field`, `end_field`, `start_row`, `end_row`, `value_source`, `manual_value`, `source_field`, `source_end_field`, `source_row`, `multi_field_fill_direction`, `source_start_row`, `source_end_row`, `source_range_mode`, `start_row_mode`, `end_row_mode`, `reference_field`, `overwrite_rule` |
| `core.row_data_mapping` | `mode`, `start_row`, `end_mode`, `count`, `end_row`, `value_fields`, `keep_fields`, `output_value_field`, `output_source_field`, `source_field_name`, `output_original_row`, `original_row_field`, `output_status`, `status_field`, `empty_mode`, `empty_fixed`, `trim_value` |

### 后置节点字段

| DataFlowKit ID | 默认配置字段 |
|---|---|
| `core.filter` | `logic`, `conditions`, `join_rules`, `join_logic`, `extra_tables`, `output_fields`, `result_limit`, `max_intermediate`, `remove_duplicates` |
| `core.match_value_output` | `source_field`, `lookup_table`, `lookup_fields`, `match_mode`, `output_field`, `output_match_value`, `match_value_field`, `output_match_row`, `match_row_field`, `output_status`, `status_field`, `multi_match_policy`, `multi_match_separator`, `no_match_value`, `skip_empty_lookup_value` |
| `core.file_list` | `directory`, `recursive`, `include_files`, `include_dirs`, `include_hidden`, `extensions`, `name_contains`, `glob_pattern`, `max_files` |
| `core.batch_rename` | `path_field`, `new_name_field`, `name_value_type`, `new_path_field`, `status_field`, `auto_append_ext`, `allow_dirs`, `create_target_dirs`, `conflict_mode`, `actual_rename`, `write_log`, `log_path` |
| `core.save_transit` | `transit_name`, `save_memory`, `save_sqlite`, `sqlite_table`, `sqlite_mode`, `save_xlsx`, `xlsx_path`, `stop_after_save` |
| `core.selected_columns_write` | `source_type`, `source_sqlite_table`, `source_transit_table`, `selected_fields`, `target_type`, `target_table`, `target_transit_table`, `write_mode`, `field_name_mode`, `target_prefix`, `target_suffix`, `field_mappings`, `overwrite_rule`, `enable_write`, `backup_before_write` |
| `core.writeback` | `writeback_direction`, `target_table`, `source_table`, `use_match_rules`, `match_rules`, `field_mappings`, `overwrite_policy`, `source_empty_policy`, `source_empty_fixed`, `no_match_policy`, `multi_match_policy`, `duplicate_target_policy`, `enable_write`, `backup_before_write`, `output_preview_table`, `sequential_insert_missing_rows` |

## 后续逐节点方案撰写建议

第一轮建议先写 P0 的 7 个节点方案：

```text
AddColumnsNode
DropColumnsNode
ReorderColumnsNode
CopyColumnNode
RenameColumnsNode
MergeColumnsNode
AddCurrentDateTimeColumnNode
```

这 7 个节点可以集中验证：

```text
TableRef 输入输出。
字段选择器配置。
schema 变更输出。
字段冲突策略。
NodeRun / RuntimeEvent 结果摘要。
不依赖权限审计。
不要求 WorkflowRunProcess 增加节点专用逻辑。
```

第二轮再写 P1 的内容处理节点，重点把“行数变化、正则/日期/数字解析、单元格上限、预览提示”收口。

第三轮再讨论 P2/P3/P4。尤其是 `save_transit`、`selected_columns_write`、`writeback`、`group`、`loop`、`plugin`，这些节点表面上可以迁移，但会推动 FlowWeaver 的运行模型、确认机制或插件隔离边界，不能和普通表格节点混为一类。

## 当前结论

DataFlowKit 对 FlowWeaver 最有价值的不是旧 UI 或旧执行链，而是它已经沉淀出的节点能力目录、稳定 ID、默认配置字段、headless 行为和副作用开关。

FlowWeaver 应优先吸收其中的纯表格节点能力，并按自己的低耦合节点模型重新规划：

```text
节点定义元数据化。
节点执行入口通用化。
表格输入输出 TableRef 化。
外部副作用显式说明化。
高风险操作用户确认化。
运行记录 RuntimeEvent / NodeRun 化。
权限审计字段不再进入节点模板。
```

推荐下一步：从 P0 的 `AddColumnsNode` 开始撰写单节点方案，用它验证 DataFlowKit 节点能力向 FlowWeaver V2 节点模板的映射方式。
