# FlowWeaver WORKFLOW-EDIT-2.2d：新增节点 View 最小接入

> 文档状态：WORKFLOW-EDIT-2.2d 已完成
> 当前阶段：结构化编辑节点新增体验收口
> 不适用范围：ViewModel 改动、模型改动、后端 API 改动、port schema 深校验、图形画布

## 1. 阶段目标

在 `WorkflowSummaryView.axaml` 的新增节点表单中接入 node catalog 选择控件：

```text
NodeDefinitions
-> SelectedNewDraftNodeDefinition
```

并继续保留 `NewDraftNodeType` 手动输入。

## 2. 修改范围

已修改：

* `Avalonia_UI/Views/Components/Workflow/WorkflowSummaryView.axaml`
* `Avalonia_UI.Tests/WorkflowSummaryViewStructureTests.cs`

未修改：

* `MainWindowViewModel.cs`
* patcher
* 后端 API
* localization 资源

## 3. 实现内容

在新增节点表单的 node type 输入区域新增：

```text
ComboBox
ItemsSource="{Binding NodeDefinitions}"
SelectedItem="{Binding SelectedNewDraftNodeDefinition, Mode=TwoWay}"
```

ComboBox item template 展示：

* `DisplayNameText`
* `TypeText`

同时保留原有：

```text
TextBox
Text="{Binding NewDraftNodeType, Mode=TwoWay, UpdateSourceTrigger=PropertyChanged}"
```

## 4. 保持边界

已保持：

* 不新增 converter。
* 不新增 code-behind。
* 不移除手动 node type 输入。
* 不移除手动 node instance id 输入。
* 不改变新增节点命令。
* 不修改 Connections Card。

## 5. 测试覆盖

已更新 `WorkflowSummaryViewStructureTests`：

* 检查 ComboBox 绑定 `NodeDefinitions`。
* 检查 ComboBox 绑定 `SelectedNewDraftNodeDefinition`。
* 检查节点目录 item template 使用 `NodeDefinitionListItemViewModel`。
* 保留既有手动输入和新增节点命令断言。

当前已运行：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "WorkflowSummaryViewStructureTests|MainWindowViewModelWorkflowTests"
通过：63，失败：0，跳过：0

dotnet build Avalonia_UI\Avalonia_UI.sln --no-restore
成功，警告：0，错误：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：261，失败：0，跳过：0
```

## 6. 保留项

本阶段仍未完成：

* 桌面真实截图 / 手动 smoke。
* 2.2 总体后置复核。
* connection source / target 下拉选择。
* connection id 自动建议。
* port 下拉与端口 schema 深校验。

## 7. 下一小步建议

建议进入：

```text
WORKFLOW-EDIT-2.2e：
node type 与 node instance id 输入体验后置复核。
```

复核通过后，再决定进入 `WORKFLOW-EDIT-2.3` 的 connection 输入体验收口。
