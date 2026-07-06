# FlowWeaver UI-NODE-CONFIG-2d.2：Apply 命令接入评估

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：Avalonia schema 解析、可编辑草稿、输入字段 ViewModel、config 构建、Apply 命令和 WorkflowSummaryView 表单接入已经落地。
> 未实现：无本文件目标内的未实现项；专用富编辑器和更复杂字段控件仍按后续节点生态处理。
> 原因：当前实现完成了从 schema 到 draft config 写回的最小闭环。

> 文档状态：UI-NODE-CONFIG-2d.2 接入评估完成
> 当前阶段：只评估是否应立即接入 `ApplySelectedNodeConfigDraftCommand`
> 不适用范围：实现 Apply 按钮、动态字段编辑控件、写回 workflow JSON

## 1. 当前事实

当前已经具备：

* `SelectedWorkflowDefinitionNode`
* `NodeConfigDraftBuilder`
* `SelectedNodeConfigDraftSummaryText`
* `NodeConfigDraftJsonPatcher`

但仍然缺少：

* 字段草稿输入模型。
* 可编辑字段当前输入值。
* 字段级校验结果。
* 用户修改 config 的 UI 控件。

因此，如果现在直接接入 `ApplySelectedNodeConfigDraftCommand`，Apply 只能把当前 JSON 中已有的 `node.config` 再写回 `WorkflowDefinitionDraftJson`。

这个行为技术上可行，但产品语义不清晰：

* 用户没有修改任何字段。
* Apply 看起来像能保存配置，但实际上只是重写当前 config。
* 可能造成“结构化配置编辑已完成”的误解。

## 2. 结论

不建议现在直接接入 Apply 命令或按钮。

更稳顺序是：

```text
UI-NODE-CONFIG-2e：
先新增字段草稿输入模型和校验测试。

UI-NODE-CONFIG-2f：
再接入最小 ViewModel Apply，
只从字段草稿输入模型生成 config object，
写回 WorkflowDefinitionDraftJson。
```

## 3. Apply 命令接入前置条件

进入 Apply 命令前，至少应具备：

```text
NodeConfigDraftEditableField
NodeConfigDraftEditableValue
NodeConfigDraftValidationResult
NodeConfigDraftToJsonObjectBuilder
```

最小支持字段：

* string
* integer
* number
* boolean
* enum

暂不支持字段：

* array
* object
* unsupported

这些字段必须继续 JSON fallback，不能通过不成熟控件写回。

## 4. ViewModel Apply 的正确职责

后续真正接入 Apply 时，命令职责应为：

```text
1. 读取 SelectedWorkflowDefinitionNode。
2. 读取当前字段草稿输入模型。
3. 将可编辑字段转换为 config JsonObject。
4. 调用 NodeConfigDraftJsonPatcher。
5. 成功时设置 WorkflowDefinitionDraftJson = updatedJson。
6. 失败时显示本地错误消息。
```

命令不应：

* 调用后端。
* 调用 Validate。
* 调用 Save。
* 清空 revision conflict。
* 替换 WorkflowDefinitionDetail。
* 修改 node definition catalog。

## 5. CanExecute 建议

后续 `CanApplySelectedNodeConfigDraft` 建议：

```text
CanUseEngineActions
WorkflowDefinitionDetail != null
SelectedWorkflowDefinitionNode != null
HasWorkflowDefinitionDraft
!IsWorkflowDefinitionDraftBusy
!HasWorkflowDefinitionRevisionConflict
EditableDraft != null
EditableDraft.IsValid
```

注意：

* `HasWorkflowDefinitionRevisionConflict == true` 时 Apply 不可用。
* Apply 不负责冲突恢复。
* 冲突恢复应作为独立 UX 小步。

## 6. 测试前置清单

在接入命令前，应先有模型测试：

* string 输入转换为 JSON string。
* integer 输入转换为 JSON number。
* number 输入转换为 JSON number。
* boolean 输入转换为 JSON boolean。
* enum 只允许候选值。
* required 空值报错。
* minimum 不满足报错。
* array/object/unsupported 不进入 editable fields。

接入命令后，再补 ViewModel 测试：

* Apply 成功后更新 `WorkflowDefinitionDraftJson`。
* Apply 成功后 `IsWorkflowDefinitionDraftDirty == true`。
* Apply 成功后 validation 状态失效。
* Apply 不调用 Validate / Save / 后端。
* revision conflict 时 Apply 不可用。
* patcher 失败时保留原 JSON。

## 7. 建议下一小步

```text
UI-NODE-CONFIG-2e：
新增 NodeConfigEditableDraft 纯模型和测试，
只把 NodeConfigDraft 中可编辑字段转换为可输入草稿，
不接 XAML，不接 ViewModel Apply。
```

之后：

```text
UI-NODE-CONFIG-2f：
把 NodeConfigEditableDraft 转为 config JsonObject，
再接 ApplySelectedNodeConfigDraftCommand。
```

## 8. 本阶段验收标准

本阶段完成标准：

* 明确不立即接入 Apply 命令。
* 明确直接 Apply 当前 config 的语义不足。
* 明确 Apply 前需要字段草稿输入模型。
* 明确后续 CanExecute 和测试清单。
* 明确下一小步转向 editable draft 纯模型。
