# FlowWeaver WORKFLOW-EDIT-1.1：WorkflowDefinitionDraftStructure 只读解析模型

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：结构化只读解析、节点新增/删除、connection 新增/删除、ViewModel 命令、View 接入、用户友好 warning/error、节点/connection 输入体验和 smoke 复核已经落地。
> 未实现：自由画布、拖拽连线、完整撤销/重做和复杂 DAG 自动重排未在本阶段实现。
> 原因：这些能力超出结构化编辑最小闭环，已作为后续体验方向保留。

> 文档状态：WORKFLOW-EDIT-1.1 已完成
> 当前阶段：工作流结构化编辑的只读草稿结构入口
> 不适用范围：ViewModel 接入、XAML 改动、节点增删、连线增删、写回命令

## 1. 本小步目标

本小步只建立 `WorkflowDefinitionDraftJson` 的只读解析模型，为后续结构化编辑提供稳定输入。

完成内容：

* 新增 `WorkflowDefinitionDraftStructure`。
* 新增 `WorkflowDefinitionDraftNode`。
* 新增 `WorkflowDefinitionDraftConnection`。
* 新增 `WorkflowDefinitionDraftStructureStatus`。
* 新增 `WorkflowDefinitionDraftStructureBuilder`。
* 新增对应测试 `WorkflowDefinitionDraftStructureBuilderTests`。

## 2. 当前边界

解析入口：

```text
WorkflowDefinitionDraftStructureBuilder.Build(workflowDefinitionDraftJson)
```

输出结构：

```text
Status
IsSupported
Nodes
Connections
Warnings
NodeCount
ConnectionCount
```

本小步只读取：

```text
nodes[].node_instance_id
nodes[].node_type
nodes[].node_version
nodes[].display_name
nodes[].enabled
nodes[].config 是否为 object

connections[].connection_id
connections[].source_node_id
connections[].source_port
connections[].target_node_id
connections[].target_port
```

## 3. 错误与 warning 边界

以下情况会使结构不可用：

```text
WORKFLOW_DRAFT_JSON_INVALID
WORKFLOW_DRAFT_ROOT_NOT_OBJECT
WORKFLOW_DRAFT_NODES_MISSING
WORKFLOW_DRAFT_CONNECTIONS_MISSING
```

以下情况只跳过对应条目，并保留 warning：

```text
WORKFLOW_DRAFT_NODE_SKIPPED
WORKFLOW_DRAFT_NODE_INSTANCE_ID_MISSING
WORKFLOW_DRAFT_CONNECTION_SKIPPED
WORKFLOW_DRAFT_CONNECTION_ID_MISSING
```

这样可以保证：

* 根结构不完整时不进入后续编辑。
* 单个脏节点或脏连线不会阻断只读摘要。
* 后续 ViewModel 可以根据 `IsSupported` 和 `Warnings` 做明确状态展示。

## 4. 验证结果

已执行：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "WorkflowDefinitionDraftStructureBuilderTests"
通过：6，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：222，失败：0，跳过：0
```

## 5. 下一小步建议

建议进入：

```text
WORKFLOW-EDIT-1.2：
接入 ViewModel 只读草稿结构状态。
```

建议范围：

* 从 `WorkflowDefinitionDraftJson` 派生 `WorkflowDefinitionDraftStructure`。
* 与已加载的 `WorkflowDefinitionDetail.Nodes` / `Connections` 保持命名和语义区分。
* JSON 手动编辑后刷新草稿结构状态。
* 不新增节点增删命令。
* 不修改 XAML。
