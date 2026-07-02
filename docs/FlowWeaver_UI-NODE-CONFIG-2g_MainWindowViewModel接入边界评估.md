# FlowWeaver UI-NODE-CONFIG-2g：MainWindowViewModel 接入边界评估

> 文档状态：UI-NODE-CONFIG-2g 边界评估完成
> 当前阶段：只确认 ViewModel 接入顺序和状态刷新边界
> 不适用范围：XAML 动态表单、Apply 按钮、workflow JSON 写回、后端 API 修改

## 1. 当前事实

当前已经具备纯模型：

* `NodeConfigDraftBuilder`
* `NodeConfigEditableDraftBuilder`
* `NodeConfigEditableDraftConfigBuilder`
* `NodeConfigDraftJsonPatcher`

当前 `MainWindowViewModel` 已具备：

* `SelectedWorkflowDefinitionNode`
* `WorkflowDefinitionDraftJson`
* `WorkflowDefinitionDetail`
* `NodeDefinitions`
* `HasWorkflowDefinitionRevisionConflict`
* `SelectedNodeConfigDraftSummaryText`

但当前 `SelectedNodeConfigDraftSummaryText` 是即时计算属性：

```text
SelectedWorkflowDefinitionNode
→ FindNodeDefinition(...)
→ NodeConfigDraftBuilder.Build(...)
→ 只返回摘要文本
```

它没有持久保存：

* `SelectedNodeConfigDraft`
* `SelectedNodeConfigEditableDraft`
* editable field input state
* field error state
* Apply 可用性状态

因此下一步不应直接接 Apply 命令；应先把选中节点配置草稿状态放进 ViewModel。

## 2. 最小接入目标

建议下一小步只做：

```text
SelectedNodeConfigDraft
SelectedNodeConfigEditableDraft
SelectedNodeConfigEditableDraftMessage
```

这些状态只来自本地已有数据：

```text
WorkflowDefinitionDraftJson
SelectedWorkflowDefinitionNode.NodeInstanceId
FindNodeDefinition(...).ConfigSchemaDescriptor
```

不新增后端接口，不重新拉取 workflow，不调用 Validate / Save。

## 3. 刷新触发点

`SelectedNodeConfigEditableDraft` 必须在以下状态变化后刷新：

| 触发点 | 原因 |
| --- | --- |
| `WorkflowDefinitionDetail` 变化 | 当前 workflow definition 被加载、清空或替换 |
| `SelectedWorkflowDefinitionNode` 变化 | 用户切换节点实例 |
| `WorkflowDefinitionDraftJson` 变化 | 用户手工编辑 JSON 或未来 Apply 写回 |
| `NodeDefinitions` 刷新完成 | schema 从 unavailable 变为 available |
| selected workflow 改变 | 需要清空旧 workflow 的节点配置状态 |

当前已有触发点：

* `OnWorkflowDefinitionDetailChanged`
* `OnSelectedWorkflowDefinitionNodeChanged`
* `OnWorkflowDefinitionDraftJsonChanged`
* `RefreshNodeDefinitionsAsync` 完成后手动通知 `SelectedNodeConfigDraftSummaryText`
* `OnSelectedWorkflowChanged`

下一步应复用这些触发点，集中调用一个内部方法：

```text
RefreshSelectedNodeConfigDraftState()
```

## 4. 第一版状态建议

建议第一版新增：

```csharp
[ObservableProperty]
private NodeConfigDraft? selectedNodeConfigDraft;

[ObservableProperty]
private NodeConfigEditableDraft? selectedNodeConfigEditableDraft;

[ObservableProperty]
private string selectedNodeConfigEditableDraftMessage = "...";
```

其中：

* `SelectedNodeConfigDraft` 只保存当前解析结果。
* `SelectedNodeConfigEditableDraft` 只保存从 draft 派生的可编辑字段草稿。
* `SelectedNodeConfigEditableDraftMessage` 先服务测试和后续 UI 显示，不直接弹错。

如果 schema unavailable、node missing、JSON invalid：

* `SelectedNodeConfigDraft` 可以保存 unsupported draft。
* `SelectedNodeConfigEditableDraft` 应为空或无字段。
* Message 使用现有本地化/formatter 语义，不新增复杂 UI 文案。

## 5. Apply 命令仍不建议马上接入

虽然 2f 已经具备 config JSON 构建器，但当前还缺少用户可编辑输入来源。

如果马上接 Apply：

* `SelectedNodeConfigEditableDraft` 只会来自当前 config/default。
* 用户无法修改字段。
* Apply 仍可能只是重写现有值。

因此建议顺序：

```text
UI-NODE-CONFIG-2h
只接 ViewModel 只读/内部 editable draft 状态，不接 Apply。

UI-NODE-CONFIG-2i
再评估最小可编辑输入状态，决定是否先用 JSON config input 或字段级临时输入模型。

UI-NODE-CONFIG-2j
再接 ApplySelectedNodeConfigDraftCommand。
```

## 6. CanApply 未来边界

后续真正接 Apply 时，建议可用条件至少包括：

```text
CanUseEngineActions
WorkflowDefinitionDetail != null
SelectedWorkflowDefinitionNode != null
HasWorkflowDefinitionDraft
!IsWorkflowDefinitionDraftBusy
!HasWorkflowDefinitionRevisionConflict
SelectedNodeConfigEditableDraft != null
SelectedNodeConfigEditableDraft.HasFields
NodeConfigEditableDraftConfigBuilder.Build(...).Succeeded
```

但这只是未来命令边界，本阶段不实现。

## 7. 测试建议

下一步如果进入代码，建议补充 `MainWindowViewModelWorkflowTests`：

* 加载 workflow 后且 schema 未加载时，editable draft 不可用。
* 刷新 node definitions 后，editable draft 有字段。
* 切换 `SelectedWorkflowDefinitionNode` 后，editable draft 切换到新节点。
* 修改 `WorkflowDefinitionDraftJson` 后，editable draft 重新从当前 JSON 派生。
* selected workflow 改变后，editable draft 清空。
* revision conflict 不会被刷新 editable draft 状态清空。

## 8. 本阶段验收标准

本阶段完成标准：

* 明确 ViewModel 当前只有 summary 即时计算，没有 editable draft 状态。
* 明确下一步只接 ViewModel 状态，不接 XAML / Apply。
* 明确刷新触发点。
* 明确 revision conflict、Validate / Save 不应被绕过。
* 明确后续 2h / 2i / 2j 顺序。
