# FlowWeaver UI-NODE-CONFIG-2o：WorkflowSummaryView 节点配置表单最小接入

> 文档状态：UI-NODE-CONFIG-2o 代码实现完成
> 当前阶段：只在 `WorkflowSummaryView.axaml` 接入节点配置字段表单和 Apply 按钮
> 不适用范围：重设计 Workflow 页面、修改 Apply 逻辑、调用后端 API、自动保存 workflow

## 1. 阶段目标

本阶段把前面已经完成的 ViewModel 契约接入 View：

```text
SelectedNodeConfigEditableInputFields
ApplySelectedNodeConfigDraftCommand
```

表单位置保持在 `WorkflowSummaryView.axaml` 的 Nodes Card 底部。

## 2. 已完成内容

`WorkflowSummaryView.axaml`：

* Nodes Card 底部新增节点配置区域。
* 字段列表绑定 `SelectedNodeConfigEditableInputFields`。
* 整体显示绑定 `HasSelectedNodeConfigEditableInputFields`。
* Apply 按钮绑定 `ApplySelectedNodeConfigDraftCommand`。
* string / integer / number 使用 `TextBox`。
* enum 使用 `ComboBox` + `EnumValues`。
* boolean 使用 `ComboBox` + `BooleanValues`。
* warning 使用 `WarningText` / `HasWarnings`。

`MainWindowViewModel`：

* 新增 `NodeConfigSectionText`。
* 新增 `ApplyNodeConfigText`。

本地化：

* `definition.node_config`
* `definition.apply_node_config`

测试：

* `WorkflowSummaryViewStructureTests` 增加节点配置表单绑定检查。

## 3. 保持不变

本阶段保持：

* 不改 `MainWindow.axaml`。
* 不改 `WorkflowPage.axaml` 三列结构。
* 不改 `MainWindowViewModel` 的 Apply 语义。
* 不调用 Validate / Save / 后端 API。
* 不新增 converter。
* 不新增 code-behind。

## 4. 验证结果

```text
dotnet build Avalonia_UI\Avalonia_UI.sln --no-restore
成功，警告：0，错误：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "WorkflowSummaryViewStructureTests|MainWindowViewModelWorkflowTests"
通过：45，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：215，失败：0，跳过：0
```

## 5. 当前限制

当前还没有做：

* 未做真实桌面截图核验。
* 未做字段错误的精细 UI 回填。
* 未做 array / object 字段的 JSON fallback 编辑器。
* 未做节点配置区域高度/滚动的真实窗口体验复核。

## 6. 下一小步建议

下一步建议：

```text
UI-NODE-CONFIG-2p：
节点配置表单后置复核，
重点检查布局高度、空状态、revision conflict 下 Apply 禁用、
以及真实 UI 中字段输入 + Apply + Draft JSON 的最小链路。
```
