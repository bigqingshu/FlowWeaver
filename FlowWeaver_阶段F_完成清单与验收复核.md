# FlowWeaver 阶段F完成清单与验收复核

复核日期：2026-06-28

本清单依据：

1. `00_第一阶段技术接口与验收规范.md`
2. `01_第一阶段执行方案.md`

后续讨论文档仅作为背景，不纳入本阶段验收范围。

## 一、阶段F范围

阶段F目标为“运行数据库与TableRef”。

本阶段只覆盖：

- 每个 `WorkflowRun` 独立 SQLite 运行数据库文件。
- `SQLiteRuntimeTableProvider` 最小读写能力。
- `STAGING` 表创建、写入与发布。
- `PUBLISHED` 表生成与只读边界。
- `RuntimeDataRegistry` 登记、读取与按运行列出 `TableRef`。
- `GenerateTestTableNode` 最小内置节点。
- `FilterRowsNode` 最小内置节点。
- 主循环中上游 `output_refs` 到下游 `input_refs` 的传递。
- IPC / NodeTask 边界只传 `TableRef` ID，不传完整表数据。

## 二、完成清单

| 项目 | 状态 | 代码位置 | 验收证据 |
| --- | --- | --- | --- |
| 每个 WorkflowRun 独立 SQLite 文件 | 已完成 | `src/flowweaver/engine/runtime_table_provider.py` | `tests/integration/test_runtime_table_provider.py` |
| SQLiteRuntimeTableProvider | 已完成 | `src/flowweaver/engine/runtime_table_provider.py` | `tests/integration/test_runtime_table_provider.py` |
| STAGING 表 | 已完成 | `SQLiteRuntimeTableProvider.create_staging_table` | `test_sqlite_runtime_table_provider_creates_staging_table_and_reads_rows` |
| PUBLISHED 表 | 已完成 | `SQLiteRuntimeTableProvider.publish_staging` | `test_sqlite_runtime_table_provider_publishes_staging_table_as_immutable_copy` |
| RuntimeDataRegistry | 已完成 | `src/flowweaver/engine/runtime_data_registry.py` | `tests/integration/test_runtime_data_registry.py` |
| TableRef 按 WorkflowRun 列出 | 已完成 | `RuntimeStore.list_table_refs_by_workflow_run` | `test_runtime_data_registry_registers_and_publishes_table_refs` |
| GenerateTestTableNode | 已完成 | `src/flowweaver/nodes/builtin_table.py` | `test_generate_test_table_node_publishes_runtime_sql_table_ref` |
| FilterRowsNode | 已完成 | `src/flowweaver/nodes/builtin_table.py` | `test_filter_rows_node_publishes_filtered_table_ref_without_mutating_input` |
| 字段缺失返回 VALIDATION_ERROR | 已完成 | `BuiltinTableNodeRunner._execute_filter` | `test_filter_rows_node_returns_validation_error_for_missing_field` |
| 主循环传递 TableRef | 已完成 | `src/flowweaver/workflow_process/main.py` | `test_workflow_process_passes_upstream_table_refs_to_downstream_task` |
| 多上游 TableRef 传递边界 | 已完成 | `src/flowweaver/workflow_process/main.py` | `test_workflow_process_passes_multiple_upstream_table_refs_in_stable_order` |
| 上游空输出边界 | 已完成 | `src/flowweaver/workflow_process/main.py` | `test_workflow_process_passes_empty_input_refs_when_upstream_has_no_outputs` |
| IPC 不传完整表 | 已完成 | `src/flowweaver/node_executor/process.py` | `test_node_executor_process_ipc_passes_table_refs_without_inline_rows` |

## 三、阶段F验收项对照

### 1. GenerateTestTableNode成功

已满足。

覆盖点：

- 生成指定行数。
- Schema 正确写入 `TableRef`。
- 输出为 `RUNTIME_SQL`。
- 输出状态为 `PUBLISHED`。
- 可通过 `SQLiteRuntimeTableProvider.read_rows` 读取生成数据。

主要测试：

- `tests/integration/test_builtin_table_nodes.py::test_generate_test_table_node_publishes_runtime_sql_table_ref`

### 2. FilterRowsNode成功

已满足。

覆盖点：

- 输入为一个 `TableRef`。
- 根据 `field`、`operator`、`value` 过滤。
- 输出新的 `TableRef`。
- 输入表保持不变。
- 字段不存在时返回 `VALIDATION_ERROR`。

主要测试：

- `tests/integration/test_builtin_table_nodes.py::test_filter_rows_node_publishes_filtered_table_ref_without_mutating_input`
- `tests/integration/test_builtin_table_nodes.py::test_filter_rows_node_returns_validation_error_for_missing_field`

### 3. 节点间只传TableRef

已满足。

实现方式：

- `NodeTaskModel.input_refs` 只保存上游输出 `TableRef` ID。
- `NodeTaskResultModel.output_refs` 只保存输出 `TableRef` ID。
- 主循环通过上游成功结果的 `output_refs` 组装下游 `input_refs`。
- 表数据本体保存在运行 SQLite 数据库中，不进入 `NodeTask`。

主要测试：

- `tests/integration/test_workflow_process_main.py::test_workflow_process_passes_upstream_table_refs_to_downstream_task`
- `tests/integration/test_workflow_process_main.py::test_workflow_process_passes_multiple_upstream_table_refs_in_stable_order`
- `tests/integration/test_workflow_process_main.py::test_workflow_process_passes_empty_input_refs_when_upstream_has_no_outputs`

### 4. 不通过IPC传完整表

已满足。

实现方式：

- `NODE_TASK_SUBMIT` 的 payload 来自 `NodeTaskModel`，包含 `input_refs`，不包含表行数据。
- `NODE_TASK_COMPLETED` 的 result 来自 `NodeTaskResultModel`，包含 `output_refs`，不包含表行数据。

主要测试：

- `tests/unit/test_node_executor_process.py::test_node_executor_process_ipc_passes_table_refs_without_inline_rows`

## 四、本阶段验证结果

最近一次阶段F复核验证：

```text
.\python312\python.exe -m ruff check src tests migrations
结果：通过

.\python312\python.exe -m mypy
结果：通过

.\python312\python.exe -m pytest
结果：103 passed, 1 warning
```

保留警告：

```text
StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
```

该警告为既有测试依赖提示，不影响阶段F验收结论。

## 五、未纳入阶段F的事项

以下事项不属于阶段F完成范围，本阶段未实现：

- 通用数据库 Provider 体系。
- 跨 WorkflowRun 共享表。
- `SharedPublication` 发布流程。
- `ReadLease` / `TableLease` 完整生命周期。
- 运行表 GC / 清理策略。
- 节点超时、取消、强制终止与执行器重建。
- DAG 并行分支调度。
- 插件系统接入。
- 完整 UI TableRef 摘要页。

其中部分数据库模型或讨论文档中已有预留结构，但不作为阶段F完成项。

## 六、阶段F结论

阶段F按当前实施边界已完成。

阶段F完成后的主线能力为：

- 内置节点可以在运行数据库中生成和过滤表。
- 运行中间数据以 `TableRef` 形式登记和传递。
- 主循环可以把上游节点的输出引用交给下游节点。
- IPC 与 NodeTask 边界不传完整表数据。

建议下一步在进入阶段G前，先确认是否需要单独提交本清单；若进入阶段G，应以“故障隔离”为边界，不回填阶段F之外的共享表或租约能力。
