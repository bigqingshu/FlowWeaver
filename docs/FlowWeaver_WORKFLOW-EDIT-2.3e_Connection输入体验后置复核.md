# FlowWeaver WORKFLOW-EDIT-2.3e：connection 输入体验后置复核

> 文档状态：WORKFLOW-EDIT-2.3e 后置复核完成
> 当前阶段：结构化编辑 connection 输入体验收口
> 不适用范围：port 下拉、端口 schema 深校验、桌面真实截图 smoke

## 1. 阶段目标

复核 WORKFLOW-EDIT-2.3 是否已经完成：

```text
source / target node 选择
+ connection id 自动建议
+ 手动输入降级
```

## 2. 完成矩阵

| 小步 | 内容 | 状态 | 证据 |
| --- | --- | --- | --- |
| 2.3a | connection source / target / id 输入体验前置分析 | 已完成 | `FlowWeaver_WORKFLOW-EDIT-2.3a...md` |
| 2.3b | source / target 选择状态与 connection id 自动建议 | 已完成 | `MainWindowViewModelWorkflowTests` |
| 2.3c | connection View 接入任务说明 | 已完成 | `FlowWeaver_WORKFLOW-EDIT-2.3c...md` |
| 2.3d | connection View 最小接入 | 已完成 | `WorkflowSummaryViewStructureTests` |

## 3. 已完成能力

当前已完成：

* `WorkflowDefinitionDraftStructure.Nodes` 可作为新增 connection 的 source / target 候选来源。
* `SelectedNewDraftConnectionSourceNode` 已接入 ViewModel。
* `SelectedNewDraftConnectionTargetNode` 已接入 ViewModel。
* 选择 source / target node 会填充 endpoint 输入字段。
* source / target 均存在时会自动建议不重复的 connection id。
* 用户手动填写的 connection id 不会被自动覆盖。
* `WorkflowSummaryView` 已在新增 connection 表单中接入 source / target ComboBox。
* source / target node id 手动输入仍保留。
* source / target port 手动输入仍保留。

## 4. 验证证据

最近验证：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "MainWindowViewModelWorkflowTests"
通过：61，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "WorkflowSummaryViewStructureTests|MainWindowViewModelWorkflowTests"
通过：66，失败：0，跳过：0

dotnet build Avalonia_UI\Avalonia_UI.sln --no-restore
成功，警告：0，错误：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：264，失败：0，跳过：0
```

## 5. 保留项

WORKFLOW-EDIT-2.3 仍不包含：

* source / target port 下拉。
* 端口 schema 深校验。
* 端口类型兼容校验。
* 自动连接推荐。
* 图形画布。
* 桌面真实截图 / 手动 smoke。

port 下拉和深校验继续等待更明确的 schema 契约，不应在当前 UI 阶段硬做。

## 6. 当前结论

WORKFLOW-EDIT-2.3 已完成 connection 输入体验的最小收口，可以进入桌面真实 smoke 或 WORKFLOW-EDIT-2 阶段复核。

建议下一步：

```text
WORKFLOW-EDIT-2.4：
桌面真实 smoke 与结构化编辑后置复核。
```

建议先跑真实 Desktop 操作路径，再决定 WORKFLOW-EDIT-2 是否完成。
