# FlowWeaver WORKFLOW-EDIT-1.7c：WorkflowSummaryView 结构化编辑表单接入

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：结构化只读解析、节点新增/删除、connection 新增/删除、ViewModel 命令、View 接入、用户友好 warning/error、节点/connection 输入体验和 smoke 复核已经落地。
> 未实现：自由画布、拖拽连线、完整撤销/重做和复杂 DAG 自动重排未在本阶段实现。
> 原因：这些能力超出结构化编辑最小闭环，已作为后续体验方向保留。

> 文档状态：WORKFLOW-EDIT-1.7c 已完成
> 当前阶段：结构化编辑命令进入 Avalonia View 的最小表单入口
> 不适用范围：画布编辑、拖拽连线、端口 schema 深校验、ViewModel/模型/后端改动

## 1. 本小步目标

本小步只修改：

```text
Avalonia_UI/Views/Components/Workflow/WorkflowSummaryView.axaml
Avalonia_UI.Tests/WorkflowSummaryViewStructureTests.cs
```

完成内容：

* 在 Nodes Card 内增加节点新增/删除紧凑表单。
* 在 Connections Card 内增加 connection 新增/删除紧凑表单。
* 使用 1.7a 提供的本地化文本属性。
* 绑定现有结构化编辑输入状态和命令。
* 不修改 ViewModel、模型、本地化资源或后端。

## 2. 当前绑定

节点表单绑定：

```text
NewDraftNodeInstanceId
NewDraftNodeType
NewDraftNodeVersion
NewDraftNodeDisplayName
NewDraftNodeConfigJson
AddWorkflowDefinitionDraftNodeCommand
SelectedWorkflowDefinitionDraftNodeInstanceId
DeleteWorkflowDefinitionDraftNodeCommand
```

Connection 表单绑定：

```text
NewDraftConnectionId
NewDraftConnectionSourceNodeId
NewDraftConnectionSourcePort
NewDraftConnectionTargetNodeId
NewDraftConnectionTargetPort
AddWorkflowDefinitionDraftConnectionCommand
SelectedWorkflowDefinitionDraftConnectionId
DeleteWorkflowDefinitionDraftConnectionCommand
```

## 3. 保持不变

本小步保持：

* `WorkflowDefinitionDetail.Nodes` ListBox 仍是 loaded detail 投影。
* `WorkflowDefinitionDetail.Connections` ListBox 仍是 loaded detail 投影。
* `SelectedWorkflowDefinitionNode` 仍只服务节点配置表单。
* 节点配置表单行为不变。
* 未引入 converter。
* 未引入 code-behind。

## 4. 验证结果

已执行：

```text
dotnet build Avalonia_UI\Avalonia_UI.sln --no-restore
成功，警告：0，错误：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "WorkflowSummaryViewStructureTests|MainWindowViewModelWorkflowTests|MainWindowViewModelLocalizationTests"
通过：81，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：257，失败：0，跳过：0
```

## 5. 下一小步建议

建议进入：

```text
WORKFLOW-EDIT-1.7d：
结构化编辑 View 后置复核。
```

建议范围：

* 复核 XAML 绑定清单。
* 复核没有越界修改 ViewModel / Models / Localization。
* 复核新增表单和现有节点配置表单互不干扰。
* 决定是否需要实际桌面截图/手动 smoke，或进入 WORKFLOW-EDIT-1 阶段总体验收。
