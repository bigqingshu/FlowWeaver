# FlowWeaver WORKFLOW-EDIT-2.2a：node type 与 node instance id 输入体验前置分析

> 文档状态：WORKFLOW-EDIT-2.2a 前置分析完成
> 当前阶段：结构化编辑节点新增体验收口
> 不适用范围：XAML 接入、ComboBox 视觉调整、后端 API 改动、port schema 深校验

## 1. 背景

WORKFLOW-EDIT-2.1 已经完成结构化编辑失败提示的用户友好映射。当前新增节点表单仍需要用户手动输入：

```text
NewDraftNodeInstanceId
NewDraftNodeType
NewDraftNodeVersion
NewDraftNodeDisplayName
NewDraftNodeConfigJson
```

这会带来两个主要问题：

* `node_type` 容易拼写错误。
* `node_instance_id` 容易为空或重复。

## 2. 当前可复用能力

现有能力已经足够支撑 2.2 的最小体验增强：

| 能力 | 现状 | 可复用方式 |
| --- | --- | --- |
| 节点目录 API | `ListNodeDefinitionsAsync` 已接入 | 继续由 `RefreshNodeDefinitionsCommand` 加载 |
| 节点目录状态 | `MainWindowViewModel.NodeDefinitions` | 作为新增节点的候选 node type 来源 |
| 节点目录展示模型 | `NodeDefinitionListItemViewModel` | 可直接作为 ComboBox `ItemsSource` 项 |
| 草稿结构 | `WorkflowDefinitionDraftStructure` | 用于生成不重复的 node instance id |
| 新增节点命令 | `AddWorkflowDefinitionDraftNodeCommand` | 继续使用现有输入字段 |

## 3. 最小 ViewModel 方案

建议下一小步只做 ViewModel 状态，不改 XAML：

```text
SelectedNewDraftNodeDefinition
```

选择节点定义时：

* 将 `NewDraftNodeType` 设置为所选定义的 `NodeType`。
* 将 `NewDraftNodeVersion` 设置为所选定义的 `NodeVersion`。
* 如果 `NewDraftNodeDisplayName` 为空，可填入所选定义的 `DisplayName`。
* 如果 `NewDraftNodeInstanceId` 为空，或仍等于上一次自动建议值，则生成新的建议 ID。

生成建议 ID 时：

* 优先使用 `NodeType` 派生。
* 转成小写 snake case。
* 避免与当前 draft nodes 重复。
* 如果重复，追加数字后缀。

示例：

```text
GenerateTestTableNode
-> generate_test_table
-> generate_test_table_2
```

## 4. 降级边界

必须保留手动输入：

* node catalog 未加载时，用户仍可手动输入 node type / version。
* node catalog 加载失败时，用户仍可手动输入。
* 用户手动改写 `NewDraftNodeInstanceId` 后，再刷新 catalog 不应覆盖用户输入。
* 用户手动改写 `NewDraftNodeType` 后，不强制反选 catalog 项。

## 5. 不进入本小步的内容

本小步不做：

* `WorkflowSummaryView.axaml` ComboBox 接入。
* Gemini View 修改任务说明。
* 自动生成 config schema 表单。
* port 下拉。
* connection source / target 下拉。
* 自动添加 connection。

## 6. 测试建议

下一小步应补充 `MainWindowViewModelWorkflowTests`：

* 选择 node definition 会填充 node type / version / display name。
* 选择 node definition 会生成不重复的 node instance id。
* 已有重复 node id 时自动追加后缀。
* 用户已有手动 node instance id 时不覆盖。
* catalog 加载失败或为空时仍可手动输入并执行现有新增命令。

## 7. 下一小步建议

建议进入：

```text
WORKFLOW-EDIT-2.2b：
SelectedNewDraftNodeDefinition 与 node instance id 自动建议 ViewModel 状态。
```

完成 2.2b 后，再决定是否进入 View 接入小步；View 接入应尽量只把 node type 输入从纯 TextBox 增强为可选目录项，而不是移除手动输入能力。
