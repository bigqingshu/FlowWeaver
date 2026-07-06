# FlowWeaver WORKFLOW-EDIT-1.7：结构化编辑 View 协作说明

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：结构化只读解析、节点新增/删除、connection 新增/删除、ViewModel 命令、View 接入、用户友好 warning/error、节点/connection 输入体验和 smoke 复核已经落地。
> 未实现：自由画布、拖拽连线、完整撤销/重做和复杂 DAG 自动重排未在本阶段实现。
> 原因：这些能力超出结构化编辑最小闭环，已作为后续体验方向保留。

> 文档状态：WORKFLOW-EDIT-1.7 协作说明完成
> 当前阶段：准备将结构化编辑命令暴露到 Avalonia View
> 不适用范围：本小步不修改 XAML、不修改 ViewModel、不调用 Gemini

## 1. 当前可用 ViewModel 能力

当前 `MainWindowViewModel` 已提供：

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

这些命令都只写回：

```text
WorkflowDefinitionDraftJson
```

## 2. 当前不建议 Gemini 立即改 XAML 的原因

目前新增结构化编辑区域缺少 View 需要的本地化文本属性，例如：

```text
Add node
Delete node
Node instance id
Node type
Node version
Display name
Config JSON
Add connection
Delete connection
Connection id
Source node
Source port
Target node
Target port
```

如果直接让 Gemini 修改 XAML，会有两个坏结果：

* 写死英文或中文文本，破坏现有 L10N 路线。
* 让 Gemini 修改 ViewModel 或资源文件，扩大纯 View 协作范围。

因此，进入 Gemini View 修改前，建议先由 Codex 做一个极小前置小步：

```text
WORKFLOW-EDIT-1.7a：
结构化编辑 View 辅助文本属性。
```

## 3. Gemini 后续允许修改范围

等 1.7a 完成后，Gemini 可以只改：

```text
Avalonia_UI/Views/Components/Workflow/WorkflowSummaryView.axaml
```

第一版建议只在现有 Nodes / Connections Card 内增加紧凑表单区。

不允许 Gemini 修改：

```text
Avalonia_UI/ViewModels/MainWindowViewModel.cs
Avalonia_UI/Models/
Avalonia_UI/Localization/
Avalonia_UI.Tests/
后端 Python 代码
```

## 4. 建议 View 布局边界

第一版不做画布，只做表单。

### Nodes Card

建议新增两个区域：

```text
Add node form
Delete node form
```

绑定建议：

```text
TextBox Text="{Binding NewDraftNodeInstanceId, Mode=TwoWay, UpdateSourceTrigger=PropertyChanged}"
TextBox Text="{Binding NewDraftNodeType, Mode=TwoWay, UpdateSourceTrigger=PropertyChanged}"
TextBox Text="{Binding NewDraftNodeVersion, Mode=TwoWay, UpdateSourceTrigger=PropertyChanged}"
TextBox Text="{Binding NewDraftNodeDisplayName, Mode=TwoWay, UpdateSourceTrigger=PropertyChanged}"
TextBox Text="{Binding NewDraftNodeConfigJson, Mode=TwoWay, UpdateSourceTrigger=PropertyChanged}"
Button Command="{Binding AddWorkflowDefinitionDraftNodeCommand}"

TextBox Text="{Binding SelectedWorkflowDefinitionDraftNodeInstanceId, Mode=TwoWay, UpdateSourceTrigger=PropertyChanged}"
Button Command="{Binding DeleteWorkflowDefinitionDraftNodeCommand}"
```

### Connections Card

建议新增两个区域：

```text
Add connection form
Delete connection form
```

绑定建议：

```text
TextBox Text="{Binding NewDraftConnectionId, Mode=TwoWay, UpdateSourceTrigger=PropertyChanged}"
TextBox Text="{Binding NewDraftConnectionSourceNodeId, Mode=TwoWay, UpdateSourceTrigger=PropertyChanged}"
TextBox Text="{Binding NewDraftConnectionSourcePort, Mode=TwoWay, UpdateSourceTrigger=PropertyChanged}"
TextBox Text="{Binding NewDraftConnectionTargetNodeId, Mode=TwoWay, UpdateSourceTrigger=PropertyChanged}"
TextBox Text="{Binding NewDraftConnectionTargetPort, Mode=TwoWay, UpdateSourceTrigger=PropertyChanged}"
Button Command="{Binding AddWorkflowDefinitionDraftConnectionCommand}"

TextBox Text="{Binding SelectedWorkflowDefinitionDraftConnectionId, Mode=TwoWay, UpdateSourceTrigger=PropertyChanged}"
Button Command="{Binding DeleteWorkflowDefinitionDraftConnectionCommand}"
```

## 5. Gemini 必须保持的限制

Gemini 修改 View 时必须保持：

* 不引入 converters。
* 不新增 code-behind 逻辑。
* 不修改 DataContext。
* 不修改现有 ListBox 的 ItemsSource。
* 不把 loaded detail selection 和 draft selection 绑定到同一个属性。
* 不做画布、不做拖拽、不做自动布局。
* 不新增外部依赖。
* 不修改现有节点配置表单行为。

## 6. 下一小步建议

建议下一步先由 Codex 执行：

```text
WORKFLOW-EDIT-1.7a：
结构化编辑 View 辅助文本属性。
```

范围：

* 新增本地化资源 key。
* 新增 MainWindowViewModel 文本属性。
* 接入语言切换刷新。
* 增加最小测试。
* 不修改 XAML。

1.7a 完成后，再把本文作为 Gemini 的 View 修改依据。
