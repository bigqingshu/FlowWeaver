# FlowWeaver UI-NODE-CONFIG-2j：输入字段 ViewModel 状态接入

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：Avalonia schema 解析、可编辑草稿、输入字段 ViewModel、config 构建、Apply 命令和 WorkflowSummaryView 表单接入已经落地。
> 未实现：无本文件目标内的未实现项；专用富编辑器和更复杂字段控件仍按后续节点生态处理。
> 原因：当前实现完成了从 schema 到 draft config 写回的最小闭环。

> 文档状态：UI-NODE-CONFIG-2j 代码实现完成
> 当前阶段：只在 ViewModel 层新增可变输入字段状态
> 不适用范围：XAML 动态表单、Apply 按钮、workflow JSON 写回、后端 API 修改

## 1. 阶段目标

本阶段在只读 editable draft 快照之外，新增用户可变输入字段状态：

```text
SelectedNodeConfigEditableDraft
→ SelectedNodeConfigEditableInputFields
```

当前仍不修改界面，不新增按钮，不调用 patcher。

## 2. 已完成内容

新增：

```text
NodeConfigEditableFieldInputViewModel
```

字段能力：

* `Name`
* `Type`
* `Title`
* `Required`
* `InputValue`
* `OriginalInputValue`
* `HasInputValue`
* `OriginalHasInputValue`
* `EnumValues`
* `Warnings`
* `IsDirty`
* `ToEditableDraftField()`

`MainWindowViewModel` 新增：

```text
SelectedNodeConfigEditableInputFields
HasSelectedNodeConfigEditableInputFields
```

`RefreshSelectedNodeConfigDraftState()` 会在 editable draft 可用时重建输入字段集合。

## 3. 当前刷新策略

第一版采用保守策略：

```text
只要 selected node / workflow draft JSON / schema 状态刷新，
就从最新 editable draft 重建 input fields。
```

这能保证显示状态和当前 `WorkflowDefinitionDraftJson` 一致，避免后续 Apply 基于过期输入。

## 4. 测试覆盖

新增：

```text
NodeConfigEditableFieldInputViewModelTests
```

补充：

```text
MainWindowViewModelWorkflowTests
```

覆盖：

* 输入字段能跟踪 dirty 状态。
* 输入字段能转换回 `NodeConfigEditableDraftField`。
* workflow 切换会清空输入字段集合。
* schema 刷新后会生成输入字段集合。
* 修改输入字段不影响当前 workflow JSON。
* selected node 切换会重建输入字段。
* `WorkflowDefinitionDraftJson` 手工变化会重建输入字段并清空 dirty。

## 5. 明确未做

本阶段没有做：

* 不改 XAML。
* 不新增 Apply 命令。
* 不调用 `NodeConfigEditableDraftConfigBuilder`。
* 不调用 `NodeConfigDraftJsonPatcher`。
* 不写回 `WorkflowDefinitionDraftJson`。
* 不做字段错误回填。

## 6. 验证结果

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "NodeConfigEditableFieldInputViewModelTests|MainWindowViewModelWorkflowTests"
通过：40，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：207，失败：0，跳过：0
```

## 7. 下一小步建议

下一步建议：

```text
UI-NODE-CONFIG-2k：
新增输入字段集合到 config JSON 的适配层，
复用 NodeConfigEditableDraftConfigBuilder，
仍不接 Apply。
```

完成后再进入：

```text
UI-NODE-CONFIG-2l：
ApplySelectedNodeConfigDraftCommand 最小接入。
```
