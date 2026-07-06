# FlowWeaver UI-NODE-CONFIG-2m：节点配置表单 View 协作说明

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：Avalonia schema 解析、可编辑草稿、输入字段 ViewModel、config 构建、Apply 命令和 WorkflowSummaryView 表单接入已经落地。
> 未实现：无本文件目标内的未实现项；专用富编辑器和更复杂字段控件仍按后续节点生态处理。
> 原因：当前实现完成了从 schema 到 draft config 写回的最小闭环。

> 文档状态：UI-NODE-CONFIG-2m View 协作说明完成
> 当前阶段：只整理给 Gemini 的 XAML 接入边界
> 不适用范围：修改 ViewModel、修改后端 API、修改 Apply 语义、保存 workflow、动态插件系统

## 1. 当前可用 ViewModel 契约

当前 `MainWindowViewModel` 已经提供节点配置编辑所需的最小绑定入口：

```text
SelectedWorkflowDefinitionNode
SelectedNodeConfigDraft
SelectedNodeConfigEditableDraft
SelectedNodeConfigEditableDraftMessage
SelectedNodeConfigEditableInputFields
HasSelectedNodeConfigEditableInputFields
ApplySelectedNodeConfigDraftCommand
SelectedNodeConfigDraftSummaryText
WorkflowDefinitionValidationMessage
WorkflowDefinitionValidationErrorMessage
```

输入字段项类型：

```text
NodeConfigEditableFieldInputViewModel
- Name
- Type
- Title
- Required
- InputValue
- OriginalInputValue
- HasInputValue
- OriginalHasInputValue
- EnumValues
- Warnings
- IsDirty
```

当前 Apply 语义：

```text
SelectedNodeConfigEditableInputFields
→ config JSON
→ patch 当前选中节点 config
→ 设置 WorkflowDefinitionDraftJson
```

Apply 不调用 Validate / Save / 后端 API。

## 2. 建议修改文件

Gemini 第一小步只建议修改：

```text
Avalonia_UI/Views/Components/Workflow/WorkflowSummaryView.axaml
```

原因：

* 该文件已经承载 workflow definition details、nodes 和 connections。
* 节点列表已经绑定 `SelectedWorkflowDefinitionNode`。
* 节点卡片底部已有 `SelectedNodeConfigDraftSummaryText`。
* 新增节点配置表单不需要修改 `MainWindow.axaml` 或 `WorkflowPage.axaml`。

暂不建议修改：

```text
Avalonia_UI/ViewModels/MainWindowViewModel.cs
Avalonia_UI/Views/Pages/WorkflowPage.axaml
Avalonia_UI/Views/MainWindow.axaml
后端 Python 代码
API client
```

## 3. 第一版 View 接入位置

建议在 `WorkflowSummaryView.axaml` 的 Nodes Card 内加入节点配置编辑区。

当前位置：

```xml
<TextBlock Grid.Row="2"
           Text="{Binding SelectedNodeConfigDraftSummaryText}"
           TextWrapping="Wrap"
           Foreground="{DynamicResource TextSecondaryBrush}"/>
```

建议将 Nodes Card 的底部区域扩展为：

```text
summary text
editable field list
Apply button
```

不要把它做成独立浮层、弹窗或新的页面；第一版应保持在节点列表下方。

## 4. 推荐绑定

字段列表：

```text
ItemsSource="{Binding SelectedNodeConfigEditableInputFields}"
IsVisible="{Binding HasSelectedNodeConfigEditableInputFields}"
```

字段行 DataTemplate：

```text
x:DataType="vm:NodeConfigEditableFieldInputViewModel"
```

字段显示：

```text
Name      → 字段主标签
Type      → 字段类型辅助文本
Required  → 可作为必填标记
Warnings  → 第一版可暂不展示，或只显示简短 warning code
IsDirty   → 可作为轻量状态标记
```

字段输入：

```text
InputValue
Mode=TwoWay
UpdateSourceTrigger=PropertyChanged
```

Apply 按钮：

```text
Command="{Binding ApplySelectedNodeConfigDraftCommand}"
```

按钮位置建议放在字段列表下方右侧，不要替代现有 Validate / Save。

## 5. 控件选择边界

当前 ViewModel 还没有这些 XAML 友好辅助属性：

```text
IsEnum
IsBoolean
IsTextInput
DisplayLabel
RequiredText
WarningText
```

因此，Gemini 第一小步有两种安全选择：

### 方案 A：最稳

所有字段先使用 `TextBox` 绑定 `InputValue`。

优点：

* 不需要新增 converter。
* 不需要改 ViewModel。
* string / integer / number / boolean 都能输入。
* enum 也可以先输入候选文本。

缺点：

* enum 不是 ComboBox。
* boolean 不是 Toggle / CheckBox。
* 交互体验只是可用，不是最终形态。

### 方案 B：稍进一步

只对 enum 使用：

```text
ComboBox ItemsSource="{Binding EnumValues}"
SelectedItem="{Binding InputValue, Mode=TwoWay}"
```

其他类型仍使用 `TextBox`。

注意：

* 不要引入 converter。
* 不要写 code-behind。
* 不要修改 ViewModel。
* 如果 XAML 条件显示做不到稳定编译，应退回方案 A。

## 6. 明确禁止事项

Gemini 不应在本阶段做：

* 不改 `MainWindowViewModel.cs`。
* 不新增 converter。
* 不新增 code-behind 逻辑。
* 不调用后端 API。
* 不修改 Validate / Save 按钮行为。
* 不让 Apply 调用 Save。
* 不清空 revision conflict。
* 不移动 WorkflowPage 三列结构。
* 不重设计整个 Workflow 页面。
* 不改 `MainWindow.axaml`。
* 不做外部插件/模块化。

## 7. 视觉边界

保持现有视觉风格：

* 使用现有 `Border Classes="Card"` 内部布局，不新增嵌套 Card。
* 控件间距保持 `RowSpacing="8"` 到 `10"`。
* 字段列表高度要受控，避免挤压 connections 区域。
* 文字使用现有 `TextPrimaryBrush` / `TextSecondaryBrush` / `TextErrorBrush`。
* Apply 按钮不要做成主保存按钮，避免和 Save 混淆。
* 不新增说明性大段文案。

## 8. 验收建议

Gemini 完成 View 修改后，Codex 需要核验：

```text
dotnet build Avalonia_UI\Avalonia_UI.sln --no-restore
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
```

人工/截图核验：

* Workflow 页面仍是三列布局。
* 加载 workflow 和 node definitions 后，节点配置字段显示在 Nodes Card 底部。
* 修改字段后点击 Apply，Draft JSON 中对应节点 config 改变。
* Apply 后不会自动 Save。
* Validate / Save 原按钮仍可用。
* revision conflict 状态下 Apply 按钮不可用。

## 9. 下一小步建议

如果先由 Codex 继续而不是交给 Gemini，建议下一步是：

```text
UI-NODE-CONFIG-2n：
为 NodeConfigEditableFieldInputViewModel 补充 View 友好辅助属性和测试，
例如 DisplayLabel / IsEnum / IsBoolean / IsTextInput。
```

这样 Gemini 后续可以更稳地做 enum ComboBox 和 boolean 控件。
