# FlowWeaver WORKFLOW-EDIT-1.6c：DeleteNode 命令前置状态

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：结构化只读解析、节点新增/删除、connection 新增/删除、ViewModel 命令、View 接入、用户友好 warning/error、节点/connection 输入体验和 smoke 复核已经落地。
> 未实现：自由画布、拖拽连线、完整撤销/重做和复杂 DAG 自动重排未在本阶段实现。
> 原因：这些能力超出结构化编辑最小闭环，已作为后续体验方向保留。

> 文档状态：WORKFLOW-EDIT-1.6c 已完成
> 当前阶段：结构化节点删除命令接入前的 ViewModel 选择状态
> 不适用范围：调用 delete patcher、修改 draft JSON、XAML 选择控件

## 1. 本小步目标

本小步新增：

```text
SelectedWorkflowDefinitionDraftNodeInstanceId
```

它用于后续 DeleteNode 命令，不复用 `SelectedWorkflowDefinitionNode`。

原因：

* `SelectedWorkflowDefinitionNode` 来自 loaded workflow detail。
* DeleteNode 应面向当前 `WorkflowDefinitionDraftJson` 派生的 draft structure。
* 两者语义不同，不能混用。

## 2. 当前行为

当前只做选择状态，不执行删除：

* 不调用 `WorkflowDefinitionDraftNodePatcher.DeleteNode`。
* 不修改 `WorkflowDefinitionDraftJson`。
* 不新增命令。
* 不修改 XAML。

加载或切换 workflow definition 时会重置选择状态。

当 `WorkflowDefinitionDraftJson` 变化后，如果所选 draft node 不再存在，会自动清空选择状态。

## 3. 验证结果

已执行：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "MainWindowViewModelWorkflowTests"
通过：48，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：250，失败：0，跳过：0
```

## 4. 下一小步建议

建议进入：

```text
WORKFLOW-EDIT-1.6d：
DeleteNode 命令最小接入。
```

建议范围：

* 调用 `WorkflowDefinitionDraftNodePatcher.DeleteNode`。
* 成功后写回 `WorkflowDefinitionDraftJson`。
* `NODE_HAS_CONNECTIONS` 时显示明确错误，不级联删除。
* revision conflict、busy、无 draft、未选择 draft node 时禁用。
* 不修改 XAML。
