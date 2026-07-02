# FlowWeaver WORKFLOW-EDIT-1.6b：AddNode 命令最小接入

> 文档状态：WORKFLOW-EDIT-1.6b 已完成
> 当前阶段：结构化节点新增命令接入 ViewModel
> 不适用范围：XAML 按钮、节点删除命令、connection 命令、自动生成节点 ID

## 1. 本小步目标

本小步新增 ViewModel 命令：

```text
AddWorkflowDefinitionDraftNodeCommand
```

命令输入来自：

```text
NewDraftNodeInstanceId
NewDraftNodeType
NewDraftNodeVersion
NewDraftNodeDisplayName
NewDraftNodeConfigJson
```

底层调用：

```text
WorkflowDefinitionDraftNodePatcher.AddNode(...)
```

## 2. 当前行为

命令可用条件：

* EngineHost action 可用。
* 已加载 workflow definition。
* `WorkflowDefinitionDraftJson` 非空。
* 当前没有 validate / save busy。
* 没有 revision conflict。
* node instance id / type / version / config JSON 输入非空。

命令成功时：

* 写回 `WorkflowDefinitionDraftJson`。
* 由现有 setter 触发 dirty、validation invalidation 和 draft structure 刷新。
* 显示新增成功消息。
* 重置节点新增输入。

命令失败时：

* 不修改 `WorkflowDefinitionDraftJson`。
* 不清空用户输入。
* 写入 `WorkflowDefinitionValidationMessage` / `WorkflowDefinitionValidationErrorMessage`。

## 3. 本地化

新增 key：

```text
definition.node_added
definition.node_add_failed
definition.node_add_config_json_invalid
```

已补充英文和简体中文。

## 4. 验证结果

已执行：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "MainWindowViewModelWorkflowTests"
通过：47，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：249，失败：0，跳过：0
```

## 5. 下一小步建议

建议进入：

```text
WORKFLOW-EDIT-1.6c：
DeleteNode 命令前置状态。
```

建议范围：

* 新增 `SelectedWorkflowDefinitionDraftNodeInstanceId` 或同等文本状态。
* 不复用 `SelectedWorkflowDefinitionNode`，避免 loaded detail selection 与 draft selection 混淆。
* 不调用 delete patcher。
* 不修改 XAML。
