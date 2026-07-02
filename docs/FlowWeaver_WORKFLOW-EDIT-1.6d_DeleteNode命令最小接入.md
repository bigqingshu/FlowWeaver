# FlowWeaver WORKFLOW-EDIT-1.6d：DeleteNode 命令最小接入

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
