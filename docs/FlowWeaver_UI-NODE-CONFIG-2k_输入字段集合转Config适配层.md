# FlowWeaver UI-NODE-CONFIG-2k：输入字段集合转 Config 适配层

> 文档状态：UI-NODE-CONFIG-2k 代码实现完成
> 当前阶段：只新增输入字段集合到 config JSON 的适配层
> 不适用范围：XAML 动态表单、Apply 按钮、workflow JSON 写回、后端 API 修改

## 1. 阶段目标

本阶段把 2j 的可变输入字段集合转换为 2f 的 config JSON 构建输入：

```text
SelectedNodeConfigEditableInputFields
→ NodeConfigEditableDraft
→ NodeConfigEditableDraftConfigBuilder
→ NodeConfigEditableDraftConfigResult
```

当前仍不调用 `NodeConfigDraftJsonPatcher`，不修改 `WorkflowDefinitionDraftJson`。

## 2. 已完成内容

新增：

```text
NodeConfigEditableFieldInputConfigBuilder
```

能力：

* 接收 `nodeInstanceId` 和 `NodeConfigEditableFieldInputViewModel` 集合。
* 将输入字段转换回 `NodeConfigEditableDraftField`。
* 复用 `NodeConfigEditableDraftConfigBuilder` 做类型解析和字段错误。
* 返回统一的 `NodeConfigEditableDraftConfigResult`。

## 3. 测试覆盖

新增：

```text
NodeConfigEditableFieldInputConfigBuilderTests
```

覆盖：

* 输入字段集合能生成 config JSON。
* 用户修改后的 `InputValue` 会进入 config JSON。
* integer / enum 等字段错误会透传。
* 空输入字段集合会返回 `DraftUnsupported`。

## 4. 明确未做

本阶段没有做：

* 不改 XAML。
* 不新增 Apply 命令。
* 不调用 `NodeConfigDraftJsonPatcher`。
* 不写回 `WorkflowDefinitionDraftJson`。
* 不改变 Validate / Save / revision conflict 行为。
* 不做字段错误回填到 UI。

## 5. 验证结果

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "NodeConfigEditableFieldInputConfigBuilderTests|NodeConfigEditableFieldInputViewModelTests|NodeConfigEditableDraftConfigBuilderTests"
通过：11，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：210，失败：0，跳过：0
```

## 6. 下一小步建议

下一步可以进入：

```text
UI-NODE-CONFIG-2l：
ApplySelectedNodeConfigDraftCommand 最小接入，
只把输入字段集合构建出的 config JSON patch 回 WorkflowDefinitionDraftJson。
```

2l 仍不做 XAML 动态表单；按钮是否显示给用户可再由 Gemini/View 层后续接入。
