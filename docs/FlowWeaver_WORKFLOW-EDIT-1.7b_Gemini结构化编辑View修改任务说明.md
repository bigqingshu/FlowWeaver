# FlowWeaver WORKFLOW-EDIT-1.7b：Gemini 结构化编辑 View 修改任务说明

> 文档状态：WORKFLOW-EDIT-1.7b 任务说明完成
> 当前阶段：交给 Gemini 做纯 View 层结构化编辑表单接入前的任务说明
> 不适用范围：本小步不修改 XAML、不修改 ViewModel、不修改模型、不运行 Gemini

## 1. 给 Gemini 的任务目标

请只修改：

```text
Avalonia_UI/Views/Components/Workflow/WorkflowSummaryView.axaml
```

目标是在现有 Workflow Summary 页面中增加最小结构化编辑表单：

```text
Add node
Delete node
Add connection
Delete connection
```

第一版只做表单，不做画布、不做拖拽、不做自动布局。

## 2. 严格禁止

Gemini 不得修改：

```text
Avalonia_UI/ViewModels/MainWindowViewModel.cs
Avalonia_UI/Models/
Avalonia_UI/Localization/
Avalonia_UI.Tests/
后端 Python 代码
```

Gemini 不得引入：

```text
Converters
code-behind 逻辑
新依赖
新 ResourceDictionary
图形画布
拖拽连线
自动布局
```

Gemini 不得改变：

```text
WorkflowDefinitionDetail.Nodes 的现有 ListBox ItemsSource
WorkflowDefinitionDetail.Connections 的现有 ListBox ItemsSource
SelectedWorkflowDefinitionNode 的现有节点配置选择行为
SelectedNodeConfigEditableInputFields 的节点配置表单行为
```

## 3. 可用绑定

### 文本属性

```text
StructuredEditSectionText
AddNodeText
DeleteNodeText
NodeInstanceIdText
NodeTypeText
NodeVersionText
DisplayNameText
ConfigJsonText
AddConnectionText
DeleteConnectionText
ConnectionIdText
SourceNodeText
SourcePortText
TargetNodeText
TargetPortText
```

### 节点新增

```text
NewDraftNodeInstanceId
NewDraftNodeType
NewDraftNodeVersion
NewDraftNodeDisplayName
NewDraftNodeConfigJson
AddWorkflowDefinitionDraftNodeCommand
```

### 节点删除

```text
SelectedWorkflowDefinitionDraftNodeInstanceId
DeleteWorkflowDefinitionDraftNodeCommand
```

### Connection 新增

```text
NewDraftConnectionId
NewDraftConnectionSourceNodeId
NewDraftConnectionSourcePort
NewDraftConnectionTargetNodeId
NewDraftConnectionTargetPort
AddWorkflowDefinitionDraftConnectionCommand
```

### Connection 删除

```text
SelectedWorkflowDefinitionDraftConnectionId
DeleteWorkflowDefinitionDraftConnectionCommand
```

## 4. Nodes Card 修改建议

当前 Nodes Card 的根 Grid 是：

```xml
<Grid RowDefinitions="Auto,*,Auto,Auto" RowSpacing="10">
```

建议改为：

```xml
<Grid RowDefinitions="Auto,*,Auto,Auto,Auto" RowSpacing="10">
```

在现有节点配置表单之后增加：

```text
Grid.Row="4"
```

结构建议：

```text
StackPanel
  TextBlock StructuredEditSectionText
  Grid Add node form
  Grid Delete node form
```

绑定建议：

```xml
Text="{Binding NewDraftNodeInstanceId, Mode=TwoWay, UpdateSourceTrigger=PropertyChanged}"
Text="{Binding NewDraftNodeType, Mode=TwoWay, UpdateSourceTrigger=PropertyChanged}"
Text="{Binding NewDraftNodeVersion, Mode=TwoWay, UpdateSourceTrigger=PropertyChanged}"
Text="{Binding NewDraftNodeDisplayName, Mode=TwoWay, UpdateSourceTrigger=PropertyChanged}"
Text="{Binding NewDraftNodeConfigJson, Mode=TwoWay, UpdateSourceTrigger=PropertyChanged}"
Command="{Binding AddWorkflowDefinitionDraftNodeCommand}"

Text="{Binding SelectedWorkflowDefinitionDraftNodeInstanceId, Mode=TwoWay, UpdateSourceTrigger=PropertyChanged}"
Command="{Binding DeleteWorkflowDefinitionDraftNodeCommand}"
```

## 5. Connections Card 修改建议

当前 Connections Card 的根 Grid 是：

```xml
<Grid RowDefinitions="Auto,*" RowSpacing="10">
```

建议改为：

```xml
<Grid RowDefinitions="Auto,*,Auto" RowSpacing="10">
```

在现有 connections ListBox 之后增加：

```text
Grid.Row="2"
```

结构建议：

```text
StackPanel
  TextBlock StructuredEditSectionText
  Grid Add connection form
  Grid Delete connection form
```

绑定建议：

```xml
Text="{Binding NewDraftConnectionId, Mode=TwoWay, UpdateSourceTrigger=PropertyChanged}"
Text="{Binding NewDraftConnectionSourceNodeId, Mode=TwoWay, UpdateSourceTrigger=PropertyChanged}"
Text="{Binding NewDraftConnectionSourcePort, Mode=TwoWay, UpdateSourceTrigger=PropertyChanged}"
Text="{Binding NewDraftConnectionTargetNodeId, Mode=TwoWay, UpdateSourceTrigger=PropertyChanged}"
Text="{Binding NewDraftConnectionTargetPort, Mode=TwoWay, UpdateSourceTrigger=PropertyChanged}"
Command="{Binding AddWorkflowDefinitionDraftConnectionCommand}"

Text="{Binding SelectedWorkflowDefinitionDraftConnectionId, Mode=TwoWay, UpdateSourceTrigger=PropertyChanged}"
Command="{Binding DeleteWorkflowDefinitionDraftConnectionCommand}"
```

## 6. 视觉约束

请保持现有页面风格：

* 不新增嵌套 Card。
* 不使用大标题。
* 不使用说明性长文案。
* 表单保持紧凑。
* Label 使用现有 `TextSecondaryBrush`。
* 输入框和按钮使用现有默认样式。
* 多行 config JSON 可使用 `TextBox AcceptsReturn="True"`，高度控制在紧凑范围。
* 不让新增区域挤压到无法浏览现有节点/连接列表。

## 7. 验收建议

Gemini 完成后，请 Codex 复核：

```text
dotnet build Avalonia_UI\Avalonia_UI.sln --no-restore
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "WorkflowSummaryViewStructureTests|MainWindowViewModelWorkflowTests|MainWindowViewModelLocalizationTests"
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
```

并检查：

* 新增 XAML 只绑定已有属性和命令。
* 没有新增 converter。
* 没有改 ViewModel / Models / Localization / Tests。
* 没有破坏节点配置表单。
* 没有把 loaded detail selection 和 draft selection 混用。

## 8. 下一步

Gemini 可以根据本文进入：

```text
WORKFLOW-EDIT-1.7c：
WorkflowSummaryView 结构化编辑表单纯 View 接入。
```
