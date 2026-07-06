# FlowWeaver WORKFLOW-EDIT-2.2c：新增节点 View 接入任务说明

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：结构化只读解析、节点新增/删除、connection 新增/删除、ViewModel 命令、View 接入、用户友好 warning/error、节点/connection 输入体验和 smoke 复核已经落地。
> 未实现：自由画布、拖拽连线、完整撤销/重做和复杂 DAG 自动重排未在本阶段实现。
> 原因：这些能力超出结构化编辑最小闭环，已作为后续体验方向保留。

> 文档状态：WORKFLOW-EDIT-2.2c 任务说明完成
> 当前阶段：结构化编辑节点新增体验 View 协作前置
> 不适用范围：ViewModel 改动、模型改动、后端 API 改动、port schema 深校验、图形画布

## 1. 目标

在 `WorkflowSummaryView.axaml` 的新增节点表单中，接入节点目录选择入口：

```text
NodeDefinitions
-> SelectedNewDraftNodeDefinition
-> NewDraftNodeType / NewDraftNodeVersion / NewDraftNodeDisplayName / NewDraftNodeInstanceId
```

目标是降低 `node_type` 手输错误，同时保留手动输入降级能力。

## 2. 允许修改范围

仅允许修改：

```text
Avalonia_UI/Views/Components/Workflow/WorkflowSummaryView.axaml
Avalonia_UI.Tests/WorkflowSummaryViewStructureTests.cs
docs/UI组件MainWindow的后续计划.MD
docs/FlowWeaver_WORKFLOW-EDIT-2.2d_新增节点View最小接入.md
```

如果需要新增文档，可只新增对应阶段文档。

## 3. 禁止修改范围

不要修改：

* `MainWindowViewModel.cs`
* `WorkflowDefinitionDraftNodePatcher`
* localization JSON
* 后端 API
* app shell / navigation
* 主题资源
* code-behind
* converter

## 4. View 接入要求

在 Nodes Card 的 Add node 表单中新增 node catalog 选择控件：

```text
ComboBox
ItemsSource -> NodeDefinitions
SelectedItem -> SelectedNewDraftNodeDefinition
```

建议显示：

* 主标题：`DisplayNameText`
* 副标题：`TypeText`

必须保留：

* `NewDraftNodeInstanceId` 手动输入。
* `NewDraftNodeType` 手动输入。
* `NewDraftNodeVersion` 手动输入。
* `NewDraftNodeDisplayName` 手动输入。
* `NewDraftNodeConfigJson` 手动输入。

也就是说，ComboBox 是辅助选择，不是唯一输入入口。

## 5. 布局建议

优先采用最小改动：

* 在 node type 当前输入区域附近增加 ComboBox。
* 不重排整个 Nodes Card。
* 不改变 Connections Card。
* 不改变节点配置表单。
* 避免引入新的视觉主题或复杂样式。

如果当前四列表格不够放置，可以在 node type 输入所在 cell 内使用一个轻量 `Grid` 或 `StackPanel`，上方 ComboBox、下方保留 TextBox。

## 6. 测试要求

更新 `WorkflowSummaryViewStructureTests`，至少检查：

* View 中存在绑定 `NodeDefinitions` 的 ComboBox。
* ComboBox 的 `SelectedItem` 绑定到 `SelectedNewDraftNodeDefinition`。
* `NewDraftNodeType` TextBox 仍存在。
* `NewDraftNodeInstanceId` TextBox 仍存在。
* `AddWorkflowDefinitionDraftNodeCommand` 按钮仍存在。

建议运行：

```text
dotnet build Avalonia_UI\Avalonia_UI.sln --no-restore
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "WorkflowSummaryViewStructureTests|MainWindowViewModelWorkflowTests"
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
```

## 7. 验收标准

完成后应满足：

* node catalog 加载后，用户可以从 ComboBox 选择节点定义。
* 选择节点定义由 ViewModel 自动填充 node type / version / display name / 建议 ID。
* 用户仍然可以手动编辑 node type 和 node instance id。
* 纯 View 接入，不引入 code-behind 或 converter。
* 结构测试和完整 Avalonia 测试通过。

## 8. 下一小步建议

建议进入：

```text
WORKFLOW-EDIT-2.2d：
新增节点 View 最小接入。
```

这一步如果由 Gemini 修改，应严格按本文档执行；如果由 Codex 修改，也应保持纯 XAML + 结构测试的小步边界。
