# 阶段Q：后端表流转执行主计划

> 文档状态：主方向执行稿
> 当前用途：把“节点表输入输出、多表槽位、内部表状态、后台运行”收束成后端优先的实施路线
> 当前边界：本阶段先改后端；前端正在重构，只在本文记录后续 UI 契约，不直接改 UI

## 1. 一句话结论

阶段 Q 的后端主方向是：

```text
节点声明自己需要哪些表
-> 主程序把用户选择解析成 TableRef / 可写目标映射
-> 节点自己决定如何处理表和写表
-> 主程序只登记表状态、提供基础读写能力和数据预览查询入口
```

这条路线的关键不是让主程序变成“表操作中心”，而是让主程序成为“表目录 + 表映射 + 低层 provider 能力”的稳定基座。

## 2. 本文范围

### 2.1 本阶段要做

| 方向 | 要点 |
| --- | --- |
| 后端节点协议 | 增加节点输入槽位、输出槽位和目标映射能力 |
| 表选择解析 | 从稳定选择器解析上游当前表、内存表、运行内 SQL 表、外部 SQL 引用表 |
| 内部表写入 | 给节点提供运行内 SQL 和内存表的基础写入能力 |
| 节点落点 | 先选择一个低风险节点试点，再推广到写入类、多槽位节点和插件节点 |
| 数据预览 | 继续通过 TableRef 和 provider rows 查询当前状态 |
| 后台运行 | 后续复用同一套 workflow process 和 TableRef 机制 |

### 2.2 本阶段暂不做

| 不做 | 原因 |
| --- | --- |
| 不改 UI 代码 | 前端正在重构，避免并行竞态 |
| 不让主程序管理覆盖、追加、合并语义 | 这些是节点业务，不应进入调度层 |
| 不把真实本地文件写入放进通用表输出 | 文件副作用必须由文件类节点或插件节点显式处理 |
| 不把真实外部 SQL 写入放进通用表输出 | 外部 SQL 修改继续由专门 SQL 节点处理 |
| 不让配置字控制表产物 | 配置字只限制日志、事件、进度、metrics、payload 等反馈量 |
| 不做全量节点一次性迁移 | 先打通协议、helper 和试点节点，降低回归风险 |

## 3. 核心边界

### 3.1 主程序负责

| 职责 | 说明 |
| --- | --- |
| 节点槽位声明读取 | 读取节点定义里的输入槽位、输出槽位、允许表类型、默认选择 |
| 表目录提供 | 给 UI 和节点配置提供当前可用表列表 |
| 输入选择器解析 | 把用户保存的稳定选择器解析成运行期 TableRef |
| 输出目标映射 | 把用户选择的新建表或已有表解析成节点可用目标 |
| 基础 provider 能力 | 提供分页读取、批量写入、事务发布、原子替换等底层能力 |
| 表状态登记 | 登记 TableRef、来源节点、输出槽位、storage kind、logical name |
| 数据预览入口 | 按 TableRef 分页返回 rows，不把整表推给 UI |

### 3.2 节点负责

| 职责 | 说明 |
| --- | --- |
| 理解槽位业务含义 | 例如 `main_table`、`rules_table`、`mapping_table` 分别代表什么 |
| 数据处理 | 自己决定如何读取多张表、如何计算结果 |
| 表操作语义 | 新建、覆盖、追加、按主键更新、合并都归节点 |
| 真实副作用 | 文件写入、文件删除、真实 SQL 修改只在指定节点内显式发生 |
| 输出结果说明 | 在 `output_refs` 和 `summary` 中说明当前表、辅助表、目标表关系 |

### 3.3 UI 后续只按契约渲染

UI 后续只需要根据节点定义显示：

```text
输入槽位名称 + 说明 + 表下拉菜单
输出槽位名称 + 说明 + 目标类型 + 表名 / 已有表下拉菜单
```

UI 不理解节点业务，也不替节点决定覆盖、追加、合并。

## 4. 代码现状总览

### 4.1 TableRef 基础已经存在

当前 `TableRefModel` 已经能表达表引用的核心信息：

| 文件 | 现状 |
| --- | --- |
| `src/flowweaver/protocols/table_ref.py` | `TableRefModel` 包含 `table_ref_id`、`role`、`storage_kind`、`provider_id`、`logical_table_id`、`opaque_handle`、`schema`、`version`、`capabilities`、`lifecycle_status`、创建来源等字段 |
| `src/flowweaver/protocols/enums.py` | 已有 `TableRole.CURRENT / AUXILIARY / SHARED` |
| `src/flowweaver/protocols/enums.py` | 已有 `TableStorageKind.MEMORY / RUNTIME_SQL / EXTERNAL_SQL` |

判断：TableRef 模型可以作为阶段 Q 的基础，不需要推倒重做。

当前缺口：

- `TableRef` 能描述“表是什么”，但还缺少“这个表绑定到哪个节点槽位”的稳定运行记录。
- `logical_table_id` 已有，但还需要和输出槽位、选择器、表目录显示规则统一起来。

### 4.2 NodeTask 仍是无名 input_refs / output_refs

| 文件 | 现状 |
| --- | --- |
| `src/flowweaver/protocols/node_task.py` | `NodeTaskModel.input_refs: list[str]` |
| `src/flowweaver/protocols/node_task.py` | `NodeTaskResultModel.output_refs: list[str]` |
| `src/flowweaver/engine/runtime_store.py` | task/result 的 `input_refs_json`、`output_refs_json` 仍按 JSON list 存储 |

判断：当前模型只能表达“给节点一组表”，不能稳定表达“这张表是 main_table，那张表是 rules_table”。

当前缺口：

- 多表输入不能继续使用无名数组，否则插件节点和复杂节点会很难维护。
- 需要新增兼容字段，例如 `input_bindings` / `output_bindings` 或 `table_slot_bindings`。
- 旧字段暂时保留，用于默认当前表链路和兼容现有节点。

### 4.3 节点定义已有端口，但还不是表槽位

| 文件 | 现状 |
| --- | --- |
| `src/flowweaver/nodes/registry.py` | `NodePortSpec` 只有 `name` 和 `required` |
| `src/flowweaver/nodes/registry.py` | `NodeDefinitionSpec` 已有 `input_ports`、`output_ports` |

判断：节点定义已经有扩展入口，但目前端口信息太薄，不能驱动表目录、表类型限制、输出目标选择。

当前缺口：

- 输入槽位需要声明显示名、说明、是否必填、允许 storage kind、默认来源。
- 输出槽位需要声明默认 role、是否可输出当前表、是否可新建、是否可选择已有表、允许的可写基座。
- 需要保持 catalog schema 向后兼容，不能让现有 UI 或 API 因新增字段崩掉。

### 4.4 provider 基础已经比较完整

| 文件 | 现状 |
| --- | --- |
| `src/flowweaver/engine/runtime_table_provider.py` | `SQLiteRuntimeTableProvider` 支持 staging table、insert rows、publish staging |
| `src/flowweaver/engine/runtime_table_provider.py` | `publish_staging()` 内部已有 `BEGIN -> DROP -> CREATE -> INSERT -> COMMIT` 的事务化发布思路 |
| `src/flowweaver/engine/memory_table_provider.py` | `MemoryTableProvider` 支持创建内存表、读取、计数、删除 |
| `src/flowweaver/engine/external_sql_table_provider.py` | 外部 SQL provider 是只读引用，`create/drop/publish` 会报只读错误 |
| `src/flowweaver/engine/table_provider_registry.py` | 默认 provider registry 已注册 runtime SQL、external SQL、memory |

判断：后端不缺“能读表”的基础，缺的是统一的“节点可写目标”和“覆盖已有目标”的 helper。

当前缺口：

- runtime SQL 的事务发布目前偏 staging -> published，不是面向“已有目标表”的通用覆盖 helper。
- memory provider 当前创建表会把 rows 存入内存，没有统一的 append / atomic replace helper。
- external SQL 当前只读是正确边界；真实外部 SQL 写入不应被通用表流转接管。

### 4.5 表节点上下文已有批处理能力，但存在全表读取风险

| 文件 | 现状 |
| --- | --- |
| `src/flowweaver/nodes/table_node_handlers.py` | `require_single_input_ref()` 要求刚好一个输入 |
| `src/flowweaver/nodes/table_node_handlers.py` | `iter_row_batches()` 支持分页读取 |
| `src/flowweaver/nodes/table_node_handlers.py` | `publish_row_batches()` 支持批量产出 runtime SQL 当前表 |
| `src/flowweaver/nodes/table_node_handlers.py` | `read_all_rows()` 仍会一次性读取整张表 |

判断：普通纯表节点已经有较好的批处理基础，但写入类和另存类节点仍容易走全表读取。

当前缺口：

- 多表输入需要 `require_input_slot("main_table")` 这类具名 helper。
- 输出目标需要 `target_for_slot("result_table")` 这类具名 helper。
- 写入类节点要尽量从 `read_all_rows()` 迁移到批处理或 provider 侧事务写入。

### 4.6 调度默认只传上游 CURRENT 表

| 文件 | 现状 |
| --- | --- |
| `src/flowweaver/workflow_process/ready_queue.py` | `_current_input_refs_from_output_refs()` 只把 `TableRole.CURRENT` 的输出传给下游 |
| `src/flowweaver/workflow_process/node_tasks.py` | `submit_ready_node()` 仍接收 `input_refs` list |
| `src/flowweaver/workflow_process/main.py` | builtin table nodes 在 workflow process 内执行，其他节点走 executor |

判断：默认当前表链路是稳定的，应该保留；阶段 Q 需要在此基础上增加显式选择器解析，不要破坏原链路。

当前缺口：

- 选择上游内存表、运行内 SQL 表、外部 SQL 引用表作为输入时，不能再依赖只传 CURRENT 的默认逻辑。
- 需要根据工作流定义里的稳定选择器，在节点提交前生成具名输入绑定。
- 选择器不能保存运行期 `table_ref_id`，否则下次运行会失效。

### 4.7 数据预览 API 已经适合作为状态查看入口

| 文件 | 现状 |
| --- | --- |
| `src/flowweaver/api/routes_data.py` | `/api/v1/data/{table_ref_id}/rows` 按 provider 分页读取 rows，默认 limit 50，最大 200 |
| `src/flowweaver/api/routes_runs.py` | `/api/v1/runs/{workflow_run_id}/table-refs` 返回当前 run 的 TableRef 列表 |

判断：数据预览可以继续读取后端 TableRef 和 provider rows，不需要新增第二套数据记录机制。

当前缺口：

- 多槽位后，预览需要知道每个输入 / 输出槽位绑定了哪张表。
- 覆盖已有表后，预览显示当前状态即可；不承诺同名表历史版本管理。
- 内存表长期预览不稳定，稳定回看应优先 runtime SQL 或显式快照。

### 4.8 已有写入类节点能提供试点经验

| 文件 | 现状 |
| --- | --- |
| `src/flowweaver/nodes/builtin_table.py` | `SaveMemoryTableNodeHandler` 输出当前表和辅助内存表 |
| `src/flowweaver/nodes/builtin_table.py` | `WriteSelectedColumnsNodeHandler` 已有 `target_type`、`write_mode` 等配置 |
| `src/flowweaver/nodes/builtin_table.py` | `WriteBackTableNodeHandler` 已有运行内写入状态表和 runtime target 写入逻辑 |
| `src/flowweaver/nodes/builtin_table.py` | `ListFilesNodeHandler`、`BatchRenameFilesNodeHandler` 证明真实文件副作用已由指定节点显式控制 |
| `src/flowweaver/nodes/builtin_sql.py` | `SqlMappingNodeRunner` 用于把外部 SQL 映射成工作流内引用 |

判断：可以从已有写入类节点提取统一 helper，但不建议直接把所有节点一次性改成新协议。

当前缺口：

- 部分写入类逻辑自己找最新目标表、自己拼 append rows，存在重复和全表复制风险。
- `sqlite` target 写入当前未真正实现，继续保持“真实 SQL 写入只走专门 SQL 节点”的边界。
- 节点命名和实际行为需要实施前复核，避免把历史兼容字段误当新契约。

### 4.9 测试已有基础，但缺少槽位协议测试

| 测试文件 | 已覆盖方向 |
| --- | --- |
| `tests/integration/test_runtime_table_provider.py` | runtime SQL provider staging / publish / read / schema |
| `tests/integration/test_memory_table_provider.py` | memory provider 和 data API 读取 |
| `tests/integration/test_data_api_provider_routing.py` | provider registry 路由和只读能力 |
| `tests/integration/test_builtin_table_nodes.py` | 保存内存表、写入列、写回表、文件列表、批量重命名等节点 |
| `tests/integration/test_builtin_sql_mapping_node.py` | SQL 映射节点 |

判断：已有测试可以托住 provider 和部分节点行为，但阶段 Q 需要新增协议级、选择器级和多槽位级测试。

## 5. 后端实施阶段

### Q-BE0：代码现状锁定与术语收口

目标：先把当前字段、能力和边界固定下来，避免边实现边改语义。

当前代码情况：

- `TableRefModel` 已经有 role、storage kind、logical table、version、capabilities。
- `NodeTaskModel` 和 `NodeTaskResultModel` 还是 list-based refs。
- provider registry 已有 runtime SQL、memory、external SQL。
- 数据预览已按 TableRef 分页读取。

后端动作：

- 在文档和代码注释中统一“运行内 SQL 表”“外部 SQL 引用表”“真实外部 SQL 写入”“本地文件副作用”的命名。
- 明确当前表、内存表、运行内 SQL 表只属于 FlowWeaver 内部数据流转。
- 明确真实文件和真实外部 SQL 修改只能由指定节点显式执行。

验收：

- 阶段 Q 相关字段和文档不再混用 runtime SQL 与 external SQL。
- 新增协议命名能兼容旧 `input_refs` / `output_refs`。

### Q-BE1：节点表槽位声明模型

目标：让节点自己声明需要几个输入表、会输出几个表。

当前代码情况：

- `NodePortSpec` 只有 `name`、`required`。
- `NodeDefinitionSpec.input_ports / output_ports` 已存在，可作为兼容入口。

建议实现：

新增或扩展表槽位描述，例如：

```text
input_table_slots:
  - name: main_table
    display_name: 主表
    required: true
    allowed_storage_kinds: [RUNTIME_SQL, MEMORY, EXTERNAL_SQL]
    default_source: upstream_current

output_table_slots:
  - name: result_table
    display_name: 结果表
    default_role: CURRENT
    allow_current: true
    allow_new_memory: true
    allow_new_runtime_sql: true
    allow_existing_memory: true
    allow_existing_runtime_sql: true
```

后端动作：

- 保留旧 `input_ports / output_ports`。
- 新增表槽位 metadata，并输出到 node catalog。
- 给内置节点逐步补默认槽位声明。

验收：

- 没有声明新槽位的老节点仍按单输入 CURRENT 链路执行。
- 已声明槽位的节点 catalog 能返回槽位名、显示名、是否必填、允许类型。

### Q-BE2：稳定输入选择器解析

目标：让节点可以选择上游任意可读表，而不是只能吃上游 CURRENT。

当前代码情况：

- `ready_queue.py` 当前只从上游 `output_refs` 中保留 `TableRole.CURRENT`。
- `NodeTaskModel.input_refs` 是无名列表。

建议选择器：

```text
source_node_instance_id
output_slot
logical_table_id
storage_kind
output_role
```

规则：

- 工作流定义保存稳定选择器，不保存运行期 `table_ref_id`。
- 运行时只在已完成上游节点输出中解析，第一版不全局扫描历史表。
- 匹配 0 个、匹配多个、表不可读都要明确报错。

后端动作：

- 在 submit ready node 前解析节点输入槽位。
- 生成 `input_bindings`，例如 `main_table -> table_ref_id`。
- 旧 `input_refs` 可暂时填充为 bindings 的值列表，兼容旧 executor。

验收：

- 默认节点不配置输入源时，仍使用上游 CURRENT。
- 节点可显式选择上游 MEMORY / RUNTIME_SQL / EXTERNAL_SQL 表。
- 多槽位节点能按槽位名拿到不同 TableRef。

### Q-BE3：输出目标映射模型

目标：主程序告诉节点“可以写到哪里”，但不替节点决定“怎么写”。

当前代码情况：

- 现有写入类节点使用自己的 `target_type`、`target_table`、`write_mode`。
- 部分节点自己找 latest target ref。
- `NodeTaskResult.output_refs` 可以登记多个输出表，但没有输出槽位绑定信息。

建议目标模型：

```text
output_bindings:
  result_table:
    target_kind: current | new_memory | new_runtime_sql | existing_memory | existing_runtime_sql
    logical_table_id: stage_orders
    existing_table_ref_id: optional
```

规则：

- 当前表不可命名。
- 新建内存表 / 新建运行内 SQL 表可命名。
- 选择已有表时表名锁定，不在 UI 或后端偷偷改名。
- 输出到已有表时，覆盖、追加、更新、合并由节点配置和节点实现决定。

后端动作：

- 新增输出目标解析 helper。
- 把目标映射传给节点上下文。
- `summary` 记录输出槽位、目标类型、logical table、写入方式、产出 TableRef。

验收：

- 普通节点默认继续输出 CURRENT。
- 支持节点额外输出 MEMORY / RUNTIME_SQL 辅助表。
- 输出同名或已有表时，主程序只提供目标映射，不自动改写语义。

### Q-BE4：统一内部表 IO helper

目标：把重复的 provider 写入和查找逻辑收敛成后端基础能力。

当前代码情况：

- `BuiltinTableNodeContext.iter_row_batches()` 已有分页读取。
- `publish_row_batches()` 已有 runtime SQL 批量输出。
- runtime SQL `publish_staging()` 已有事务发布基础。
- memory provider 没有通用 atomic replace。
- 写入类节点存在 `read_all_rows()` + append 拼接的全表复制风险。

建议 helper：

| helper | 用途 |
| --- | --- |
| `require_input_slot(name)` | 根据槽位名取 TableRef |
| `iter_slot_batches(name)` | 按槽位分页读取 |
| `output_target(name)` | 获取输出槽位目标 |
| `publish_current_batches(...)` | 保持当前表输出 |
| `create_memory_batches(...)` | 创建内存表 |
| `replace_memory_table_atomically(...)` | 内存表原子替换 |
| `replace_runtime_table_transactionally(...)` | runtime SQL 事务化覆盖 |
| `list_run_table_directory(...)` | 给解析器和 UI 使用表目录 |

性能要求：

- 主程序和节点之间传 TableRef，不传整表 rows。
- 大表默认走 batches。
- append / merge 这类需要读已有目标的节点，必须先评估是否会全表复制。

验收：

- 新 helper 有 provider 级和节点级测试。
- 覆盖 runtime SQL 失败时不留下空表或半张表。
- 覆盖 memory 失败时原表仍可用。

### Q-BE5：单节点试点

目标：先用一个节点打通协议、输入选择、输出目标和预览。

推荐试点：

| 候选 | 优点 | 风险 |
| --- | --- | --- |
| 低风险纯表节点 | 行为简单，容易验证默认 CURRENT 不变 | 不能覆盖写入目标全部场景 |
| `SaveMemoryTableNode` | 已有辅助表输出经验 | 当前有全表读取，需要同时处理性能边界 |
| `WriteSelectedColumnsNode` | 已有 target/write mode 概念 | 逻辑复杂，不适合作为第一刀 |

建议第一版：

先选择一个低风险纯表节点或 `SaveMemoryTableNode` 的后端协议试点，不直接迁移所有写入类节点。

验收：

- 默认输入 CURRENT 正常。
- 显式输入上游辅助表正常。
- 输出 CURRENT 正常。
- 额外输出 memory 或 runtime SQL 正常。
- 数据预览能看到新 TableRef。

### Q-BE6：已有目标覆盖试点

目标：验证“节点管理表操作语义，主程序只提供可写目标和事务能力”。

当前代码情况：

- runtime SQL 有事务发布基础。
- memory 表还缺原子替换 helper。
- 写入类节点已有 create / overwrite / append / upsert 配置雏形。

后端动作：

- 选择一个写入类节点作为覆盖试点。
- 节点内部决定覆盖语义。
- runtime SQL 覆盖走事务化 helper。
- memory 覆盖先生成新结果，成功后再替换目标。

验收：

- 覆盖成功后，数据预览显示最新表状态。
- 覆盖失败后，旧表仍保持可读。
- 主程序没有新增覆盖 / 追加 / 合并业务分支。

### Q-BE7：多槽位节点 / 插件节点试点

目标：验证多表输入不是无名数组，而是稳定槽位。

建议试点形态：

```text
main_table -> 主数据
rules_table -> 规则表
mapping_table -> 映射表
```

后端动作：

- 节点定义声明多个 input slots。
- resolver 生成具名 input bindings。
- 节点通过 `require_input_slot("rules_table")` 获取对应 TableRef。
- 输出可以声明多个 output slots。

验收：

- 槽位缺失时错误明确。
- 槽位选错 storage kind 时错误明确。
- 插件节点不需要理解 `input_refs[0]` 这类脆弱顺序。

### Q-BE8：数据预览与后台运行对齐

目标：让手动运行、预览运行、后台运行复用同一套表状态和查询方式。

当前代码情况：

- 运行表 refs 可按 workflow run 查询。
- rows 可按 TableRef 分页查询。
- 后台运行入口和列表仍是后续阶段。

后端动作：

- 保持后台运行也创建普通 WorkflowRun。
- 后台运行产生的 runtime SQL 表继续登记 TableRef。
- UI 后续只查询 run 的 table refs 和 data rows。
- 内存表不作为后台长期回看来源；需要稳定回看时使用 runtime SQL 或显式快照。

验收：

- 手动运行和后台运行没有第二套数据记录机制。
- 配置字只影响反馈量，不影响表产物。
- 数据预览查询仍是分页，不把大表塞进事件或日志。

## 6. 前端后续契约

本阶段不改 UI 代码，但后端要为后续 UI 提供清晰契约。

### 6.1 节点配置区

UI 后续应按节点 schema 渲染：

| 区域 | 内容 |
| --- | --- |
| 输入表 | 每个输入槽位一行，显示中文名、说明、表下拉 |
| 输出表 | 每个输出槽位一行，显示目标类型、表名输入或已有表下拉 |
| 当前表 | 默认主链路，不允许命名 |
| 内存表 | 显示 `内存表: 表名` |
| 运行内 SQL 表 | 显示 `运行SQL: 表名` |
| 外部 SQL 引用表 | 显示 `SQL: 数据库名 / 表名` 或 `SQL: 连接名 / 表名` |

### 6.2 数据预览区

UI 后续应显示：

| 信息 | 说明 |
| --- | --- |
| 表类型 | 当前表、内存表、运行 SQL、SQL 引用 |
| 来源节点 | 由哪个节点产生或映射 |
| 输出槽位 | 例如 `result_table`、`error_rows` |
| 当前有效状态 | 覆盖后显示最新内容 |
| 分页 rows | 通过 data API 分页读取 |

注意：数据预览不承诺同名表历史版本管理。旧内容需要保留时，用户自行另存新表名。

## 7. 性能硬边界

| 边界 | 要求 |
| --- | --- |
| 不传整表 | 主程序和节点之间传 TableRef / slot binding，不传 rows |
| 不全局扫历史表 | 选择器第一版只解析上游已完成输出 |
| 分页读取 | 普通处理走 `iter_row_batches` 或 provider 分页 |
| 批量写入 | runtime SQL 和 memory 写入使用 batch |
| 覆盖原子化 | runtime SQL 覆盖事务化，memory 覆盖原子替换 |
| 预览分页 | data API 保持 offset / limit，不返回全表 |
| 事件轻量 | 事件和日志只记录摘要，不携带大表数据 |
| 内存表不长期承诺 | 稳定预览优先 runtime SQL |

## 8. 耦合硬边界

| 边界 | 要求 |
| --- | --- |
| 主程序不理解节点业务 | 只处理槽位、TableRef、provider 能力和状态登记 |
| 主程序不实现表策略 | 新建、覆盖、追加、更新、合并由节点决定 |
| UI 不写节点专属表选择逻辑 | UI 由节点槽位声明驱动 |
| 文件副作用显式节点化 | 文件读取、写入、覆盖、删除、重命名只由指定节点或插件节点执行 |
| 外部 SQL 写入节点化 | 真实外部 SQL 修改只由 SQL 节点处理 |
| 配置字不管表产物 | 配置字不控制新建表、覆盖表、删除表、快照 |
| 旧链路兼容 | 默认 CURRENT 输入输出不能被新协议破坏 |

## 9. 推荐第一轮执行顺序

### 第一阶段：只补协议和测试

目标：不改节点行为，先让后端能表达槽位和目标。

动作：

- 新增表槽位 schema。
- node catalog 返回槽位 metadata。
- runtime store 可兼容保存 input / output bindings。
- 加协议序列化和兼容测试。

提交建议：`docs/协议` 或 `backend: 增加表槽位协议基础`

### 第二阶段：输入选择器 resolver

目标：让节点运行前能把稳定选择器解析成 TableRef。

动作：

- 实现上游输出表目录查询。
- 实现选择器匹配。
- 默认 CURRENT 链路保持不变。
- 增加 0 匹配、多匹配、不可读、storage kind 不符测试。

提交建议：`backend: 增加节点输入表选择器解析`

### 第三阶段：输出目标映射

目标：节点可以拿到“当前表 / 新建内存表 / 新建运行 SQL / 已有表”的目标。

动作：

- 定义 output target model。
- 解析节点配置中的输出目标。
- `summary` 记录目标信息。
- 增加目标解析和冲突测试。

提交建议：`backend: 增加节点输出表目标映射`

### 第四阶段：统一 IO helper

目标：把 provider 写入能力收成节点可复用 helper。

动作：

- 增加具名输入 helper。
- 增加具名输出目标 helper。
- 增加 runtime SQL 事务覆盖 helper。
- 增加 memory atomic replace helper。
- 增加批处理路径测试。

提交建议：`backend: 增加内部表读写辅助能力`

### 第五阶段：单节点试点

目标：验证新协议能真实跑通，不影响旧节点。

动作：

- 选择一个节点接入具名输入和输出目标。
- 验证默认 CURRENT 行为不变。
- 验证输入辅助表和输出辅助表。
- 验证数据预览 TableRef 可查。

提交建议：`backend: 接入首个节点表槽位试点`

### 第六阶段：覆盖写入试点

目标：验证节点内覆盖和 provider 原子能力。

动作：

- 选择一个写入类节点。
- 覆盖 runtime SQL 走事务。
- 覆盖 memory 走原子替换。
- 失败保持旧表。

提交建议：`backend: 加固节点覆盖写入试点`

### 第七阶段：多槽位试点

目标：验证复杂节点和插件节点的多表输入基础。

动作：

- 增加多输入槽位声明。
- 节点按槽位名读取多张表。
- 输出多个槽位。
- 增加槽位缺失、错绑、重复目标测试。

提交建议：`backend: 增加多表槽位试点`

## 10. 当前最稳落点

当前最稳的起手不是直接改写所有节点，而是：

```text
协议可表达
-> resolver 可解析
-> helper 可复用
-> 一个节点试点
-> 一个覆盖写入试点
-> 一个多槽位试点
```

这样可以保持主程序低耦合，也能避免前端重构期间产生 UI 竞态。

## 11. 执行前检查清单

每次开始阶段实现前，先检查：

| 检查项 | 通过标准 |
| --- | --- |
| 工作区状态 | 不混入前端并行重构文件 |
| 默认链路 | 普通 CURRENT 输入输出测试仍通过 |
| provider 能力 | runtime SQL、memory、external SQL 边界清晰 |
| 配置字边界 | 配置字不控制表产物 |
| 文件边界 | 本地文件副作用只在指定节点 |
| SQL 边界 | 外部 SQL 写入只在 SQL 节点 |
| 性能边界 | 新路径不默认 `read_all_rows()` |
| 数据预览 | 继续用 TableRef + provider rows 分页查询 |

## 12. 失败处理原则

| 场景 | 原则 |
| --- | --- |
| 输入选择器找不到表 | 节点运行失败，提示具体槽位和选择器 |
| 输入选择器匹配多个表 | 节点运行失败，提示候选冲突 |
| 输出目标不可写 | 节点运行失败，不自动改成新建表 |
| runtime SQL 覆盖失败 | 事务回滚，旧表保持可用 |
| memory 覆盖失败 | 不切换目标状态，旧表保持可用 |
| 数据预览刷新失败 | 运行结果仍按后端状态为准，UI 可重试读取 |
| 后台运行查询失败 | 不影响工作流执行状态，列表或预览提示查询失败 |

## 13. 与现有阶段文档关系

| 文档 | 本文如何使用 |
| --- | --- |
| `阶段Q_表流转与后台运行总览.md` | 本文是后端执行主线，承接总览里的阶段顺序 |
| `节点表输入输出策略方案.md` | 本文把输入源和输出保存转成后端协议、resolver、helper 阶段 |
| `多表输入输出与覆盖表方案.md` | 本文把槽位制、多输出、覆盖边界转成后端试点阶段 |
| `工作流表状态规划_内存表_SQL表_当前表.md` | 本文沿用当前表、内存表、运行内 SQL 表、外部 SQL 引用表边界 |
| `内存表优化建议步骤_临时.md` | 本文把内存表优化收进 helper 和后台预览边界 |
| `后台工作流实现方向.md` | 本文要求后台运行复用同一套 workflow process 和 TableRef 查询 |
| 配置字相关 MD | 本文只引用配置字边界：配置字限制反馈，不控制表产物 |

## 14. 最终目标状态

完成本文后，后端应达到：

```text
节点定义能声明输入 / 输出表槽位
工作流定义保存稳定表选择器
运行时解析选择器为 TableRef
节点按槽位读取表
节点按输出目标写当前表、内存表或运行内 SQL 表
覆盖和追加等语义留在节点内部
主程序登记 TableRef 和表状态
数据预览按 TableRef 分页查询
后台运行复用同一套执行和查询机制
配置字只控制反馈量，不影响数据产物
```

这就是阶段 Q 后端最稳的主方向。
