# FlowWeaver UI-NODE-CONFIG-2d：Apply 写回边界与验收清单

> 文档状态：UI-NODE-CONFIG-2d Apply 写回边界分析完成
> 当前阶段：只确认最小 Apply 写回算法、状态语义和验收清单
> 不适用范围：动态表单实现、字段编辑控件、后端 API 修改、自动保存

## 1. 当前事实

当前 UI 已具备：

* `SelectedWorkflowDefinitionNode`
* `NodeConfigDraft`
* `NodeConfigDraftBuilder`
* `SelectedNodeConfigDraftSummaryText`
* `WorkflowDefinitionDraftJson`
* `ValidateWorkflowDefinitionDraftCommand`
* `SaveWorkflowDefinitionDraftCommand`

当前 UI 尚未具备：

* 可编辑字段控件。
* 可持久化的 `NodeConfigDraft` UI 状态。
* `ApplySelectedNodeConfigDraftCommand`。
* 写回 `WorkflowDefinitionDraftJson` 的节点 config patcher。

因此本阶段只分析 Apply 写回边界，不直接实现。

## 2. Apply 的唯一职责

Apply 只做一件事：

```text
把当前选中节点的 config 草稿写回 WorkflowDefinitionDraftJson。
```

Apply 不做：

* 不调用后端。
* 不调用 Validate。
* 不调用 Save。
* 不刷新 WorkflowDefinitionDetail。
* 不清空 revision conflict。
* 不改变 selected workflow。
* 不改变 node definition catalog。

保存仍然只允许通过：

```text
SaveWorkflowDefinitionDraftCommand
```

## 3. 最小 Apply 输入

后续最小实现需要以下输入：

```text
WorkflowDefinitionDraftJson
SelectedWorkflowDefinitionNode.NodeInstanceId
NodeConfigDraft 或等价的字段草稿值集合
```

第一版不应直接从 `WorkflowDefinitionDetail.RawDefinitionJson` 写回。

原因：

* 用户可能已经手工修改 JSON 草稿。
* dirty 状态以 `WorkflowDefinitionDraftJson` 为准。
* revision conflict 后必须保留用户当前草稿。

## 4. JSON patcher 边界

建议后续新增纯模型/工具：

```text
NodeConfigDraftApplyResult
NodeConfigDraftJsonPatcher
```

建议输入：

```text
workflowDefinitionDraftJson: string
nodeInstanceId: string
config: JsonElement 或 IReadOnlyDictionary<string, JsonElement>
```

建议输出：

```text
Success
UpdatedWorkflowDefinitionDraftJson
Warnings
ErrorCode
```

错误状态建议：

| 状态 | 含义 |
| --- | --- |
| `JSON_INVALID` | 当前 `WorkflowDefinitionDraftJson` 无法解析 |
| `NODES_MISSING` | 根对象没有合法 `nodes[]` |
| `NODE_NOT_FOUND` | 找不到选中节点实例 |
| `NODE_CONFIG_NOT_OBJECT` | 现有 node.config 不是对象，需要明确替换策略 |
| `CONFIG_UNSUPPORTED` | 当前草稿不能安全写回 |

第一版建议：

* 缺失 `config` 时新增对象。
* 已有 `config` 为 object 时替换为草稿 config。
* 已有 `config` 不是 object 时拒绝，不静默覆盖。
* 保留节点其它字段。
* 保留 workflow 根对象其它字段。
* 保留 connections、outputs、failure_policy 等其它区域。

## 5. JSON 格式边界

Apply 后可以重新格式化整份 workflow JSON。

建议：

```text
JsonSerializerOptions { WriteIndented = true }
```

原因：

* 当前 `WorkflowDefinitionDetailViewModel` 已使用缩进 JSON。
* 结构化编辑优先保证数据正确与可读。
* 不承诺保留用户手工格式。

但必须保留：

* JSON 字段语义。
* 未修改节点的 config。
* 未修改节点的顺序。
* 未修改 connection 顺序。

## 6. Dirty / validation 语义

Apply 写回必须通过设置：

```text
WorkflowDefinitionDraftJson = updatedJson
```

而不是绕过属性直接改内部字段。

原因：

* `OnWorkflowDefinitionDraftJsonChanged` 会更新 `IsWorkflowDefinitionDraftDirty`。
* 已有 validation 成功/失败状态会被置为 `definition.validation_invalidated`。
* Save command 可用性会复用现有逻辑。
* `SelectedNodeConfigDraftSummaryText` 会自动刷新。

Apply 后预期：

| 条件 | 结果 |
| --- | --- |
| updatedJson 与 original 不同 | `IsWorkflowDefinitionDraftDirty == true` |
| Apply 前 validation 已成功 | validation message 变为“草稿已修改，请重新校验” |
| Apply 前 validation 有问题 | validation message 变为“草稿已修改，请重新校验” |
| Apply 后用户未 Save | 后端不变 |
| Apply 后点击 Save | 继续带原 `base_revision_id` |

## 7. Revision conflict 语义

现有语义：

* Save 遇到 `WORKFLOW_REVISION_CONFLICT` 时，保留当前 `WorkflowDefinitionDraftJson`。
* `HasWorkflowDefinitionRevisionConflict = true` 后 Save 禁用。
* 用户继续编辑 JSON 不会自动清空 conflict 标记。

Apply 不应改变这条语义。

建议：

* 如果 `HasWorkflowDefinitionRevisionConflict == true`，第一版 Apply 应拒绝或保持不可用。
* 不允许 Apply 清空 `HasWorkflowDefinitionRevisionConflict`。
* 冲突恢复应作为单独 UX 阶段处理，例如重新加载、复制草稿、手工合并。

原因：

* Apply 只是本地草稿操作，但 conflict 表示 base revision 已过期。
* 自动继续 Apply 可能给用户造成“冲突已解决”的错觉。

## 8. 可用性边界

第一版 `CanApplySelectedNodeConfigDraft` 建议条件：

```text
CanUseEngineActions
WorkflowDefinitionDetail != null
SelectedWorkflowDefinitionNode != null
HasWorkflowDefinitionDraft
!IsWorkflowDefinitionDraftBusy
!HasWorkflowDefinitionRevisionConflict
NodeConfigDraft.Status == Supported
NodeConfigDraft 字段草稿校验通过
```

但如果后续 2d 只实现 patcher，不接按钮，则不需要 command。

更稳顺序：

```text
UI-NODE-CONFIG-2d.1
只做 NodeConfigDraftJsonPatcher + tests。

UI-NODE-CONFIG-2d.2
再接 ApplySelectedNodeConfigDraftCommand。
```

## 9. 测试清单

最小 patcher 测试：

* 替换选中节点已有 object config。
* 缺失 config 时新增 object config。
* 保留其它节点和 connections。
* 找不到节点返回 `NODE_NOT_FOUND`。
* JSON 无效返回 `JSON_INVALID`。
* node.config 非 object 时拒绝。

最小 ViewModel Apply 测试：

* Apply 后 `WorkflowDefinitionDraftJson` 包含新 config。
* Apply 后 `IsWorkflowDefinitionDraftDirty == true`。
* Apply 后 Validate 成功状态失效。
* Apply 后不调用后端 Validate / Save。
* revision conflict 状态下 Apply 不可用或被拒绝。
* Apply 后 Save 仍使用原 `base_revision_id`。

## 10. 与后端阶段的关系

Apply 写回不要求后端改动。

后端相关能力保持后置：

* workflow config 静态校验。
* schema 对 config 的服务端校验。
* 节点配置专用 API。
* 节点级 patch API。

第一阶段最稳路线仍是：

```text
完整 workflow definition 更新 + base_revision_id
```

## 11. 建议下一小步

```text
UI-NODE-CONFIG-2d.1：
新增 NodeConfigDraftJsonPatcher 纯模型和测试，
只验证 JSON patch 算法，
不接 MainWindowViewModel，不加 Apply 按钮。
```

然后再决定是否进入：

```text
UI-NODE-CONFIG-2d.2：
接入 ApplySelectedNodeConfigDraftCommand 的最小 ViewModel 层，
仍不实现动态字段编辑控件。
```

## 12. 本阶段验收标准

本阶段完成标准：

* 明确 Apply 只写回 `WorkflowDefinitionDraftJson`。
* 明确 Apply 不调用 Validate / Save / 后端 API。
* 明确 dirty、validation invalidation、revision conflict 的继承语义。
* 明确 patcher 错误状态。
* 明确最小测试清单。
* 明确下一小步先做纯 patcher，不直接接按钮。
