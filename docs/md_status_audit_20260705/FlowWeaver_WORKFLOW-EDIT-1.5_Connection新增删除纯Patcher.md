# FlowWeaver WORKFLOW-EDIT-1.5：Connection 新增 / 删除纯 Patcher

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：结构化只读解析、节点新增/删除、connection 新增/删除、ViewModel 命令、View 接入、用户友好 warning/error、节点/connection 输入体验和 smoke 复核已经落地。
> 未实现：自由画布、拖拽连线、完整撤销/重做和复杂 DAG 自动重排未在本阶段实现。
> 原因：这些能力超出结构化编辑最小闭环，已作为后续体验方向保留。

> 文档状态：WORKFLOW-EDIT-1.5 已完成
> 当前阶段：工作流结构化编辑的 connection 纯模型能力
> 不适用范围：ViewModel 命令、XAML 按钮、端口 schema 深校验、画布连线

## 1. 本小步目标

本小步新增 connection 的纯 patcher：

```text
WorkflowDefinitionDraftConnectionPatcher.AddConnection(...)
WorkflowDefinitionDraftConnectionPatcher.DeleteConnection(...)
```

并新增：

```text
WorkflowDefinitionDraftConnectionPatchResult
WorkflowDefinitionDraftConnectionPatchStatus
```

## 2. 当前能力

`AddConnection` 会：

* 校验 `connection_id` 必填且不重复。
* 校验 `source_node_id` / `target_node_id` 必填。
* 校验 `source_port` / `target_port` 必填。
* 校验 source / target node 在 `nodes` 中存在。
* append 新 connection。
* 保留 root 其他字段和现有 nodes。

`DeleteConnection` 会：

* 校验 `connection_id` 必填。
* 校验目标 connection 存在。
* 删除目标 connection。
* 保留 root 其他字段和现有 nodes。

两者都会校验：

```text
root 必须是 object
nodes 必须是 array
connections 必须是 array
```

## 3. 当前不做

本小步没有做：

* 端口 schema 深校验。
* connection 类型校验。
* 自动生成 connection_id。
* ViewModel 命令接入。
* XAML 按钮或输入区。
* 图形化拖拽连线。

## 4. 验证结果

已执行：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "WorkflowDefinitionDraftConnectionPatcherTests"
通过：8，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：245，失败：0，跳过：0
```

## 5. 下一小步建议

建议进入：

```text
WORKFLOW-EDIT-1.6：
结构化编辑 ViewModel 命令接入前置分析。
```

建议先只分析：

* 是否先接节点新增，还是节点删除和 connection 一起接。
* 是否需要新增输入 ViewModel。
* 默认 node_instance_id / connection_id 是否由 UI 生成。
* 命令失败信息如何复用现有 workflow definition validation message。
* revision conflict、busy、dirty、validation invalidation 如何复用。
