# FlowWeaver WORKFLOW-EDIT-2.2b：SelectedNewDraftNodeDefinition 与自动建议 ID

> 文档状态：WORKFLOW-EDIT-2.2b 已完成
> 当前阶段：结构化编辑节点新增体验收口
> 不适用范围：XAML 接入、ComboBox 视觉调整、后端 API 改动、port schema 深校验

## 1. 阶段目标

在不修改 View 的前提下，先为新增节点表单提供 ViewModel 状态桥接：

```text
NodeDefinitions
-> SelectedNewDraftNodeDefinition
-> NewDraftNodeType / NewDraftNodeVersion / NewDraftNodeDisplayName
-> NewDraftNodeInstanceId 自动建议
```

这样后续 View 接入可以直接绑定现有状态，不需要再改 patcher 或后端。

## 2. 修改范围

已修改：

* `Avalonia_UI/ViewModels/MainWindowViewModel.cs`
* `Avalonia_UI.Tests/MainWindowViewModelWorkflowTests.cs`

未修改：

* `WorkflowSummaryView.axaml`
* `WorkflowDefinitionDraftNodePatcher`
* 后端 API
* localization 资源

## 3. 实现内容

新增状态：

```text
SelectedNewDraftNodeDefinition
```

选择节点定义时：

* 自动填充 `NewDraftNodeType`。
* 自动填充 `NewDraftNodeVersion`，空值时降级为 `1.0`。
* `NewDraftNodeDisplayName` 为空时自动填充定义显示名。
* `NewDraftNodeInstanceId` 为空或仍等于上一次自动建议值时，生成新的建议 ID。

自动建议规则：

```text
GenerateTestTableNode -> generate_test_table
FilterRowsNode -> filter_rows
```

如果当前 draft nodes 中已存在相同 ID，则追加数字后缀：

```text
generate_test_table
generate_test_table_2
generate_test_table_3
```

## 4. 降级边界

已保持：

* node catalog 为空或加载失败时，手动输入能力不受影响。
* 用户已经手动填写 `NewDraftNodeInstanceId` 时，选择节点定义不会覆盖。
* 重载 workflow definition 会重置新增节点输入状态。
* 新增节点成功后会重置新增节点输入状态。

## 5. 测试覆盖

新增 / 更新 `MainWindowViewModelWorkflowTests`：

* 选择 node definition 会填充 node type / version / display name / instance id。
* 选择 node definition 时会避开已有 node instance id 并追加后缀。
* 用户手动填写 node instance id 后不会被自动建议覆盖。

当前已运行：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "MainWindowViewModelWorkflowTests"
通过：58，失败：0，跳过：0

dotnet build Avalonia_UI\Avalonia_UI.sln --no-restore
成功，警告：0，错误：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：261，失败：0，跳过：0
```

## 6. 保留项

本阶段仍未完成：

* `WorkflowSummaryView.axaml` 中将 node type 输入增强为可选 node catalog 项。
* View 层保留手动输入降级。
* 连接 source / target 下拉选择。
* port 下拉与端口 schema 深校验。
* 桌面真实 smoke。

## 7. 下一小步建议

建议进入：

```text
WORKFLOW-EDIT-2.2c：
新增节点 View 接入前置复核 / Gemini 任务说明。
```

如果直接进入 XAML，应保持纯 View 改动：绑定 `NodeDefinitions` 与 `SelectedNewDraftNodeDefinition`，保留 `NewDraftNodeType` 手动输入，不引入 converter 或 code-behind。
