# FlowWeaver WORKFLOW-EDIT-2.3b：connection source / target 选择状态与自动建议 ID

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：结构化只读解析、节点新增/删除、connection 新增/删除、ViewModel 命令、View 接入、用户友好 warning/error、节点/connection 输入体验和 smoke 复核已经落地。
> 未实现：自由画布、拖拽连线、完整撤销/重做和复杂 DAG 自动重排未在本阶段实现。
> 原因：这些能力超出结构化编辑最小闭环，已作为后续体验方向保留。

> 文档状态：WORKFLOW-EDIT-2.3b 已完成
> 当前阶段：结构化编辑 connection 输入体验收口
> 不适用范围：XAML 接入、port 下拉、端口 schema 深校验、后端 API 改动

## 1. 阶段目标

在不修改 View 的前提下，为新增 connection 表单提供 source / target 选择状态和 connection id 自动建议：

```text
WorkflowDefinitionDraftStructure.Nodes
-> SelectedNewDraftConnectionSourceNode
-> SelectedNewDraftConnectionTargetNode
-> NewDraftConnectionSourceNodeId / NewDraftConnectionTargetNodeId
-> NewDraftConnectionId 自动建议
```

## 2. 修改范围

已修改：

* `Avalonia_UI/ViewModels/MainWindowViewModel.cs`
* `Avalonia_UI.Tests/MainWindowViewModelWorkflowTests.cs`

未修改：

* `WorkflowSummaryView.axaml`
* `WorkflowDefinitionDraftConnectionPatcher`
* 后端 API
* localization 资源

## 3. 实现内容

新增状态：

```text
SelectedNewDraftConnectionSourceNode
SelectedNewDraftConnectionTargetNode
```

选择 source node 时：

* 设置 `NewDraftConnectionSourceNodeId`。
* 如果 target 也已存在，则尝试生成 connection id。

选择 target node 时：

* 设置 `NewDraftConnectionTargetNodeId`。
* 如果 source 也已存在，则尝试生成 connection id。

自动建议规则：

```text
source + filter -> source_to_filter
source_to_filter 已存在 -> source_to_filter_2
```

用户已手动填写 `NewDraftConnectionId` 时，不覆盖用户输入。

## 4. 保持边界

已保持：

* source / target port 仍手动输入。
* 不根据端口 schema 自动推断端口。
* 不修改 connection patcher。
* 不修改后端 API。
* draft nodes 不可用时，仍可手动输入 source / target node id。

## 5. 测试覆盖

已补充 `MainWindowViewModelWorkflowTests`：

* 选择 source / target node 会填充 endpoint 输入。
* source / target 均存在时自动建议 connection id。
* 已有重复 connection id 时自动追加后缀。
* 用户手动填写 connection id 后不会被覆盖。

当前已运行：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "MainWindowViewModelWorkflowTests"
通过：61，失败：0，跳过：0

dotnet build Avalonia_UI\Avalonia_UI.sln --no-restore
成功，警告：0，错误：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：264，失败：0，跳过：0
```

## 6. 保留项

本阶段仍未完成：

* `WorkflowSummaryView.axaml` 中 source / target node ComboBox 接入。
* View 层保留手动 source / target node id 输入。
* connection source / target port 下拉。
* port schema 深校验。
* 2.3 后置复核。

## 7. 下一小步建议

建议进入：

```text
WORKFLOW-EDIT-2.3c：
connection View 接入任务说明。
```

后续 View 接入应绑定 `WorkflowDefinitionDraftStructure.Nodes`、`SelectedNewDraftConnectionSourceNode` 和 `SelectedNewDraftConnectionTargetNode`，并保留原有手动 TextBox。
