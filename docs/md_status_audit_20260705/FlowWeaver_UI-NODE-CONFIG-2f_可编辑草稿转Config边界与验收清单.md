# FlowWeaver UI-NODE-CONFIG-2f：可编辑草稿转 Config 边界与验收清单

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：Avalonia schema 解析、可编辑草稿、输入字段 ViewModel、config 构建、Apply 命令和 WorkflowSummaryView 表单接入已经落地。
> 未实现：无本文件目标内的未实现项；专用富编辑器和更复杂字段控件仍按后续节点生态处理。
> 原因：当前实现完成了从 schema 到 draft config 写回的最小闭环。

> 文档状态：UI-NODE-CONFIG-2f 纯模型实现完成
> 当前阶段：只实现 `NodeConfigEditableDraft` 到 config JSON 的转换
> 不适用范围：XAML 动态表单、MainWindowViewModel Apply 命令、workflow JSON 写回、后端 API 修改

## 1. 阶段目标

本阶段只解决一个前置问题：

```text
把可编辑字段草稿安全转换为节点 config JSON object。
```

这个转换是后续 Apply 写回的输入，但本阶段不直接调用 `NodeConfigDraftJsonPatcher`，也不修改 `WorkflowDefinitionDraftJson`。

## 2. 已完成模型

新增模型：

```text
NodeConfigEditableDraftConfigBuildStatus
NodeConfigEditableDraftConfigFieldError
NodeConfigEditableDraftConfigResult
NodeConfigEditableDraftConfigBuilder
```

扩展模型：

```text
NodeConfigEditableDraftField.HasInputValue
```

`HasInputValue` 用于区分：

* 字段确实来自当前 config 或 default。
* 字段只是因为缺失而显示为空输入。

这样可以避免缺失的可选字段在未来 Apply 时被静默写成空字符串。

## 3. 当前支持范围

当前仅支持以下字段类型：

* `string`
* `integer`
* `number`
* `boolean`
* `enum`

转换规则：

| 类型 | 输入 | 输出 |
| --- | --- | --- |
| `string` | 原始文本 | JSON string |
| `integer` | invariant culture 整数文本 | JSON number |
| `number` | invariant culture 数字文本 | JSON number |
| `boolean` | `true` / `false`，大小写不敏感 | JSON boolean |
| `enum` | 必须命中 `EnumValues` | JSON string |

## 4. 错误边界

字段错误会返回：

```text
NodeConfigEditableDraftConfigFieldError
- FieldName
- Warning
```

当前 warning code：

| Warning | 含义 |
| --- | --- |
| `EDITABLE_CONFIG_NO_EDITABLE_FIELDS` | 没有可转换字段 |
| `EDITABLE_CONFIG_FIELD_REQUIRED_EMPTY` | 必填字段为空 |
| `EDITABLE_CONFIG_FIELD_INTEGER_INVALID` | integer 输入无法解析 |
| `EDITABLE_CONFIG_FIELD_NUMBER_INVALID` | number 输入无法解析 |
| `EDITABLE_CONFIG_FIELD_BOOLEAN_INVALID` | boolean 输入无法解析 |
| `EDITABLE_CONFIG_FIELD_ENUM_INVALID` | enum 输入不在候选值内 |
| `EDITABLE_CONFIG_FIELD_TYPE_UNSUPPORTED` | 字段类型不在当前转换范围内 |

只要存在字段错误，就不生成新的 config JSON，返回 `FieldInvalid`。

## 5. 明确未做

本阶段没有做：

* 不改 XAML。
* 不接 `MainWindowViewModel`。
* 不新增 Apply 命令。
* 不调用 `NodeConfigDraftJsonPatcher`。
* 不写回 `WorkflowDefinitionDraftJson`。
* 不改变 Validate / Save / revision conflict 行为。
* 不做 array / object / unsupported 的结构化编辑。

## 6. 测试结果

新增测试：

```text
NodeConfigEditableDraftConfigBuilderTests
```

覆盖：

* string / integer / number / boolean / enum 正常转换。
* 缺失可选字段不写入 config JSON。
* 显式空字符串可以保留。
* required 空值拒绝。
* integer / number / boolean / enum 非法输入拒绝。
* unsupported editable field type 拒绝。
* 无字段 draft 返回 DraftUnsupported。

验证结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "NodeConfigEditableDraftConfigBuilderTests|NodeConfigEditableDraftBuilderTests|NodeConfigDraftJsonPatcherTests"
通过：19，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：205，失败：0，跳过：0
```

## 7. 下一小步建议

下一步不建议直接做 XAML 动态表单。

更稳的小步是：

```text
UI-NODE-CONFIG-2g：
先分析 MainWindowViewModel 接入边界，
确认如何持有 SelectedNodeConfigEditableDraft、
如何在选中节点/草稿 JSON/schema 变化时刷新、
以及 Apply 命令是否已有足够输入。
```

如果进入代码，建议优先只接 ViewModel 只读/内部状态，不立刻暴露按钮。
