# FlowWeaver UI-NODE-CONFIG-2h：ViewModel 只读 EditableDraft 状态接入

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：Avalonia schema 解析、可编辑草稿、输入字段 ViewModel、config 构建、Apply 命令和 WorkflowSummaryView 表单接入已经落地。
> 未实现：无本文件目标内的未实现项；专用富编辑器和更复杂字段控件仍按后续节点生态处理。
> 原因：当前实现完成了从 schema 到 draft config 写回的最小闭环。

> 文档状态：UI-NODE-CONFIG-2h 代码实现完成
> 当前阶段：只在 `MainWindowViewModel` 接入只读节点配置草稿状态
> 不适用范围：XAML 动态表单、Apply 按钮、workflow JSON 写回、后端 API 修改

## 1. 阶段目标

本阶段只把前置纯模型接入 ViewModel 状态层：

```text
WorkflowDefinitionDraftJson
+ SelectedWorkflowDefinitionNode
+ NodeDefinition config_schema
→ SelectedNodeConfigDraft
→ SelectedNodeConfigEditableDraft
```

当前 UI 仍只显示原有 summary 文案，不新增字段编辑控件。

## 2. 已完成内容

`MainWindowViewModel` 新增状态：

```text
SelectedNodeConfigDraft
SelectedNodeConfigEditableDraft
SelectedNodeConfigEditableDraftMessage
```

新增内部刷新方法：

```text
RefreshSelectedNodeConfigDraftState()
```

现有 `SelectedNodeConfigDraftSummaryText` 改为读取统一 message，保持原文案行为。

## 3. 刷新触发点

已接入以下刷新入口：

* `WorkflowDefinitionDetail` 变化。
* `SelectedWorkflowDefinitionNode` 变化。
* `WorkflowDefinitionDraftJson` 变化。
* node definitions 刷新成功或失败后。
* 语言切换后。
* 构造初始化时。

刷新规则：

| 条件 | 状态 |
| --- | --- |
| 没有 workflow detail 或没有选中节点 | draft 状态清空，message 为 no node selected |
| schema 不可用或 draft 不支持 | 保存 unsupported draft，editable draft 为空 |
| draft 支持 | 保存 draft，并派生 editable draft |

## 4. 测试覆盖

补充 `MainWindowViewModelWorkflowTests`：

* workflow 切换会清空 selected node config 状态。
* schema 未加载时 editable draft 不可用。
* node definitions 刷新后 editable draft 有字段。
* enum 候选值能从 schema 流到 ViewModel 状态。
* 切换 selected node 会刷新 editable draft。
* 修改 `WorkflowDefinitionDraftJson` 会重新派生 editable draft。

## 5. 明确未做

本阶段没有做：

* 不改 XAML。
* 不新增 Apply 命令。
* 不调用 `NodeConfigEditableDraftConfigBuilder`。
* 不调用 `NodeConfigDraftJsonPatcher`。
* 不写回 `WorkflowDefinitionDraftJson`。
* 不改变 Validate / Save / revision conflict 行为。

## 6. 验证结果

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "MainWindowViewModelWorkflowTests"
通过：39，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：206，失败：0，跳过：0
```

## 7. 下一小步建议

下一步不建议直接接 Apply。

建议先做：

```text
UI-NODE-CONFIG-2i：
最小可编辑输入状态边界评估，
明确用户修改字段值应落在哪个 ViewModel/model 状态中，
以及如何避免覆盖手写 WorkflowDefinitionDraftJson。
```

评估完成后，再决定是否进入：

```text
UI-NODE-CONFIG-2j：
ApplySelectedNodeConfigDraftCommand 最小接入。
```
