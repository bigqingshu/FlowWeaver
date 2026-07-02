# FlowWeaver WORKFLOW-EDIT-1.6：ViewModel 命令接入前置分析

> 文档状态：WORKFLOW-EDIT-1.6 前置分析完成
> 当前阶段：准备把结构化 patcher 接入 Avalonia ViewModel
> 不适用范围：本小步不实现命令、不改 XAML、不新增 UI 输入控件

## 1. 当前基础

WORKFLOW-EDIT-1.1 到 1.5 已经完成：

```text
WorkflowDefinitionDraftStructure 只读解析
MainWindowViewModel 只读 draft structure 状态
节点新增纯 patcher
节点删除 preflight / patcher
connection 新增 / 删除纯 patcher
```

这些能力都还没有接入 ViewModel 命令，也没有进入 XAML。

## 2. 命令接入必须复用的现有语义

结构化编辑命令必须继续复用：

```text
WorkflowDefinitionDraftJson
IsWorkflowDefinitionDraftDirty
WorkflowDefinitionValidationMessage
WorkflowDefinitionValidationErrorMessage
HasWorkflowDefinitionRevisionConflict
IsWorkflowDefinitionDraftBusy
ValidateWorkflowDefinitionDraftCommand
SaveWorkflowDefinitionDraftCommand
```

规则：

* 命令成功后只写回 `WorkflowDefinitionDraftJson`。
* `WorkflowDefinitionDraftJson` 的 setter 继续负责 dirty 和 validation invalidation。
* revision conflict 下结构化编辑命令不可用。
* validating / saving 期间结构化编辑命令不可用。
* 命令失败时写入 `WorkflowDefinitionValidationMessage` / `WorkflowDefinitionValidationErrorMessage`。
* 不新增后端调用。

## 3. 不建议一次性接入所有命令

虽然底层 patcher 已经支持：

```text
AddNode
DeleteNode
AddConnection
DeleteConnection
```

但 ViewModel 不建议一次接入全部命令。

原因：

* 节点新增需要输入状态和默认 config JSON。
* 节点删除需要选中 draft node，而当前 UI 选中的是 loaded detail node。
* connection 新增需要 source / target / port 输入状态。
* connection 删除需要选中 draft connection。
* 同时接入会扩大测试面，并且很快需要 XAML 输入设计。

## 4. 推荐命令接入顺序

### WORKFLOW-EDIT-1.6a

新增节点新增输入状态，不执行 patch。

建议状态：

```text
NewDraftNodeInstanceId
NewDraftNodeType
NewDraftNodeVersion
NewDraftNodeDisplayName
NewDraftNodeConfigJson
```

目标：

* 提供 ViewModel 可测试输入状态。
* 明确默认值策略。
* 不修改 draft。
* 不修改 XAML。

### WORKFLOW-EDIT-1.6b

接入 AddNode 命令。

范围：

* 调用 `WorkflowDefinitionDraftNodePatcher.AddNode`。
* 成功后写回 `WorkflowDefinitionDraftJson`。
* 失败后写入 validation message / error。
* revision conflict、busy、无 draft 时禁用。
* 不修改 XAML。

### WORKFLOW-EDIT-1.6c

接入 DeleteNode 命令前置状态。

范围：

* 明确使用 draft structure node 选择，还是临时按 node_instance_id 文本输入。
* 第一版建议先用 `SelectedWorkflowDefinitionDraftNodeInstanceId` 文本状态，避免与 loaded detail selection 混用。
* 不修改 XAML。

### WORKFLOW-EDIT-1.6d

接入 DeleteNode 命令。

范围：

* 调用 `WorkflowDefinitionDraftNodePatcher.DeleteNode`。
* 有 connection 依赖时显示 `NODE_HAS_CONNECTIONS`。
* 不做级联删除。

### WORKFLOW-EDIT-1.6e

connection 命令接入前置状态。

建议状态：

```text
NewDraftConnectionId
NewDraftConnectionSourceNodeId
NewDraftConnectionSourcePort
NewDraftConnectionTargetNodeId
NewDraftConnectionTargetPort
SelectedWorkflowDefinitionDraftConnectionId
```

### WORKFLOW-EDIT-1.6f

接入 AddConnection / DeleteConnection 命令。

范围：

* 调用 `WorkflowDefinitionDraftConnectionPatcher`。
* 不做端口 schema 深校验。
* 不修改 XAML。

## 5. 下一小步建议

建议下一步进入：

```text
WORKFLOW-EDIT-1.6a：
节点新增输入状态最小接入。
```

建议只新增 ViewModel 属性和测试：

* 默认 `NewDraftNodeVersion = "1.0"`。
* 默认 `NewDraftNodeConfigJson = "{}"`。
* 不调用 patcher。
* 不修改 `WorkflowDefinitionDraftJson`。
* 不修改 XAML。

这一步完成后，再进入 `WORKFLOW-EDIT-1.6b` 接入 AddNode 命令会更稳。
