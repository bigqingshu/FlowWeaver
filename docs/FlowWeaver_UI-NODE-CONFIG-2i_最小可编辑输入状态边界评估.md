# FlowWeaver UI-NODE-CONFIG-2i：最小可编辑输入状态边界评估

> 文档状态：UI-NODE-CONFIG-2i 边界评估完成
> 当前阶段：只确认用户可编辑输入状态的归属和后续实施顺序
> 不适用范围：XAML 动态表单、Apply 按钮、workflow JSON 写回、后端 API 修改

## 1. 当前事实

当前已经具备：

* `SelectedNodeConfigDraft`
* `SelectedNodeConfigEditableDraft`
* `NodeConfigEditableDraftConfigBuilder`
* `NodeConfigDraftJsonPatcher`

但 `SelectedNodeConfigEditableDraft` 当前仍是从 `WorkflowDefinitionDraftJson` 和 schema 派生的快照。

它适合表达：

```text
当前节点有哪些可编辑字段
当前字段值/默认值是什么
enum 候选值是什么
字段当前是否有 warning
```

它不适合直接表达：

```text
用户正在编辑但尚未 Apply 的输入值
字段输入是否 dirty
字段输入的本地校验错误
用户清空字段是“删除字段”还是“显式空字符串”
```

因此不建议直接让 UI 双向绑定 `NodeConfigEditableDraftField.InputValue` 后立刻接 Apply。

## 2. 风险点

如果直接把 `NodeConfigEditableDraft` 当作可变输入状态，会出现几个问题：

| 风险 | 说明 |
| --- | --- |
| 快照和用户输入混淆 | draft 重新刷新时可能覆盖用户未 Apply 的输入 |
| dirty 难以判断 | 无法区分来自 workflow JSON 的值和用户修改后的值 |
| 空值语义不清 | 可选 string 清空是省略字段还是写入空字符串，需要明确 |
| schema 变化难处理 | node definitions 刷新后是否保留旧输入需要有规则 |
| Apply 错误难显示 | 字段级错误需要能回填到具体输入字段 |

## 3. 推荐状态分层

建议后续分成三层：

```text
SelectedNodeConfigDraft
    只读解析结果，来自 workflow JSON + schema

SelectedNodeConfigEditableDraft
    只读可编辑字段快照，来自 draft

SelectedNodeConfigEditableInputFields
    用户可变输入状态，来自 editable draft，但独立保存
```

第三层建议用 ViewModel 专用类型，而不是继续扩大纯 record：

```text
NodeConfigEditableFieldInputViewModel
- Name
- Type
- Title
- Required
- InputValue
- OriginalInputValue
- HasInputValue
- EnumValues
- WarningText / ErrorCode
- IsDirty
```

第一版可以只支持标量字段：

* `string`
* `integer`
* `number`
* `boolean`
* `enum`

## 4. 刷新与保留规则

后续接入输入状态时，建议规则如下：

| 触发 | 处理 |
| --- | --- |
| 选中节点变化 | 丢弃旧输入，按新节点重建 |
| workflow detail 重新加载 | 丢弃旧输入，按新 detail 重建 |
| node definitions 初次加载 | 从 schema 重建输入 |
| node definitions 刷新且同 node/schema 字段兼容 | 可评估保留同名 dirty 输入，但第一版建议先重建 |
| `WorkflowDefinitionDraftJson` 手动修改 | 第一版建议重建输入，避免显示和 JSON 不一致 |
| Apply 成功 | 通过更新 `WorkflowDefinitionDraftJson` 触发现有刷新链路 |

第一版为了安全，可以先采用“触发即重建”的保守策略。

## 5. Apply 前置条件

Apply 命令应等以下能力具备后再接：

```text
SelectedNodeConfigEditableInputFields
字段输入可编辑
字段输入本地校验
字段输入转换为 NodeConfigEditableDraft 或等价 config JSON
NodeConfigDraftJsonPatcher 写回 workflow draft JSON
```

也就是说，2i 后不建议直接进入 Apply。

更稳顺序是：

```text
UI-NODE-CONFIG-2j
新增 NodeConfigEditableFieldInputViewModel 和输入字段集合状态，
不改 XAML，不接 Apply。

UI-NODE-CONFIG-2k
把输入字段集合转换为 config JSON，并复用 2f 校验。

UI-NODE-CONFIG-2l
接入 ApplySelectedNodeConfigDraftCommand。
```

## 6. UI / Gemini 协作边界

在 Codex 完成输入状态前，不建议让 Gemini 直接做动态表单 View。

Gemini 后续应等待以下接口稳定：

```text
SelectedNodeConfigEditableInputFields
InputValue 双向绑定
EnumValues
Type
Required
Field warning/error
Apply command
CanApply
```

否则 View 层会被迫绑定临时模型，后续返工概率较高。

## 7. 本阶段验收标准

本阶段完成标准：

* 明确 editable draft 是快照，不是用户输入状态。
* 明确需要单独的可变 input field ViewModel。
* 明确第一版刷新策略先采用保守重建。
* 明确 Apply 仍后置。
* 明确下一步先做输入字段状态，不改 XAML。
