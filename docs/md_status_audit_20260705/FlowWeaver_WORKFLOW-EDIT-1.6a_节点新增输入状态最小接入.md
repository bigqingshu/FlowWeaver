# FlowWeaver WORKFLOW-EDIT-1.6a：节点新增输入状态最小接入

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：结构化只读解析、节点新增/删除、connection 新增/删除、ViewModel 命令、View 接入、用户友好 warning/error、节点/connection 输入体验和 smoke 复核已经落地。
> 未实现：自由画布、拖拽连线、完整撤销/重做和复杂 DAG 自动重排未在本阶段实现。
> 原因：这些能力超出结构化编辑最小闭环，已作为后续体验方向保留。

> 文档状态：WORKFLOW-EDIT-1.6a 已完成
> 当前阶段：结构化节点新增命令接入前的 ViewModel 输入状态
> 不适用范围：调用 patcher、修改 draft JSON、XAML 输入控件、保存语义调整

## 1. 本小步目标

本小步只在 `MainWindowViewModel` 中新增节点新增输入状态：

```text
NewDraftNodeInstanceId
NewDraftNodeType
NewDraftNodeVersion
NewDraftNodeDisplayName
NewDraftNodeConfigJson
```

默认值：

```text
NewDraftNodeVersion = "1.0"
NewDraftNodeConfigJson = "{}"
```

## 2. 当前行为

当前只做输入状态，不执行写入：

* 不调用 `WorkflowDefinitionDraftNodePatcher.AddNode`。
* 不修改 `WorkflowDefinitionDraftJson`。
* 不改变 dirty / validation invalidation。
* 不新增命令。
* 不修改 XAML。

加载或切换 workflow definition 时，会重置节点新增输入，避免旧 workflow 的输入误用于新草稿。

## 3. 验证结果

已执行：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "MainWindowViewModelWorkflowTests"
通过：44，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：246，失败：0，跳过：0
```

## 4. 下一小步建议

建议进入：

```text
WORKFLOW-EDIT-1.6b：
AddNode 命令最小接入。
```

建议范围：

* 解析 `NewDraftNodeConfigJson`。
* 调用 `WorkflowDefinitionDraftNodePatcher.AddNode`。
* 成功后写回 `WorkflowDefinitionDraftJson`。
* 失败后写入 validation message / error。
* revision conflict、busy、无 draft 时禁用。
* 不修改 XAML。
