# FlowWeaver WORKFLOW-EDIT-2.3a：connection source / target / id 输入体验前置分析

> 文档状态：WORKFLOW-EDIT-2.3a 前置分析完成
> 当前阶段：结构化编辑 connection 输入体验收口
> 不适用范围：port 下拉、端口 schema 深校验、图形画布、后端 API 改动

## 1. 背景

WORKFLOW-EDIT-2.2 已完成新增节点的 node type 选择与 node instance id 自动建议。当前 connection 新增仍需要用户手动输入：

```text
NewDraftConnectionId
NewDraftConnectionSourceNodeId
NewDraftConnectionSourcePort
NewDraftConnectionTargetNodeId
NewDraftConnectionTargetPort
```

其中 source / target node id 可以基于当前 draft nodes 提供选择；connection id 可以基于 source / target 自动建议。

## 2. 当前可复用能力

| 能力 | 现状 | 可复用方式 |
| --- | --- | --- |
| 草稿结构 | `WorkflowDefinitionDraftStructure` | 提供当前 draft nodes / connections |
| source / target 输入 | `NewDraftConnectionSourceNodeId` / `NewDraftConnectionTargetNodeId` | 继续作为 patcher 输入 |
| connection id 输入 | `NewDraftConnectionId` | 继续作为 patcher 输入 |
| connection patcher | `WorkflowDefinitionDraftConnectionPatcher` | 保持行为不变 |
| View 结构测试 | `WorkflowSummaryViewStructureTests` | 覆盖后续 ComboBox 绑定 |

## 3. 建议 ViewModel 最小方案

建议下一小步只做 ViewModel 状态，不改 XAML：

```text
SelectedNewDraftConnectionSourceNode
SelectedNewDraftConnectionTargetNode
```

选择 source node 时：

* 设置 `NewDraftConnectionSourceNodeId`。
* 如果 source / target 都存在，并且 `NewDraftConnectionId` 为空或仍等于上一次自动建议值，则生成新的 connection id。

选择 target node 时：

* 设置 `NewDraftConnectionTargetNodeId`。
* 如果 source / target 都存在，并且 `NewDraftConnectionId` 为空或仍等于上一次自动建议值，则生成新的 connection id。

connection id 建议规则：

```text
source_to_filter
source_to_filter_2
```

建议 ID 应避开当前 draft connections 中已有的 `connection_id`。

## 4. 降级边界

必须保持：

* draft structure 不可用时，用户仍可手动输入 source / target node id。
* 用户手动填写 `NewDraftConnectionId` 后，不应被自动建议覆盖。
* source / target port 仍保留手动输入。
* 不根据 node type 或端口 schema 自动推断 port。
* 不校验 source / target port 是否存在。

## 5. 不进入本小步的内容

本小步不做：

* `WorkflowSummaryView.axaml` ComboBox 接入。
* source / target port 下拉。
* port 类型兼容校验。
* 自动连接推荐。
* 图形画布或拖拽连线。

## 6. 测试建议

下一小步应补充 `MainWindowViewModelWorkflowTests`：

* 选择 source node 会填充 `NewDraftConnectionSourceNodeId`。
* 选择 target node 会填充 `NewDraftConnectionTargetNodeId`。
* source / target 均存在时生成 connection id。
* 已有重复 connection id 时自动追加后缀。
* 用户已有手动 connection id 时不覆盖。
* draft nodes 删除后，已选 source / target 节点状态应按现有草稿刷新边界清理或降级。

## 7. 建议执行顺序

```text
WORKFLOW-EDIT-2.3b：
connection source / target 选择状态与 connection id 自动建议。

WORKFLOW-EDIT-2.3c：
connection View 接入任务说明。

WORKFLOW-EDIT-2.3d：
connection View 最小接入。

WORKFLOW-EDIT-2.3e：
connection 输入体验后置复核。
```

2.3 完成后，再决定是否进入桌面真实 smoke；port 下拉和深校验继续后置。
