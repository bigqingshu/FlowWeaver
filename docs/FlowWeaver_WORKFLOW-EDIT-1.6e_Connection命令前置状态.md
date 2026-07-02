# FlowWeaver WORKFLOW-EDIT-1.6e：Connection 命令前置状态

> 文档状态：WORKFLOW-EDIT-1.6e 已完成
> 当前阶段：结构化 connection 命令接入前的 ViewModel 输入/选择状态
> 不适用范围：调用 connection patcher、修改 draft JSON、XAML 输入控件

## 1. 本小步目标

本小步新增 connection 新增输入：

```text
NewDraftConnectionId
NewDraftConnectionSourceNodeId
NewDraftConnectionSourcePort
NewDraftConnectionTargetNodeId
NewDraftConnectionTargetPort
```

并新增 connection 删除选择状态：

```text
SelectedWorkflowDefinitionDraftConnectionId
```

## 2. 当前行为

当前只做输入/选择状态，不执行写入：

* 不调用 `WorkflowDefinitionDraftConnectionPatcher`。
* 不修改 `WorkflowDefinitionDraftJson`。
* 不新增命令。
* 不修改 XAML。

加载或切换 workflow definition 时会重置 connection 输入和选择状态。

当 `WorkflowDefinitionDraftJson` 变化后，如果所选 draft connection 不再存在，会自动清空选择状态。

## 3. 验证结果

已执行：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "MainWindowViewModelWorkflowTests"
通过：51，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：253，失败：0，跳过：0
```

## 4. 下一小步建议

建议进入：

```text
WORKFLOW-EDIT-1.6f：
AddConnection / DeleteConnection 命令最小接入。
```

建议范围：

* 调用 `WorkflowDefinitionDraftConnectionPatcher`。
* 成功后写回 `WorkflowDefinitionDraftJson`。
* 失败后保留用户输入/选择。
* revision conflict、busy、无 draft、输入为空时禁用。
* 不修改 XAML。
