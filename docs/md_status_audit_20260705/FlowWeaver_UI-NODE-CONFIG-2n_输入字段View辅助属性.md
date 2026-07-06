# FlowWeaver UI-NODE-CONFIG-2n：输入字段 View 辅助属性

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：Avalonia schema 解析、可编辑草稿、输入字段 ViewModel、config 构建、Apply 命令和 WorkflowSummaryView 表单接入已经落地。
> 未实现：无本文件目标内的未实现项；专用富编辑器和更复杂字段控件仍按后续节点生态处理。
> 原因：当前实现完成了从 schema 到 draft config 写回的最小闭环。

> 文档状态：UI-NODE-CONFIG-2n 代码实现完成
> 当前阶段：只为节点配置输入字段补充 XAML 友好只读属性
> 不适用范围：XAML 表单、Apply 按钮显示、后端 API 修改、保存 workflow

## 1. 阶段目标

本阶段为 `NodeConfigEditableFieldInputViewModel` 补充 View 层可直接绑定的辅助属性，减少 Gemini 后续写 XAML 时对 converter / code-behind 的依赖。

## 2. 已完成内容

新增辅助属性：

```text
DisplayLabel
TypeText
RequiredText
IsTextInput
IsEnumInput
IsBooleanInput
BooleanValues
HasWarnings
WarningText
```

用途：

| 属性 | 用途 |
| --- | --- |
| `DisplayLabel` | 优先显示 title，缺失时显示 name |
| `TypeText` | 显示字段类型 |
| `RequiredText` | 必填标记 |
| `IsTextInput` | string / integer / number 使用文本输入 |
| `IsEnumInput` | enum 使用 ComboBox |
| `IsBooleanInput` | boolean 使用 ComboBox 或后续 Toggle |
| `BooleanValues` | 提供 `true` / `false` 候选值 |
| `HasWarnings` | 控制 warning 显示 |
| `WarningText` | 显示 warning code |

## 3. 测试覆盖

补充：

```text
NodeConfigEditableFieldInputViewModelTests
```

覆盖：

* title fallback 到 display label。
* enum / text / boolean 类型标记。
* required 标记。
* warning 展示文本。
* boolean 候选值。

## 4. 明确未做

本阶段没有做：

* 不改 XAML。
* 不新增按钮。
* 不新增 converter。
* 不新增 code-behind。
* 不改变 Apply / Validate / Save 语义。

## 5. 验证结果

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "NodeConfigEditableFieldInputViewModelTests|NodeConfigEditableFieldInputConfigBuilderTests"
通过：5，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：214，失败：0，跳过：0
```

## 6. 下一小步建议

下一步可以进入：

```text
UI-NODE-CONFIG-2o：
WorkflowSummaryView.axaml 节点配置表单最小接入，
只改 View，绑定 SelectedNodeConfigEditableInputFields 和 ApplySelectedNodeConfigDraftCommand。
```

如果交给 Gemini，应先阅读：

```text
docs/FlowWeaver_UI-NODE-CONFIG-2m_节点配置表单View协作说明.md
```
