# FlowWeaver WORKFLOW-EDIT-1.6g：结构化编辑命令后置复核

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：结构化只读解析、节点新增/删除、connection 新增/删除、ViewModel 命令、View 接入、用户友好 warning/error、节点/connection 输入体验和 smoke 复核已经落地。
> 未实现：自由画布、拖拽连线、完整撤销/重做和复杂 DAG 自动重排未在本阶段实现。
> 原因：这些能力超出结构化编辑最小闭环，已作为后续体验方向保留。

> 文档状态：WORKFLOW-EDIT-1.6g 后置复核完成
> 当前阶段：WORKFLOW-EDIT-1 ViewModel 命令最小闭环复核
> 不适用范围：XAML 改动、Gemini View 实施、画布编辑、端口 schema 深校验

## 1. 完成矩阵

| 小步 | 内容 | 状态 | 证据 |
| --- | --- | --- | --- |
| 1.0 | 工作流结构化编辑前置边界分析 | 已完成 | `FlowWeaver_WORKFLOW-EDIT-1.0...md` |
| 1.1 | `WorkflowDefinitionDraftStructure` 只读解析 | 已完成 | `WorkflowDefinitionDraftStructureBuilderTests` |
| 1.2 | ViewModel 只读 draft structure 状态 | 已完成 | `MainWindowViewModelWorkflowTests` |
| 1.3 | 节点新增纯 patcher | 已完成 | `WorkflowDefinitionDraftNodePatcherTests` |
| 1.4 | 节点删除 preflight / patcher | 已完成 | `WorkflowDefinitionDraftNodePatcherTests` |
| 1.5 | connection 新增 / 删除纯 patcher | 已完成 | `WorkflowDefinitionDraftConnectionPatcherTests` |
| 1.6a | 节点新增输入状态 | 已完成 | `MainWindowViewModelWorkflowTests` |
| 1.6b | AddNode 命令 | 已完成 | `MainWindowViewModelWorkflowTests` |
| 1.6c | DeleteNode 前置选择状态 | 已完成 | `MainWindowViewModelWorkflowTests` |
| 1.6d | DeleteNode 命令 | 已完成 | `MainWindowViewModelWorkflowTests` |
| 1.6e | connection 前置输入/选择状态 | 已完成 | `MainWindowViewModelWorkflowTests` |
| 1.6f | AddConnection / DeleteConnection 命令 | 已完成 | `MainWindowViewModelWorkflowTests` |

## 2. 当前能力

当前 ViewModel 已具备结构化编辑最小命令：

```text
AddWorkflowDefinitionDraftNodeCommand
DeleteWorkflowDefinitionDraftNodeCommand
AddWorkflowDefinitionDraftConnectionCommand
DeleteWorkflowDefinitionDraftConnectionCommand
```

所有命令成功后都只写回：

```text
WorkflowDefinitionDraftJson
```

并复用现有：

```text
dirty
validation invalidation
draft structure refresh
revision conflict guard
busy guard
Save workflow draft
Validate workflow draft
```

## 3. 当前保护边界

已确认：

* revision conflict 下结构化编辑命令不可用。
* validate / save busy 下结构化编辑命令不可用。
* 未加载 workflow definition 时命令不可用。
* AddNode 失败不清空用户输入。
* DeleteNode 失败不清空选择状态。
* AddConnection 失败不清空用户输入。
* DeleteConnection 失败不清空选择状态。
* DeleteNode 遇到 connection 依赖时返回 `NODE_HAS_CONNECTIONS`，不做级联删除。
* connection 只校验 source / target node 存在和端口非空，不做端口 schema 深校验。

## 4. 验证证据

最近验证：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "MainWindowViewModelWorkflowTests"
通过：54，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：256，失败：0，跳过：0
```

## 5. 保留项

当前尚未完成：

* XAML 输入区和按钮。
* Gemini View 协作说明。
* 用户友好的 patcher warning 文案映射。
* 自动生成 node_instance_id。
* 自动生成 connection_id。
* node type 下拉选择。
* source / target node 下拉选择。
* port 下拉选择或 schema 深校验。
* 连接依赖下的“先删连接再删节点”引导。
* 图形化画布。

## 6. 下一小步建议

建议下一步不要继续扩展命令逻辑，而是进入：

```text
WORKFLOW-EDIT-1.7：
结构化编辑 View 协作说明。
```

建议只写 Gemini 可执行说明，不直接改 XAML：

* 说明新增节点输入字段绑定。
* 说明新增连接输入字段绑定。
* 说明删除节点 / 删除连接按钮绑定。
* 明确不允许 Gemini 修改 ViewModel、模型、后端和测试。
* 明确不引入 converters。
* 明确第一版只做表单区，不做画布。

如果要先继续由 Codex 实施 UI 辅助属性，也应拆成 `WORKFLOW-EDIT-1.7a`，不要把 View 协作和 ViewModel 再混在一起。
