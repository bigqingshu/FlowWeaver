# FlowWeaver UI-NODE-CONFIG-2l：Apply 命令最小接入

> 文档状态：UI-NODE-CONFIG-2l 代码实现完成
> 当前阶段：只在 `MainWindowViewModel` 接入 `ApplySelectedNodeConfigDraftCommand`
> 不适用范围：XAML 按钮、动态字段表单、后端 API 修改、自动保存

## 1. 阶段目标

本阶段完成最小 Apply 链路：

```text
SelectedNodeConfigEditableInputFields
→ NodeConfigEditableFieldInputConfigBuilder
→ NodeConfigDraftJsonPatcher
→ WorkflowDefinitionDraftJson
```

Apply 只修改本地 workflow draft JSON，不调用后端。

## 2. 已完成内容

`MainWindowViewModel` 新增：

```text
ApplySelectedNodeConfigDraftCommand
CanApplySelectedNodeConfigDraft
```

Apply 成功时：

* 从输入字段集合构建 config JSON。
* patch 当前选中节点的 `config`。
* 设置 `WorkflowDefinitionDraftJson = updatedJson`。
* 触发现有 dirty / validation invalidation 链路。
* 显示 `definition.node_config_applied`。

Apply 失败时：

* 保留原 `WorkflowDefinitionDraftJson`。
* 显示 `definition.node_config_apply_failed`。
* 字段错误以 `fieldName: warningCode` 形式进入 validation error message。

新增本地化键：

```text
definition.node_config_applied
definition.node_config_apply_failed
```

## 3. CanExecute 边界

当前最小条件：

```text
CanUseEngineActions
WorkflowDefinitionDetail != null
SelectedWorkflowDefinitionNode != null
HasWorkflowDefinitionDraft
!IsWorkflowDefinitionDraftBusy
!HasWorkflowDefinitionRevisionConflict
HasSelectedNodeConfigEditableInputFields
```

revision conflict 状态下 Apply 不可用，不能误导用户认为冲突已解决。

## 4. 测试覆盖

补充 `MainWindowViewModelWorkflowTests`：

* Apply 成功后 patch `WorkflowDefinitionDraftJson`。
* Apply 成功后 draft dirty。
* Apply 成功后显示本地 Apply 成功消息。
* 字段输入非法时 Apply 拒绝且保留原 JSON。
* revision conflict 状态下 Apply 不可用。

## 5. 明确未做

本阶段没有做：

* 不改 XAML。
* 不显示 Apply 按钮。
* 不做动态字段表单。
* 不调用 Validate / Save / 后端 API。
* 不清空 revision conflict。
* 不做字段错误可视化回填。

## 6. 验证结果

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "MainWindowViewModelWorkflowTests"
通过：42，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：213，失败：0，跳过：0
```

## 7. 下一小步建议

下一步建议先做 View 协作说明，不直接让 Gemini 自由改：

```text
UI-NODE-CONFIG-2m：
整理节点配置字段表单和 Apply 按钮的 XAML 接入说明，
明确绑定对象、Command、控件类型和不可改边界。
```

之后再交给 Gemini 做纯 View 层接入会更稳。
