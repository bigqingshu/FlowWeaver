# FlowWeaver WORKFLOW-EDIT-1.6d：DeleteNode 命令最小接入

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：结构化只读解析、节点新增/删除、connection 新增/删除、ViewModel 命令、View 接入、用户友好 warning/error、节点/connection 输入体验和 smoke 复核已经落地。
> 未实现：自由画布、拖拽连线、完整撤销/重做和复杂 DAG 自动重排未在本阶段实现。
> 原因：这些能力超出结构化编辑最小闭环，已作为后续体验方向保留。

> 文档状态：WORKFLOW-EDIT-1.6d 已完成
> 当前阶段：结构化节点删除命令接入 ViewModel
> 不适用范围：XAML 按钮、级联删除、connection 命令、画布编辑

## 1. 本小步目标

本小步新增 ViewModel 命令：

```text
DeleteWorkflowDefinitionDraftNodeCommand
```

命令输入来自：

```text
SelectedWorkflowDefinitionDraftNodeInstanceId
```

底层调用：

```text
WorkflowDefinitionDraftNodePatcher.DeleteNode(...)
```

## 2. 当前行为

命令可用条件：

* EngineHost action 可用。
* 已加载 workflow definition。
* `WorkflowDefinitionDraftJson` 非空。
* 当前没有 validate / save busy。
* 没有 revision conflict。
* 已选择 draft node instance id。

命令成功时：

* 写回 `WorkflowDefinitionDraftJson`。
* 由现有 setter 触发 dirty、validation invalidation、draft structure 刷新。
* 被删除节点不再存在时，选择状态自动清空。
* 显示删除成功消息。

命令失败时：

* 不修改 `WorkflowDefinitionDraftJson`。
* 不清空选择状态。
* 显示 patcher warning，例如 `NODE_HAS_CONNECTIONS`。

## 3. 删除策略

当前策略保持：

```text
不做级联删除
有 connection 依赖时阻断
```

用户需要先删除相关 connection，再删除节点。

## 4. 验证结果

已执行：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "MainWindowViewModelWorkflowTests"
通过：50，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：252，失败：0，跳过：0
```

## 5. 下一小步建议

建议进入：

```text
WORKFLOW-EDIT-1.6e：
connection 命令接入前置状态。
```

建议范围：

* 新增 connection 新增输入状态。
* 新增 selected draft connection id 状态。
* 不调用 connection patcher。
* 不修改 XAML。
