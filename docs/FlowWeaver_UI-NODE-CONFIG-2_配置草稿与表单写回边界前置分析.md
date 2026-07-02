# FlowWeaver UI-NODE-CONFIG-2：配置草稿与表单写回边界前置分析

> 文档状态：UI-NODE-CONFIG-2 前置分析完成
> 当前阶段：只确认配置草稿、动态表单和 workflow JSON 写回边界
> 不适用范围：直接实现动态表单、保存节点配置、节点新增删除、连接编辑、画布编辑

## 1. 背景

当前节点配置主线已经完成：

* 后端 `GET /api/v1/node-definitions` 返回 `config_schema_version` 和 `config_schema`。
* Avalonia 已能解析 `NodeDefinitionDto.ConfigSchema`。
* 节点目录已显示只读配置摘要。

下一步如果直接生成配置表单，会碰到这些边界：

* 当前正式保存入口仍是 `WorkflowDefinitionDraftJson`。
* Save 必须继续带 `base_revision_id`，不能绕过 revision conflict。
* Validate / Save / Dirty 状态已经绑定 JSON 草稿。
* 当前 UI 还没有“选中 workflow 节点实例”的独立状态。
* schema 只来自节点类型定义，而实际 config 属于 workflow definition 中的某个 node instance。

因此 `UI-NODE-CONFIG-2` 不应直接做大表单，应该先把配置草稿和写回边界固定下来。

## 2. 当前 UI 结构事实

当前 Workflow 页面结构：

```text
WorkflowPage
├─ WorkflowListView
├─ WorkflowSummaryView
│  ├─ Workflow details / revisions
│  ├─ nodes list
│  └─ connections list
└─ 右侧区域
   ├─ WorkflowEditorView
   │  └─ WorkflowDefinitionDraftJson TextBox
   └─ WorkflowNodeCatalogView
      └─ NodeDefinitions 只读目录与 config schema 摘要
```

现有保存链路：

```text
WorkflowDefinitionDraftJson
→ ValidateWorkflowDefinitionDraftCommand
→ SaveWorkflowDefinitionDraftCommand
→ UpdateWorkflowAsync(workflow_id, definition, base_revision_id)
→ 后端 revision conflict 保护
```

现有节点目录链路：

```text
GET /api/v1/node-definitions
→ NodeDefinitionDto
→ NodeConfigSchemaParser
→ NodeDefinitionListItemViewModel.ConfigSchemaSummaryText
```

注意：

```text
NodeDefinition 是节点类型目录。
WorkflowDefinitionDetail.Nodes 是工作流中的节点实例。
配置表单必须编辑节点实例 config，而不是编辑节点类型定义。
```

## 3. UI-NODE-CONFIG-2 的最小职责

建议 `UI-NODE-CONFIG-2` 拆成前置分析和后续很小代码小步。

本前置分析只确认：

* 需要一个“选中 workflow node instance”的状态。
* 需要一个从 `WorkflowDefinitionDraftJson` 读取节点 config 的草稿模型。
* 需要一个把草稿写回 `WorkflowDefinitionDraftJson` 的单向提交动作。
* 动态表单控件只能先支持基础字段。
* array / object / unsupported 必须回退 JSON 或只读。
* 保存仍然只走现有 `SaveWorkflowDefinitionDraftCommand`。

本阶段不实现：

* 不新增动态控件。
* 不新增保存接口。
* 不直接修改后端 workflow API。
* 不绕过 `WorkflowDefinitionDraftJson`。
* 不改变 revision conflict 处理。

## 4. 建议状态模型

后续 `UI-NODE-CONFIG-2a` 可先只新增模型和测试：

```text
SelectedWorkflowDefinitionNode
SelectedNodeConfigSchema
NodeConfigDraft
NodeConfigDraftField
NodeConfigDraftStatus
```

建议职责：

| 模型 | 职责 |
| --- | --- |
| `WorkflowDefinitionNodeListItemViewModel` | 表示 workflow 中的节点实例，后续可被选中 |
| `NodeConfigDraft` | 某个节点实例当前 config 的 UI 草稿 |
| `NodeConfigDraftField` | 单个 schema field 的草稿值和 warning |
| `NodeConfigDraftStatus` | Supported / ReadOnly / JsonFallback / Unsupported |

第一版不要把这些模型放进 HTTP DTO。

## 5. 节点实例选择边界

当前 `WorkflowDefinitionDetail.Nodes` 只是只读列表，没有选中状态。

建议后续最小顺序：

```text
UI-NODE-CONFIG-2a
只新增 SelectedWorkflowDefinitionNode 状态和测试。
不显示表单。

UI-NODE-CONFIG-2b
基于选中节点 + node definition catalog 找到 schema。
只生成 NodeConfigDraft 模型。
不显示表单。

UI-NODE-CONFIG-2c
只读展示选中节点 config draft 摘要。
不写回 JSON。
```

这样可以避免：

* 还没有选中节点就生成表单。
* 用节点类型目录误改工作流节点实例。
* 异步刷新 node-definitions 覆盖 workflow draft。

## 6. 配置草稿读取边界

读取来源必须是：

```text
WorkflowDefinitionDraftJson
```

而不是：

```text
WorkflowDefinitionDetail.RawDefinitionJson
```

原因：

* 用户可能已经在 JSON 草稿里手动修改。
* 保存按钮 dirty 状态基于 `WorkflowDefinitionDraftJson`。
* 结构化配置编辑必须与 JSON 草稿保持同一事实源。

读取建议：

```text
1. Parse WorkflowDefinitionDraftJson。
2. 找到 nodes[] 中 node_instance_id 匹配的节点。
3. 读取 node.config；缺失时视为 {}。
4. 结合 NodeConfigSchemaDescriptor 生成 NodeConfigDraft。
```

如果 JSON 无效：

```text
不生成配置草稿。
显示 JSON invalid 状态。
不覆盖用户当前文本。
```

## 7. 写回边界

写回必须是显式动作，建议后续命名：

```text
ApplySelectedNodeConfigDraftCommand
```

写回行为：

```text
NodeConfigDraft
→ 更新 WorkflowDefinitionDraftJson 中对应 node.config
→ 触发 OnWorkflowDefinitionDraftJsonChanged
→ IsWorkflowDefinitionDraftDirty 更新
→ Validate 结果失效
→ 用户仍需点击 Save
```

不能做：

* 字段编辑时自动保存到后端。
* 字段编辑时绕过 `WorkflowDefinitionDraftJson`。
* Apply 后自动调用 Save。
* Apply 后清空 revision conflict。
* Save 时换用新的 API。

## 8. 字段控件第一版边界

第一版可编辑字段类型建议：

| schema type | UI-NODE-CONFIG-2 可否编辑 | 说明 |
| --- | --- | --- |
| `string` | 可以 | TextBox |
| `integer` | 可以 | TextBox + integer parse，或后续 NumericUpDown |
| `number` | 可以 | TextBox + number parse |
| `boolean` | 可以 | CheckBox |
| `enum` | 可以 | ComboBox |
| `array` | 暂不编辑 | 先 JSON fallback 或只读摘要 |
| `object` | 暂不编辑 | 先 JSON fallback |
| `unsupported` | 不编辑 | JSON fallback |

第一版校验只在 UI 草稿层提示：

* 必填为空。
* integer / number 解析失败。
* enum 不在候选值。
* minimum 不满足。

但这不替代后端 Validate。

## 9. JSON fallback 边界

需要保留三层 fallback：

```text
1. 整个 workflow 仍可用 WorkflowDefinitionDraftJson 直接编辑。
2. 某个节点 config 可后续提供 JSON fallback。
3. array / object / unsupported 字段不强行生成不成熟控件。
```

若 schema 不支持：

```text
显示 schema 不支持或 JSON fallback 状态。
不要隐藏节点。
不要禁用整个 workflow 编辑。
```

## 10. 与 Validate / Save 的关系

结构化配置编辑只改变草稿，不直接改变保存协议。

现有链路必须保持：

```text
ValidateWorkflowDefinitionDraftCommand
SaveWorkflowDefinitionDraftCommand
WORKFLOW_REVISION_CONFLICT 保留用户草稿
```

后续测试必须覆盖：

* Apply config draft 后 `IsWorkflowDefinitionDraftDirty == true`。
* Apply config draft 后 Save command 可用条件仍沿用现有逻辑。
* 后端 revision conflict 后不清空结构化编辑产生的 JSON。
* JSON 无效时结构化草稿不可生成，但原文本保留。

## 11. 后端关系

`UI-NODE-CONFIG-2` 不要求后端改动。

原因：

* 后端已经提供 node definition schema。
* workflow update API 已经支持完整 definition 更新。
* config 静态校验还没有进入后端主线。

后端 config validation 可作为后续独立阶段：

```text
WORKFLOW-VALIDATION-SCHEMA-1
```

不要把它混进 UI-NODE-CONFIG-2。

## 12. Gemini 视图协作边界

如果让 Gemini 做 View 层，建议先给它以下边界：

```text
只做选中节点配置摘要或只读草稿视图。
不要实现 Apply。
不要实现动态编辑控件。
不要改 Save / Validate 按钮。
不要替换 WorkflowEditorView 的 JSON TextBox。
不要改 WorkflowPage 三列主体结构。
```

真正进入表单前，Codex 应先落模型和测试，再让 Gemini 做纯 View 拆分或展示。

## 13. 建议下一小步

```text
UI-NODE-CONFIG-2a：
新增 SelectedWorkflowDefinitionNode 前置状态和测试，
允许在 WorkflowDefinitionDetail.Nodes 中选择节点实例，
不生成配置表单，不写回 JSON。
```

然后：

```text
UI-NODE-CONFIG-2b：
新增 NodeConfigDraft 纯模型和 builder 测试，
从 WorkflowDefinitionDraftJson + selected node + node definition schema 生成草稿。

UI-NODE-CONFIG-2c：
展示选中节点 config draft 只读摘要。

UI-NODE-CONFIG-2d：
评估最小 Apply 写回 WorkflowDefinitionDraftJson。
```

## 14. UI-NODE-CONFIG-2 前置验收标准

本阶段完成标准：

* 明确节点类型定义和节点实例 config 的区别。
* 明确配置草稿读取来源是 `WorkflowDefinitionDraftJson`。
* 明确写回只能回到 `WorkflowDefinitionDraftJson`，再走现有 Validate / Save。
* 明确第一版字段控件支持范围。
* 明确 array / object / unsupported 的 fallback。
* 明确不改后端。
* 明确不直接实现动态表单。
