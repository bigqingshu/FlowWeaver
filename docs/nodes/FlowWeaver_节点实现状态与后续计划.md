# FlowWeaver 节点实现状态与后续计划

更新时间：2026-07-07

## 文档定位

本文件用于记录当前节点实现阶段的真实状态，并作为后续继续批量补节点的执行看板。

当前判断以代码事实为准：

```text
后端注册表：src/flowweaver/nodes/default_registry.py
节点执行器：src/flowweaver/nodes/builtin_table.py
配置字模型：src/flowweaver/workflow/definition.py
配置字运行合并：src/flowweaver/workflow/runtime_options.py
前端汉化：Avalonia_UI/Localization/zh-Hans.json
```

## 总体状态

当前默认注册表中共有 38 个后端节点：

| 类型 | 数量 | 状态说明 |
|---|---:|---|
| DataFlowKit 规划节点中已真实处理 | 23 | 已注册、已有 `config_schema`、已有 handler，并能产出真实表处理结果 |
| DataFlowKit 规划节点中部分真实执行 | 3 | 已支持低风险运行内写入或显式开关外部动作，默认仍保持预览或跳过 |
| DataFlowKit 规划节点中预览占位 | 4 | 已注册、已有 `config_schema`、已有 handler，但真实副作用或真实调度暂未执行；插件节点已先补执行前校验，跳转锚点、无条件跳转和条件跳转已输出控制状态表 |
| DataFlowKit 规划节点中未实现 | 3 | 已有方案文档，尚未进入默认注册表和后端 handler |
| 既有基础节点 | 8 | 生成测试表、筛选行、保存内存表、共享表、SQL 映射、测试节点等 |

## 已真实落地的 DataFlowKit 节点

这些节点已具备后端注册、配置 schema、独立 handler、运行输出和测试覆盖。

| 节点方案 | 后端节点类型 | 当前功能 |
|---|---|---|
| 新建列 | `AddColumnsNode` | 新增字段，支持默认值和基础数据类型 |
| 删除列 | `DeleteColumnsNode` | 删除指定列，保留输出 schema 一致性校验 |
| 复制列 | `CopyColumnNode` | 复制到新字段或覆盖目标字段，支持修剪和空值默认值 |
| 移动列 | `ReorderColumnsNode` | 调整列顺序，支持缺失字段和未列出字段策略 |
| 批量更改列名 | `RenameColumnsNode` | 支持手动映射、前缀、后缀、查找替换、缺失字段策略和重名策略 |
| 填充值 | `FillCellsNode` | 按起始行、方向、数量填充单列，支持固定值和当前行字段值 |
| 区域填充 | `FillRangeNode` | 在字段范围和行范围内填充，支持最大单元格保护 |
| 序列填充 | `FillSequenceNode` | 对既有字段按起始行、方向、结束方式、步长和格式化规则写入序列 |
| 批量替换 | `ReplaceTextNode` | 支持包含、等于、开头、结尾、正则、空值匹配，支持当前行值来源 |
| 删除行 | `DeleteRowsNode` | 支持指定行、行范围、条件、空行删除 |
| 复制行 | `CopyRowsNode` | 支持追加、前置、指定行前后插入，并限制最大输出行数 |
| 行数据映射填充 | `UnpivotRowsNode` | 支持将多值字段展开为多行，保留指定字段并输出来源、原始行和状态 |
| 去重与重复数据处理 | `DeduplicateRowsNode` | 支持关键字段、整行去重、保留策略和标记模式 |
| 高级筛选 | `AdvancedFilterRowsNode` | 支持多条件、且/或逻辑、输出字段、结果限制和去重 |
| 数据提取 | `ExtractTextNode` | 支持正则、位置、左右截取、分隔符、前后关键字提取 |
| 匹配值输出列名 | `LookupMatchedFieldNameNode` | 支持 lookup 输入表，输出匹配字段、匹配值、匹配行和状态 |
| 合并列 | `MergeColumnsNode` | 多字段合并，支持分隔符、跳过空值、修剪和冲突策略 |
| 列数字运算 | `NumericColumnOperationNode` | 支持加减乘除、序列、取整、行字段/行号/序列操作数 |
| 新建日期时间列 | `AddCurrentDateTimeColumnNode` | 新建或覆盖日期时间字段，支持固定时间、逐行、模板格式 |
| 格式规范化与日期时间解析 | `ParseDateTimeNode` | 支持日期、时间、日期时间解析，支持输出状态和未匹配策略 |
| 条件判断节点 | `ConditionFlagNode` | 第一版作为普通结果节点实现，输出条件状态表；支持行数、字段存在、字段值条件，支持固定值和当前行字段值来源，支持 `any`、`all`、`first`、`count` 聚合；不改变 DAG 执行路径 |
| 保存中转数据 | `SaveRunTableNode` | 保存运行内中转表，同时输出当前表和辅助中转表引用 |
| 获取文件列表 | `ListFilesNode` | 读取目录文件元数据，支持递归、隐藏项、扩展名、glob 和数量限制 |

## 已注册且部分真实执行的节点

这些节点已经开始具备真实写入能力，但只覆盖低风险运行内目标；外部数据库或文件类副作用仍保持可控边界。

| 节点方案 | 后端节点类型 | 当前状态 |
|---|---|---|
| 选定列写入指定表 | `WriteSelectedColumnsNode` | `target_type=run_table/memory_table` 且 `enable_write=true` 时可真实生成辅助目标表；支持 `create`、`overwrite`、`append`，状态表输出 `actual_write`、`affected_rows`、`skipped_rows`、`warning_count`、`warnings` 和 `target_table_ref_id`；`sqlite` 目标仍跳过真实写入 |
| 字段映射写入表 | `WriteBackTableNode` | `target_type=run_table/memory_table` 且 `enable_write=true` 时可按字段映射真实生成辅助目标表；支持 `create`、`overwrite`、`append`、空值跳过和状态摘要；`sqlite` 目标仍跳过真实写入 |
| 批量重命名 | `BatchRenameFilesNode` | 默认只输出计划；`actual_rename=true` 时可真实重命名文件，支持目标目录创建、冲突跳过/覆盖/自动追加序号和 JSONL 日志 |

## 已注册但处于预览占位的节点

这些节点已经可以在后端注册表和前端节点目录中出现，也有配置 schema 和状态表输出。当前为了保持外部副作用边界可控，只产出计划或状态，不执行真实写入或外部动作。

| 节点方案 | 后端节点类型 | 当前状态 |
|---|---|---|
| 插件节点 | `PluginNode` | 支持 `plugin_manifest` 执行前校验，输出清单状态、ID/版本匹配、输入输出绑定、必填参数、外部动作门控、执行就绪和错误结构；当前不实际执行插件 |
| 跳转锚点节点 | `JumpAnchorNode` | 输出统一控制状态表，记录 `anchor_name`、说明和后续调度参数；`actual_control=false`，不改变 DAG 执行路径 |
| 无条件跳转节点 | `UnconditionalJumpNode` | 输出统一控制状态表，支持按锚点或节点实例 ID 生成跳转计划；`actual_control=false`，不改变 DAG 执行路径 |
| 条件跳转节点 | `ConditionalJumpNode` | 读取条件状态表，支持 true/false 分支按锚点或节点实例 ID 生成跳转计划；`actual_control=false`，不改变 DAG 执行路径 |

## 既有基础节点

这些节点不全部来自 DataFlowKit 规划，但已经是当前默认注册表的一部分。

| 节点 | 后端节点类型 | 当前功能 |
|---|---|---|
| 生成测试表 | `GenerateTestTableNode` | 生成测试数据表 |
| 筛选行 | `FilterRowsNode` | 简单条件筛选 |
| 保存内存表 | `SaveMemoryTableNode` | 保存内存表并输出辅助引用 |
| 发布共享表 | `PublishSharedTablesNode` | 发布共享表 |
| 读取共享表 | `ReadSharedTablesNode` | 读取共享表 |
| SQL 映射 | `SqlMappingNode` | 从 SQLite 查询并发布表引用 |
| 延迟测试 | `DelayTestNode` | 测试执行延迟 |
| 故障测试 | `FaultTestNode` | 测试故障与隔离 |

## 配置字状态

配置字已经落地到工作流运行配置层，定位是控制运行观测和反馈，不进入节点业务 `config`。

| 能力 | 当前状态 |
|---|---|
| 工作流定义承载 | `WorkflowDefinitionModel.runtime_options` 已存在 |
| 工作流整体配置 | `runtime_options.workflow` 已存在 |
| 节点独立覆盖 | `runtime_options.node_overrides` 已存在 |
| 后端合并 | 已按系统默认值、工作流配置、节点覆盖合并 |
| 事件出口控制 | 已通过 `RuntimeOptionsEventSink` 控制事件等级、进度事件、事件限流、metrics、payload 限制和脱敏 |
| 前端入口 | 已有独立配置字窗口、结构化编辑和 JSON 草稿编辑 |
| 节点业务隔离 | 节点 handler 不直接读取配置字，业务参数继续由节点 `config_schema` 和节点 `config` 承载 |

当前配置字字段包括：

```text
profile
strict_validation
telemetry.log_level
telemetry.event_level
telemetry.event_rate_limit_per_second
telemetry.progress_enabled
telemetry.progress_interval_seconds
diagnostics.capture_error_context
diagnostics.include_metrics
diagnostics.payload_byte_limit
diagnostics.ttl_seconds
diagnostics.redact_columns
diagnostics.mask_policy
```

当前落点说明：

```text
配置字已经能影响运行事件输出和诊断 payload。
配置字没有写入节点 config，也不会污染节点业务 schema。
NodeTaskManager 可以按节点实例取得合并后的配置字。
NodeTaskModel 当前仍保持业务任务模型，不额外携带配置字字段。
```

## 未完成节点

这些节点已有规划文档，但尚未进入默认注册表和后端执行器。

| 节点方案 | 主要原因 | 推荐批次 |
|---|---|---|
| 循环执行起点 | 需要循环上下文和迭代边界 | 控制流批次 |
| 循环判断回跳 | 需要循环终止条件、最大迭代保护和运行记录表达 | 控制流批次 |
| 节点组与子工作流 | 需要子图封装、输入输出映射和运行记录层级 | 子工作流批次 |

## 下一步实施顺序

### 第一批：补齐低耦合纯表节点

当前已完成，保持主程序低改动，复用现有 handler、schema 和分批读写能力。

| 顺序 | 节点 | 交付内容 |
|---:|---|---|
| 1 | 批量更改列名 | 已完成：后端常量、默认注册、config schema、handler、测试、前端汉化 |
| 2 | 行数据映射填充 | 已完成：行展开配置、保留字段、来源字段、原始行、状态、测试、前端汉化 |
| 3 | 序列填充 | 已完成：独立 schema、序列生成规则、范围控制、测试、前端汉化 |

### 第二批：完善写入类节点的真实执行

目标是把当前状态表节点逐步升级为可执行节点，同时保留写入开关和状态输出。

| 顺序 | 节点 | 交付内容 |
|---:|---|---|
| 1 | 选定列写入指定表 | 已部分完成：运行中转表和内存表目标真实写入，外部 SQLite 仍保持跳过 |
| 2 | 字段映射写入表 | 已部分完成：运行中转表和内存表目标真实写入，外部 SQLite 仍保持跳过 |
| 3 | 写入结果统一 | 已部分完成：`WriteSelectedColumnsNode` 和 `WriteBackTableNode` 状态表均包含 affected_rows、skipped_rows、warnings、actual_write 和 target_table_ref_id |

### 第三批：完善外部资源类节点

目标是让外部动作继续可控，并保留状态表作为审阅和调试依据。

| 顺序 | 节点 | 交付内容 |
|---:|---|---|
| 1 | 批量重命名 | 已部分完成：显式开关真实重命名、冲突处理、目标目录创建、日志输出和失败状态 |
| 2 | 插件节点 | 已部分完成：`plugin_manifest` 清单草稿校验、参数绑定检查、外部动作门控、状态表和错误结构；真实插件发现与执行隔离后置 |

### 第四批：控制流与子工作流

目标是单独处理执行路径、循环、跳转和子图语义，避免把控制流能力混进普通表节点。

当前最小语义分析见：`docs/nodes/FlowWeaver_控制流节点最小语义分析.md`。

| 顺序 | 节点 | 交付内容 |
|---:|---|---|
| 1 | 条件判断节点 | 已完成第一版：作为普通结果节点实现，只输出条件状态表，不改变 DAG 执行路径 |
| 2 | 跳转锚点 | 已完成预览版：作为普通节点输出 `anchor` 控制状态表，不改变 DAG 执行路径 |
| 3 | 无条件跳转 | 已完成预览版：作为普通节点输出 `jump` 控制状态表，不改变 DAG 执行路径 |
| 4 | 条件跳转 | 已完成预览版：读取条件状态表并输出 `conditional_jump` 控制状态表，不改变 DAG 执行路径 |
| 5 | 循环执行起点、循环判断回跳 | 迭代上下文、最大迭代保护、终止状态 |
| 6 | 节点组与子工作流 | 子图输入输出映射和运行记录层级 |

## 下一步最小目标

建议先完成后端普通节点和运行内写入节点稳定基线，再进入控制流、循环、节点组和子工作流：

```text
1. 保持普通表节点现有 handler、schema 和批量读写方式稳定。
2. 运行内写入继续限制在 run_table / memory_table。
3. 补齐 create 已有目标、append 结构不一致、空值跳过统计等边界测试。
4. 外部 SQLite / 数据库写入继续保持状态表跳过，不打开真实写库。
5. `ConditionFlagNode` 与三类预览控制节点已完成，后续如需真实分支执行，必须先补条件边或动态调度协议。
```

低耦合纯表节点已经完成，写入类、外部资源类节点已开始逐步升级为可控真实执行；控制流批次已先落地不改变调度路径的条件结果节点和预览控制计划节点。
