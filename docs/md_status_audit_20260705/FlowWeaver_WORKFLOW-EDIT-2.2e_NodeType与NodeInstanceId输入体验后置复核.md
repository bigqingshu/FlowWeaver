# FlowWeaver WORKFLOW-EDIT-2.2e：node type 与 node instance id 输入体验后置复核

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：结构化只读解析、节点新增/删除、connection 新增/删除、ViewModel 命令、View 接入、用户友好 warning/error、节点/connection 输入体验和 smoke 复核已经落地。
> 未实现：自由画布、拖拽连线、完整撤销/重做和复杂 DAG 自动重排未在本阶段实现。
> 原因：这些能力超出结构化编辑最小闭环，已作为后续体验方向保留。

> 文档状态：WORKFLOW-EDIT-2.2e 后置复核完成
> 当前阶段：结构化编辑节点新增体验收口
> 不适用范围：connection 输入体验、port schema 深校验、桌面真实截图 smoke

## 1. 阶段目标

复核 WORKFLOW-EDIT-2.2 是否已经完成：

```text
node type 选择
+ node instance id 自动建议
+ 手动输入降级
```

## 2. 完成矩阵

| 小步 | 内容 | 状态 | 证据 |
| --- | --- | --- | --- |
| 2.2a | node type 与 node instance id 输入体验前置分析 | 已完成 | `FlowWeaver_WORKFLOW-EDIT-2.2a...md` |
| 2.2b | `SelectedNewDraftNodeDefinition` 与自动建议 ID | 已完成 | `MainWindowViewModelWorkflowTests` |
| 2.2c | 新增节点 View 接入任务说明 | 已完成 | `FlowWeaver_WORKFLOW-EDIT-2.2c...md` |
| 2.2d | 新增节点 View 最小接入 | 已完成 | `WorkflowSummaryViewStructureTests` |

## 3. 已完成能力

当前已完成：

* `NodeDefinitions` 可作为新增节点候选来源。
* `SelectedNewDraftNodeDefinition` 已接入 ViewModel。
* 选择节点定义会填充 node type / version / display name。
* 选择节点定义会生成不重复的 node instance id。
* 用户手动填写的 node instance id 不会被自动覆盖。
* `WorkflowSummaryView` 已在新增节点表单中接入节点目录 ComboBox。
* `NewDraftNodeType` 手动输入仍保留。
* `NewDraftNodeInstanceId` 手动输入仍保留。

## 4. 验证证据

最近验证：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "MainWindowViewModelWorkflowTests"
通过：58，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "WorkflowSummaryViewStructureTests|MainWindowViewModelWorkflowTests"
通过：63，失败：0，跳过：0

dotnet build Avalonia_UI\Avalonia_UI.sln --no-restore
成功，警告：0，错误：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：261，失败：0，跳过：0
```

## 5. 保留项

WORKFLOW-EDIT-2.2 仍不包含：

* source / target node 下拉选择。
* connection id 自动建议。
* source / target port 下拉选择。
* 端口 schema 深校验。
* 图形画布。
* 桌面真实截图 / 手动 smoke。

其中 source / target node 下拉和 connection id 自动建议建议进入 `WORKFLOW-EDIT-2.3`；port 下拉和端口深校验继续等待 schema 契约。

## 6. 当前结论

WORKFLOW-EDIT-2.2 已完成“新增节点输入体验”的最小收口，可以进入 connection 输入体验收口。

建议下一步：

```text
WORKFLOW-EDIT-2.3a：
connection source / target / id 输入体验前置分析。
```

2.3 应继续小步推进，先做 ViewModel 状态和自动建议，再做 View 接入。
