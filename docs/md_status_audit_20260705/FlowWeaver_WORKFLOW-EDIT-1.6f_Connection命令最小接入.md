# FlowWeaver WORKFLOW-EDIT-1.6f：Connection 命令最小接入

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：结构化只读解析、节点新增/删除、connection 新增/删除、ViewModel 命令、View 接入、用户友好 warning/error、节点/connection 输入体验和 smoke 复核已经落地。
> 未实现：自由画布、拖拽连线、完整撤销/重做和复杂 DAG 自动重排未在本阶段实现。
> 原因：这些能力超出结构化编辑最小闭环，已作为后续体验方向保留。

> 文档状态：WORKFLOW-EDIT-1.6f 已完成
> 当前阶段：结构化 connection 新增 / 删除命令接入 ViewModel
> 不适用范围：XAML 按钮、端口 schema 深校验、画布连线

## 1. 本小步目标

本小步新增 ViewModel 命令：

```text
AddWorkflowDefinitionDraftConnectionCommand
DeleteWorkflowDefinitionDraftConnectionCommand
```

底层调用：

```text
WorkflowDefinitionDraftConnectionPatcher.AddConnection(...)
WorkflowDefinitionDraftConnectionPatcher.DeleteConnection(...)
```

## 2. 当前行为

AddConnection 命令可用条件：

* EngineHost action 可用。
* 已加载 workflow definition。
* `WorkflowDefinitionDraftJson` 非空。
* 当前没有 validate / save busy。
* 没有 revision conflict。
* connection id、source node id、source port、target node id、target port 均非空。

DeleteConnection 命令可用条件：

* EngineHost action 可用。
* 已加载 workflow definition。
* `WorkflowDefinitionDraftJson` 非空。
* 当前没有 validate / save busy。
* 没有 revision conflict。
* 已选择 draft connection id。

命令成功时：

* 写回 `WorkflowDefinitionDraftJson`。
* 由现有 setter 触发 dirty、validation invalidation、draft structure 刷新。
* AddConnection 成功后重置 connection 输入。
* DeleteConnection 成功后所选 connection 不再存在时，选择状态自动清空。

命令失败时：

* 不修改 `WorkflowDefinitionDraftJson`。
* 不清空用户输入/选择。
* 显示 patcher warning，例如 `TARGET_NODE_NOT_FOUND`。

## 3. 当前不做

本小步仍不做：

* 端口 schema 深校验。
* 自动生成 connection id。
* XAML 输入区。
* 图形化连线。

## 4. 验证结果

已执行：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "MainWindowViewModelWorkflowTests"
通过：54，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：256，失败：0，跳过：0
```

## 5. 下一小步建议

建议进入：

```text
WORKFLOW-EDIT-1.6g：
结构化编辑命令后置复核。
```

建议范围：

* 汇总 AddNode / DeleteNode / AddConnection / DeleteConnection 的完成矩阵。
* 复核 dirty / validation invalidation / revision conflict / busy / no-XAML 边界。
* 决定是否进入 Gemini View 协作说明，还是先补更细的错误消息格式化。
