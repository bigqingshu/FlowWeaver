# FlowWeaver WORKFLOW-EDIT-2.3d：connection View 最小接入

> 文档状态：WORKFLOW-EDIT-2.3d 已完成
> 当前阶段：结构化编辑 connection 输入体验收口
> 不适用范围：ViewModel 改动、port 下拉、端口 schema 深校验、后端 API 改动

## 1. 阶段目标

在 `WorkflowSummaryView.axaml` 的新增 connection 表单中接入 source / target 节点选择控件：

```text
WorkflowDefinitionDraftStructure.Nodes
-> SelectedNewDraftConnectionSourceNode
-> SelectedNewDraftConnectionTargetNode
```

并继续保留 source / target node id 手动输入。

## 2. 修改范围

已修改：

* `Avalonia_UI/Views/Components/Workflow/WorkflowSummaryView.axaml`
* `Avalonia_UI.Tests/WorkflowSummaryViewStructureTests.cs`

未修改：

* `MainWindowViewModel.cs`
* `WorkflowDefinitionDraftConnectionPatcher`
* 后端 API
* localization 资源

## 3. 实现内容

在新增 connection 表单中新增：

```text
Source ComboBox
ItemsSource="{Binding WorkflowDefinitionDraftStructure.Nodes}"
SelectedItem="{Binding SelectedNewDraftConnectionSourceNode, Mode=TwoWay}"

Target ComboBox
ItemsSource="{Binding WorkflowDefinitionDraftStructure.Nodes}"
SelectedItem="{Binding SelectedNewDraftConnectionTargetNode, Mode=TwoWay}"
```

ComboBox item template 展示：

* `NodeInstanceId`
* `NodeType`

同时保留原有：

```text
NewDraftConnectionSourceNodeId
NewDraftConnectionTargetNodeId
NewDraftConnectionSourcePort
NewDraftConnectionTargetPort
```

## 4. 保持边界

已保持：

* 不新增 converter。
* 不新增 code-behind。
* 不移除手动 source / target node id 输入。
* 不移除 source / target port 手动输入。
* 不修改新增 connection 命令。
* 不修改 Nodes Card。

## 5. 测试覆盖

已更新 `WorkflowSummaryViewStructureTests`：

* 检查 ComboBox 绑定 `WorkflowDefinitionDraftStructure.Nodes`。
* 检查 source ComboBox 绑定 `SelectedNewDraftConnectionSourceNode`。
* 检查 target ComboBox 绑定 `SelectedNewDraftConnectionTargetNode`。
* 检查 draft node item template 使用 `WorkflowDefinitionDraftNode`。
* 保留既有手动输入和新增 connection 命令断言。

当前已运行：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "WorkflowSummaryViewStructureTests|MainWindowViewModelWorkflowTests"
通过：66，失败：0，跳过：0

dotnet build Avalonia_UI\Avalonia_UI.sln --no-restore
成功，警告：0，错误：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：264，失败：0，跳过：0
```

## 6. 保留项

本阶段仍未完成：

* 2.3 connection 输入体验后置复核。
* source / target port 下拉。
* port schema 深校验。
* 桌面真实截图 / 手动 smoke。

## 7. 下一小步建议

建议进入：

```text
WORKFLOW-EDIT-2.3e：
connection 输入体验后置复核。
```

复核通过后，再决定是否进入 `WORKFLOW-EDIT-2.4` 的桌面真实 smoke。
