# FlowWeaver WORKFLOW-EDIT-1.6b：AddNode 命令最小接入

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：结构化只读解析、节点新增/删除、connection 新增/删除、ViewModel 命令、View 接入、用户友好 warning/error、节点/connection 输入体验和 smoke 复核已经落地。
> 未实现：自由画布、拖拽连线、完整撤销/重做和复杂 DAG 自动重排未在本阶段实现。
> 原因：这些能力超出结构化编辑最小闭环，已作为后续体验方向保留。

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
