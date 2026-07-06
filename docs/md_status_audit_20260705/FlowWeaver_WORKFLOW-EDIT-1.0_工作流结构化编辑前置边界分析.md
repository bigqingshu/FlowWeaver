# FlowWeaver WORKFLOW-EDIT-1.0：工作流结构化编辑前置边界分析

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：结构化只读解析、节点新增/删除、connection 新增/删除、ViewModel 命令、View 接入、用户友好 warning/error、节点/connection 输入体验和 smoke 复核已经落地。
> 未实现：自由画布、拖拽连线、完整撤销/重做和复杂 DAG 自动重排未在本阶段实现。
> 原因：这些能力超出结构化编辑最小闭环，已作为后续体验方向保留。

> 文档状态：WORKFLOW-EDIT-1.0 前置边界分析完成
> 当前阶段：从节点配置编辑进入 workflow definition 结构化编辑
> 不适用范围：直接实现节点增删、连线编辑、图形化画布、后端 partial patch API、自动布局

## 1. 当前事实

当前 Avalonia UI 已经具备三类能力。

### 1.1 完整 JSON 草稿编辑

`WorkflowEditorView.axaml` 已提供完整 `WorkflowDefinitionDraftJson` 文本编辑入口，并复用现有命令：

```text
ValidateWorkflowDefinitionDraftCommand
SaveWorkflowDefinitionDraftCommand
```

当前保存路径仍是：

```text
WorkflowDefinitionDraftJson
-> JsonDocument.Parse
-> UpdateWorkflowAsync(workflow_id, name, definition, base_revision_id)
-> 后端 revision conflict / validation / save
```

因此，第一版结构化编辑不应绕开 `WorkflowDefinitionDraftJson`，也不应新增独立保存源。

### 1.2 Workflow 详情只读投影

`WorkflowDefinitionDetailViewModel` 当前从已加载的 workflow definition 中派生：

```text
Nodes
Connections
Revisions
RawDefinitionJson
```

这些集合目前是只读展示用途：

```text
WorkflowDefinitionDetail.Nodes
WorkflowDefinitionDetail.Connections
```

它们不是独立草稿状态，也不会自动代表用户正在编辑的 `WorkflowDefinitionDraftJson`。

### 1.3 节点 config 最小结构化编辑

UI-NODE-CONFIG-2 已完成已有节点实例 config 的最小结构化编辑闭环：

```text
Node definition config_schema
-> NodeConfigDraft
-> NodeConfigEditableDraft
-> SelectedNodeConfigEditableInputFields
-> ApplySelectedNodeConfigDraftCommand
-> NodeConfigDraftJsonPatcher
-> WorkflowDefinitionDraftJson
```

该能力只覆盖：

```text
编辑已有 node_instance_id 的 config
```

它不覆盖：

```text
新增节点
删除节点
修改节点基础字段
新增 connection
删除 connection
图形化编排
```

## 2. 必须保持的边界

WORKFLOW-EDIT-1 应继续遵守以下边界。

### 2.1 `WorkflowDefinitionDraftJson` 是唯一保存源

结构化编辑产生的结果必须最终写回 `WorkflowDefinitionDraftJson`。

理由：

* 现有 Validate / Save 已围绕完整 JSON 草稿建立。
* dirty 状态、校验失效、保存失败提示和 revision conflict 已依赖该字段。
* 后端当前提供的是 workflow definition 整体更新接口，不是局部 patch API。

### 2.2 revision conflict 继续阻断结构化写入

当前节点 config Apply 已在 `HasWorkflowDefinitionRevisionConflict` 下禁用。

后续节点增删和连线编辑也应保持相同规则：

```text
有 revision conflict
-> 禁止继续结构化修改
-> 保留用户草稿
-> 引导重新加载或人工处理
```

### 2.3 Validate 不作为 Save 的前置强制门

当前策略是宽松模式：

```text
Draft dirty
-> Save 可用
-> Save 时后端仍做校验
```

WORKFLOW-EDIT-1 不应单独改变该策略。结构化编辑只负责生成合法 JSON 草稿；最终合法性仍由 Validate / Save 路径兜底。

### 2.4 不新增后端 API

WORKFLOW-EDIT-1 第一轮不新增：

```text
PATCH /workflow-definition/nodes
PATCH /workflow-definition/connections
server-side draft session
server-side graph layout
```

原因是当前后端整体 update + revision 校验已经足够支撑最小桌面编辑链路。

## 3. WORKFLOW-EDIT-1 最小范围

WORKFLOW-EDIT-1 建议只做“结构化草稿编辑”。

可纳入：

* 从 `WorkflowDefinitionDraftJson` 解析 nodes / connections 的只读草稿结构。
* 暴露草稿节点和草稿连线的可读状态。
* 建立纯模型 patcher，修改 JSON 草稿。
* 先支持极小操作：新增节点、删除节点前置检查、connection 增删。
* ViewModel 命令只调用纯模型 patcher，再写回 `WorkflowDefinitionDraftJson`。

暂不纳入：

* 可视化画布。
* 拖拽布局。
* 自动布局。
* 复杂节点专用编辑器。
* array / object config 的结构化编辑。
* 多人协作合并。
* 后端局部 patch API。

## 4. WORKFLOW-EDIT-1 与 WORKFLOW-EDIT-2 分界

### 4.1 WORKFLOW-EDIT-1

目标是建立可靠的结构化 JSON 草稿操作边界。

推荐完成后具备：

```text
只读草稿结构解析
节点新增 patcher
节点删除 preflight / patcher
connection 新增 patcher
connection 删除 patcher
ViewModel 最小命令接入
结构化操作复用 dirty / validation invalidation / revision conflict
```

### 4.2 WORKFLOW-EDIT-2

目标是提升编辑体验和视觉表达。

建议后置到 WORKFLOW-EDIT-2 的能力：

```text
节点图形化画布
拖拽连线
自动布局
字段级错误视觉回填
节点专用编辑器注册体系
复杂 config 类型表单
草稿冲突合并辅助
批量编辑
撤销/重做
```

## 5. 推荐执行顺序

建议后续小步按以下顺序推进。

### WORKFLOW-EDIT-1.1

建立 `WorkflowDefinitionDraftStructure` 只读解析模型和测试。

范围：

* 输入 `WorkflowDefinitionDraftJson`。
* 输出 nodes / connections 摘要。
* 保留 parse warning。
* 不修改 ViewModel。
* 不修改 XAML。

### WORKFLOW-EDIT-1.2

接入 ViewModel 只读草稿结构状态。

范围：

* 从 `WorkflowDefinitionDraftJson` 派生 draft nodes / draft connections。
* 与 `WorkflowDefinitionDetail.Nodes` 的 loaded definition 只读投影区分。
* 确认 JSON 手动编辑后结构投影刷新。
* 不新增修改命令。

### WORKFLOW-EDIT-1.3

建立节点新增纯 patcher。

范围：

* 输入当前 draft JSON、node type、node version、node_instance_id、display_name、初始 config。
* 输出更新后的 draft JSON。
* 校验重复 `node_instance_id`。
* 不接 UI 按钮。

### WORKFLOW-EDIT-1.4

建立节点删除 preflight / patcher。

范围：

* 删除前识别受影响 connections。
* 第一版可要求无连接节点才能删除，或显式返回阻断 warning。
* 不做级联删除默认策略，除非后续明确确认。

### WORKFLOW-EDIT-1.5

建立 connection 新增 / 删除纯 patcher。

范围：

* 校验 source / target node 存在。
* 校验 connection_id 不重复。
* 第一版不做端口 schema 深校验。

### WORKFLOW-EDIT-1.6

接入最小 ViewModel 命令。

范围：

* 命令调用纯 patcher。
* 写回 `WorkflowDefinitionDraftJson`。
* 复用 dirty / validation invalidation。
* revision conflict 下禁用。
* 仍不做画布。

### WORKFLOW-EDIT-1.7

补最小 View 协作说明，交给 Gemini 只改 View。

范围：

* 只说明按钮、列表、输入项绑定。
* 不要求 Gemini 修改 ViewModel 或模型。
* 不引入 converters。

## 6. 下一小步结论

建议下一步进入：

```text
WORKFLOW-EDIT-1.1：
WorkflowDefinitionDraftStructure 只读解析模型和测试。
```

这是最稳的第一步，因为它先把“当前 JSON 草稿到底包含哪些节点和连线”从 loaded detail 只读视图区分出来，后续新增、删除和连线 patch 才有稳定输入。
