# FlowWeaver UI-NODE-EDITOR-7 Gemini 只读展示任务说明

> 审核状态（2026-07-05）：部分已实现 / 专用编辑器后置
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：节点目录、内置节点可见性、JsonFallback 编辑入口和后续配置 schema 表单主线已经落地。
> 未实现：针对每类节点的专用富编辑器未实现，当前 BuiltinNodeEditors 仍以 JsonFallback 为主。
> 原因：先用 schema/JSON 路线保证可编辑闭环，专用编辑器需要在真实业务节点稳定后再做。

## 目标

在 Avalonia 的 Workflow 定义只读摘要里，展示每个节点当前使用的节点编辑器状态。

本阶段只允许做只读展示，不允许进入节点编辑、配置表单或拖拽画布。

## 当前代码事实

已完成的 Codex 前置模型：

```text
WorkflowDefinitionNodeListItemViewModel
  NodeEditorResolution
  NodeEditorStatusText
  HasRegisteredNodeEditor
  UsesJsonFallback
```

当前目标 View：

```text
Avalonia_UI/Views/Components/Workflow/WorkflowSummaryView.axaml
```

当前节点列表位于 `WorkflowSummaryView.axaml` 的 Nodes Card：

```text
ItemsSource="{Binding WorkflowDefinitionDetail.Nodes}"
DataTemplate DataType="vm:WorkflowDefinitionNodeListItemViewModel"
```

当前已展示字段：

```text
NodeInstanceId
EnabledText
TypeText
DisplayNameText
ConfigJson
```

## 允许修改范围

建议只修改：

```text
Avalonia_UI/Views/Components/Workflow/WorkflowSummaryView.axaml
```

如确实需要布局结构测试，可以只补充不涉及视觉断言的结构测试。

## 建议展示方式

在每个节点条目中增加一行只读编辑器状态。

推荐最小文案：

```text
Editor: {NodeEditorStatusText}
```

绑定字段：

```xml
Text="{Binding NodeEditorStatusText}"
```

如果需要同时表达是否回退 JSON，可优先使用现有状态文本，不要在 XAML 中根据 bool 拼接业务文案。

## 布局建议

当前节点条目 Grid 为：

```xml
<Grid ColumnDefinitions="*,Auto"
      RowDefinitions="Auto,Auto,Auto"
      ColumnSpacing="12"
      Margin="8">
```

可改为：

```xml
RowDefinitions="Auto,Auto,Auto,Auto"
```

并新增：

```xml
<TextBlock Grid.Row="2"
           Grid.ColumnSpan="2"
           Text="{Binding NodeEditorStatusText}"
           FontSize="12"
           TextTrimming="CharacterEllipsis"
           Foreground="{DynamicResource TextSecondaryBrush}"/>
```

原 `ConfigJson` 建议下移到 `Grid.Row="3"`。

## 禁止事项

不得新增：

* 编辑按钮。
* 配置按钮。
* 打开编辑器命令。
* 节点配置表单。
* JSON Schema renderer。
* 拖拽画布。
* 节点添加/删除入口。
* 保存逻辑。
* `ListNodeDefinitionsAsync` 调用。
* 外部 DLL / 模块扫描。

不得修改：

* `WorkflowDefinitionDraftJson`。
* Validate / Save 按钮行为。
* revision conflict 处理。
* 工作流启动、取消、运行监控逻辑。
* 后端 API。

## 验收要求

完成后请执行：

```powershell
dotnet test "Avalonia_UI\Avalonia_UI.sln" --no-restore
```

并确认：

* Workflow 节点列表仍能显示。
* 已加载 WorkflowDefinition 后，每个节点有编辑器状态文本。
* `ConfigJson` 仍显示。
* 没有新增按钮或可编辑控件。
* 没有改动后端或 API Client。

## 后续阶段

如果本阶段完成且无回归，下一步再由 Codex 复核是否需要：

```text
UI-NODE-EDITOR-8：
只读展示复核与本地化策略分析。
```
