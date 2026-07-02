# FlowWeaver WORKFLOW-EDIT-1.2：ViewModel 只读草稿结构状态接入

> 文档状态：WORKFLOW-EDIT-1.2 已完成
> 当前阶段：将 workflow draft structure 接入 Avalonia ViewModel
> 不适用范围：XAML 展示、节点增删命令、连线增删命令、保存语义调整

## 1. 本小步目标

本小步只把 `WorkflowDefinitionDraftStructure` 接入 `MainWindowViewModel` 的只读状态。

新增状态：

```text
WorkflowDefinitionDraftStructure
HasWorkflowDefinitionDraftStructure
WorkflowDefinitionDraftNodeCount
WorkflowDefinitionDraftConnectionCount
HasWorkflowDefinitionDraftStructureWarnings
```

这些状态只由 `WorkflowDefinitionDraftJson` 派生，不作为独立保存源。

## 2. 行为边界

当前行为：

* 加载 workflow definition 后，`WorkflowDefinitionDraftJson` 初始化，同时派生 draft structure。
* 手动修改 `WorkflowDefinitionDraftJson` 后，draft structure 自动重建。
* 清空或切换 workflow 时，draft structure 清空。
* draft structure 与 `WorkflowDefinitionDetail.Nodes` / `Connections` 保持语义区分。

未改变：

* `ValidateWorkflowDefinitionDraftCommand`
* `SaveWorkflowDefinitionDraftCommand`
* `ApplySelectedNodeConfigDraftCommand`
* revision conflict 阻断规则
* dirty 与 validation invalidation 规则

## 3. 验证结果

已执行：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "MainWindowViewModelWorkflowTests"
通过：43，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：223，失败：0，跳过：0
```

## 4. 下一小步建议

建议进入：

```text
WORKFLOW-EDIT-1.3：
节点新增纯 patcher 前置实现。
```

建议范围：

* 只新增纯模型 patcher 和测试。
* 输入当前 draft JSON、node_instance_id、node_type、node_version、display_name、初始 config。
* 校验 nodes / connections 基础结构。
* 校验重复 node_instance_id。
* 输出更新后的 draft JSON。
* 不接 ViewModel 命令，不修改 XAML。
