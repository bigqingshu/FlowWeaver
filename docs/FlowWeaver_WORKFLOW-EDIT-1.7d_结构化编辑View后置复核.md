# FlowWeaver WORKFLOW-EDIT-1.7d：结构化编辑 View 后置复核

> 文档状态：WORKFLOW-EDIT-1.7d 后置复核完成
> 当前阶段：WORKFLOW-EDIT-1 View 接入后收口
> 不适用范围：新增代码、XAML 再改动、运行桌面截图 smoke

## 1. 完成矩阵

| 小步 | 内容 | 状态 | 证据 |
| --- | --- | --- | --- |
| 1.7 | View 协作说明 | 已完成 | `FlowWeaver_WORKFLOW-EDIT-1.7...md` |
| 1.7a | View 辅助文本属性 | 已完成 | `MainWindowViewModelLocalizationTests` |
| 1.7b | Gemini View 修改任务说明 | 已完成 | `FlowWeaver_WORKFLOW-EDIT-1.7b...md` |
| 1.7c | `WorkflowSummaryView` 结构化编辑表单接入 | 已完成 | `WorkflowSummaryViewStructureTests` |

## 2. 当前 View 能力

当前 `WorkflowSummaryView.axaml` 已有：

```text
Nodes Card:
Add node form
Delete node form

Connections Card:
Add connection form
Delete connection form
```

表单绑定现有 ViewModel 状态和命令。

## 3. 已保持的边界

已确认：

* 没有新增 converter。
* 没有新增 code-behind。
* 没有修改 ViewModel、Models、Localization 或后端。
* 没有改变 `WorkflowDefinitionDetail.Nodes` 的现有 ListBox ItemsSource。
* 没有改变 `WorkflowDefinitionDetail.Connections` 的现有 ListBox ItemsSource。
* 没有混用 loaded detail selection 和 draft selection。
* 节点配置表单仍绑定 `SelectedNodeConfigEditableInputFields` 和 `ApplySelectedNodeConfigDraftCommand`。
* 第一版没有引入画布、拖拽、自动布局。

## 4. 验证证据

最近验证：

```text
dotnet build Avalonia_UI\Avalonia_UI.sln --no-restore
成功，警告：0，错误：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "WorkflowSummaryViewStructureTests|MainWindowViewModelWorkflowTests|MainWindowViewModelLocalizationTests"
通过：81，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：257，失败：0，跳过：0
```

## 5. 保留项

当前尚未完成：

* 桌面真实截图 / 手动 smoke。
* 结构化编辑 warning 的用户友好映射。
* node type 下拉选择。
* source / target node 下拉选择。
* port 下拉选择和端口 schema 深校验。
* 自动生成 node_instance_id / connection_id。
* 连接依赖下的“先删连接再删节点”交互引导。
* 图形化画布。

## 6. 下一小步建议

建议进入：

```text
WORKFLOW-EDIT-1.8：
WORKFLOW-EDIT-1 阶段总体验收复核。
```

建议只做文档和验证复核：

* 从 1.0 到 1.7d 建立完成矩阵。
* 复核模型、ViewModel、View、L10N、测试证据。
* 明确 WORKFLOW-EDIT-1 仍不等同于 WORKFLOW-EDIT-2。
* 决定下一阶段是否进入用户友好错误映射，还是进入桌面 smoke。
