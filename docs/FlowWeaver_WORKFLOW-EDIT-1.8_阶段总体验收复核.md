# FlowWeaver WORKFLOW-EDIT-1.8：阶段总体验收复核

> 文档状态：WORKFLOW-EDIT-1 阶段总体验收复核完成
> 当前阶段：工作流结构化编辑第一阶段收口
> 不适用范围：WORKFLOW-EDIT-2、桌面真实截图 smoke、后端 API 改动、节点配置 schema 深校验

## 1. 阶段目标

WORKFLOW-EDIT-1 的目标是让工作流定义从纯 JSON 草稿编辑，推进到“结构化辅助编辑”的最小闭环：

* 保持 `WorkflowDefinitionDraftJson` 作为唯一保存源。
* 提供只读草稿结构解析，供 ViewModel 和 View 展示。
* 提供节点新增、节点删除、connection 新增、connection 删除的纯 patcher。
* 将 patcher 接入 ViewModel 命令，复用现有 dirty、validation invalidation、busy guard 和 revision conflict 边界。
* 将最小结构化编辑表单接入 `WorkflowSummaryView`。

## 2. 完成矩阵

| 小步 | 内容 | 状态 | 主要证据 |
| --- | --- | --- | --- |
| 1.0 | 工作流结构化编辑前置边界分析 | 已完成 | `docs/FlowWeaver_WORKFLOW-EDIT-1.0_工作流结构化编辑前置边界分析.md` |
| 1.1 | `WorkflowDefinitionDraftStructure` 只读解析模型 | 已完成 | `WorkflowDefinitionDraftStructureTests` |
| 1.2 | ViewModel 只读草稿结构状态接入 | 已完成 | `MainWindowViewModelWorkflowTests` |
| 1.3 | 节点新增纯 patcher | 已完成 | `WorkflowDefinitionDraftNodePatcherTests` |
| 1.4 | 节点删除 preflight 与 patcher | 已完成 | `WorkflowDefinitionDraftNodePatcherTests` |
| 1.5 | connection 新增 / 删除纯 patcher | 已完成 | `WorkflowDefinitionDraftConnectionPatcherTests` |
| 1.6 | ViewModel 命令接入前置分析 | 已完成 | `docs/FlowWeaver_WORKFLOW-EDIT-1.6_ViewModel命令接入前置分析.md` |
| 1.6a | 节点新增输入状态 | 已完成 | `MainWindowViewModelWorkflowTests` |
| 1.6b | AddNode 命令 | 已完成 | `MainWindowViewModelWorkflowTests` |
| 1.6c | DeleteNode 选择状态 | 已完成 | `MainWindowViewModelWorkflowTests` |
| 1.6d | DeleteNode 命令 | 已完成 | `MainWindowViewModelWorkflowTests` |
| 1.6e | connection 输入 / 选择状态 | 已完成 | `MainWindowViewModelWorkflowTests` |
| 1.6f | AddConnection / DeleteConnection 命令 | 已完成 | `MainWindowViewModelWorkflowTests` |
| 1.6g | 结构化编辑命令后置复核 | 已完成 | `docs/FlowWeaver_WORKFLOW-EDIT-1.6g_结构化编辑命令后置复核.md` |
| 1.7 | 结构化编辑 View 协作说明 | 已完成 | `docs/FlowWeaver_WORKFLOW-EDIT-1.7_结构化编辑View协作说明.md` |
| 1.7a | 结构化编辑 View 辅助文本属性 | 已完成 | `MainWindowViewModelLocalizationTests` |
| 1.7b | Gemini 结构化编辑 View 修改任务说明 | 已完成 | `docs/FlowWeaver_WORKFLOW-EDIT-1.7b_Gemini结构化编辑View修改任务说明.md` |
| 1.7c | `WorkflowSummaryView` 结构化编辑表单接入 | 已完成 | `WorkflowSummaryViewStructureTests` |
| 1.7d | 结构化编辑 View 后置复核 | 已完成 | `docs/FlowWeaver_WORKFLOW-EDIT-1.7d_结构化编辑View后置复核.md` |

## 3. 已固化边界

当前已固化：

* `WorkflowDefinitionDraftJson` 仍是保存接口唯一输入。
* 结构化命令只修改草稿 JSON，不直接写后端。
* 草稿变更会复用现有 dirty 和 validation invalidation 机制。
* 保存 revision 冲突保护仍由既有保存流程负责。
* `WorkflowDefinitionDetail.Nodes` / `WorkflowDefinitionDetail.Connections` 继续作为后端已加载定义的只读投影。
* draft selection 与 loaded detail selection 分离。
* DeleteNode 不级联删除 connection，存在依赖时由 `NODE_HAS_CONNECTIONS` 阻断。
* Connection patcher 当前只校验 source / target node 存在和 port 非空，不做端口 schema 深校验。
* View 第一版是表单式最小接入，不包含画布、拖拽、自动布局或复杂图编辑。

## 4. 测试与验证

最近一次完整验证记录：

```text
dotnet build Avalonia_UI\Avalonia_UI.sln --no-restore
成功，警告：0，错误：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "WorkflowSummaryViewStructureTests|MainWindowViewModelWorkflowTests|MainWindowViewModelLocalizationTests"
通过：81，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：257，失败：0，跳过：0
```

本次 1.8 只做文档复核，不新增源码或 XAML 改动。

## 5. 当前不支持能力

WORKFLOW-EDIT-1 明确不包含：

* 桌面真实截图 / 手动 smoke。
* 用户友好 warning / error 映射。
* node type 下拉选择。
* source / target node 下拉选择。
* port 下拉选择。
* 端口 schema 深校验。
* 自动生成 node_instance_id / connection_id。
* “先删连接再删节点”的引导式交互。
* 图形化画布、拖拽连线、自动布局。
* WORKFLOW-EDIT-2 的完整可用性体验。

## 6. 下一阶段建议

建议不要直接把 WORKFLOW-EDIT-2 做成大步。更稳的顺序是：

```text
WORKFLOW-EDIT-2.0：
结构化编辑可用性缺口边界分析。

WORKFLOW-EDIT-2.1：
用户友好 warning / error 映射。

WORKFLOW-EDIT-2.2：
node type 与 node instance id 输入体验收口。

WORKFLOW-EDIT-2.3：
connection source / target / port 选择体验收口。

WORKFLOW-EDIT-2.4：
桌面真实 smoke 与后置复核。
```

如果继续保持“最小风险优先”，下一小步建议先进入 `WORKFLOW-EDIT-2.0`，只做边界分析和清单，不直接改代码。
