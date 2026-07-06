# FlowWeaver WORKFLOW-EDIT-2.3c：connection View 接入任务说明

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：结构化只读解析、节点新增/删除、connection 新增/删除、ViewModel 命令、View 接入、用户友好 warning/error、节点/connection 输入体验和 smoke 复核已经落地。
> 未实现：自由画布、拖拽连线、完整撤销/重做和复杂 DAG 自动重排未在本阶段实现。
> 原因：这些能力超出结构化编辑最小闭环，已作为后续体验方向保留。

> 文档状态：WORKFLOW-EDIT-2.3c 任务说明完成
> 当前阶段：结构化编辑 connection 输入体验 View 协作前置
> 不适用范围：ViewModel 改动、模型改动、后端 API 改动、port schema 深校验、图形画布

## 1. 目标

在 `WorkflowSummaryView.axaml` 的新增 connection 表单中，接入 source / target 节点选择入口：

```text
WorkflowDefinitionDraftStructure.Nodes
-> SelectedNewDraftConnectionSourceNode
-> SelectedNewDraftConnectionTargetNode
-> NewDraftConnectionSourceNodeId / NewDraftConnectionTargetNodeId / NewDraftConnectionId
```

目标是降低 source / target node id 手输错误，同时保留手动输入降级能力。

## 2. 允许修改范围

仅允许修改：

```text
Avalonia_UI/Views/Components/Workflow/WorkflowSummaryView.axaml
Avalonia_UI.Tests/WorkflowSummaryViewStructureTests.cs
docs/UI组件MainWindow的后续计划.MD
docs/FlowWeaver_WORKFLOW-EDIT-2.3d_ConnectionView最小接入.md
```

## 3. 禁止修改范围

不要修改：

* `MainWindowViewModel.cs`
* `WorkflowDefinitionDraftConnectionPatcher`
* localization JSON
* 后端 API
* code-behind
* converter
* port schema 解析逻辑

## 4. View 接入要求

在 Connections Card 的 Add connection 表单中新增两个选择控件：

```text
Source ComboBox
ItemsSource -> WorkflowDefinitionDraftStructure.Nodes
SelectedItem -> SelectedNewDraftConnectionSourceNode

Target ComboBox
ItemsSource -> WorkflowDefinitionDraftStructure.Nodes
SelectedItem -> SelectedNewDraftConnectionTargetNode
```

建议显示：

* 主标题：`NodeInstanceId`
* 副标题：`NodeType` / `NodeVersion`

必须保留：

* `NewDraftConnectionId` 手动输入。
* `NewDraftConnectionSourceNodeId` 手动输入。
* `NewDraftConnectionTargetNodeId` 手动输入。
* `NewDraftConnectionSourcePort` 手动输入。
* `NewDraftConnectionTargetPort` 手动输入。

也就是说，ComboBox 是辅助选择，不是唯一输入入口。

## 5. 布局建议

优先采用最小改动：

* 在 source node 当前输入区域附近增加 ComboBox。
* 在 target node 当前输入区域附近增加 ComboBox。
* 原 TextBox 保留在 ComboBox 下方。
* 不重排整个 Connections Card。
* 不改变 Nodes Card。
* 不引入新样式或视觉主题。

## 6. 测试要求

更新 `WorkflowSummaryViewStructureTests`，至少检查：

* View 中存在绑定 `WorkflowDefinitionDraftStructure.Nodes` 的 ComboBox。
* Source ComboBox 的 `SelectedItem` 绑定到 `SelectedNewDraftConnectionSourceNode`。
* Target ComboBox 的 `SelectedItem` 绑定到 `SelectedNewDraftConnectionTargetNode`。
* `NewDraftConnectionSourceNodeId` TextBox 仍存在。
* `NewDraftConnectionTargetNodeId` TextBox 仍存在。
* `NewDraftConnectionSourcePort` / `NewDraftConnectionTargetPort` TextBox 仍存在。
* `AddWorkflowDefinitionDraftConnectionCommand` 按钮仍存在。

建议运行：

```text
dotnet build Avalonia_UI\Avalonia_UI.sln --no-restore
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "WorkflowSummaryViewStructureTests|MainWindowViewModelWorkflowTests"
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
```

## 7. 验收标准

完成后应满足：

* 用户可以从当前 draft nodes 中选择 source / target。
* 选择 source / target 后由 ViewModel 自动填充 endpoint 和建议 connection id。
* 用户仍然可以手动编辑 source / target node id。
* source / target port 仍手动输入。
* 纯 View 接入，不引入 code-behind 或 converter。
* 结构测试和完整 Avalonia 测试通过。

## 8. 下一小步建议

建议进入：

```text
WORKFLOW-EDIT-2.3d：
connection View 最小接入。
```
