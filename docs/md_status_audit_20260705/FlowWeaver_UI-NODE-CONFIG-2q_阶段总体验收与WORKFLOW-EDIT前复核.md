# FlowWeaver UI-NODE-CONFIG-2q：阶段总体验收与 WORKFLOW-EDIT 前复核

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：Avalonia schema 解析、可编辑草稿、输入字段 ViewModel、config 构建、Apply 命令和 WorkflowSummaryView 表单接入已经落地。
> 未实现：无本文件目标内的未实现项；专用富编辑器和更复杂字段控件仍按后续节点生态处理。
> 原因：当前实现完成了从 schema 到 draft config 写回的最小闭环。

> 文档状态：UI-NODE-CONFIG-2q 总体验收复核完成
> 当前阶段：节点配置主线收口，准备进入 WORKFLOW-EDIT 前置边界分析
> 不适用范围：直接实现节点增删、连线编辑、画布编辑、后端 workflow patch API

## 1. 节点配置主线完成矩阵

| 小步 | 内容 | 状态 | 证据 |
| --- | --- | --- | --- |
| 2e | `NodeConfigEditableDraft` 纯模型 | 已完成 | `NodeConfigEditableDraftBuilderTests` |
| 2f | editable draft 转 config JSON | 已完成 | `NodeConfigEditableDraftConfigBuilderTests` |
| 2g | ViewModel 接入边界评估 | 已完成 | `FlowWeaver_UI-NODE-CONFIG-2g...md` |
| 2h | `SelectedNodeConfigDraft` / `SelectedNodeConfigEditableDraft` 状态 | 已完成 | `MainWindowViewModelWorkflowTests` |
| 2i | 可编辑输入状态边界评估 | 已完成 | `FlowWeaver_UI-NODE-CONFIG-2i...md` |
| 2j | 输入字段 ViewModel 状态 | 已完成 | `NodeConfigEditableFieldInputViewModelTests` |
| 2k | 输入字段集合转 config 适配层 | 已完成 | `NodeConfigEditableFieldInputConfigBuilderTests` |
| 2l | Apply 命令最小接入 | 已完成 | `MainWindowViewModelWorkflowTests` |
| 2m | View 协作说明 | 已完成 | `FlowWeaver_UI-NODE-CONFIG-2m...md` |
| 2n | View 辅助属性 | 已完成 | `NodeConfigEditableFieldInputViewModelTests` |
| 2o | `WorkflowSummaryView` 表单接入 | 已完成 | `WorkflowSummaryViewStructureTests` |
| 2p | 后置复核 | 已完成 | build + targeted/full tests |

## 2. 当前能力

当前已具备：

* 后端 node definition 可暴露 `config_schema_version` / `config_schema`。
* Avalonia 可解析 schema 支持子集。
* Workflow 节点实例可选中。
* 选中节点可根据 schema 派生可编辑字段。
* UI 可显示 string / integer / number / enum / boolean 字段。
* 用户修改字段后可 Apply 到 `WorkflowDefinitionDraftJson`。
* Apply 只改本地 draft，不调用后端。
* Save 仍走现有 workflow definition update + revision 校验。
* revision conflict 下 Apply 不可用。
* schema 未加载或无可编辑字段时 Apply 不可用。

## 3. 验证证据

最近验证：

```text
dotnet build Avalonia_UI\Avalonia_UI.sln --no-restore
成功，警告：0，错误：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "WorkflowSummaryViewStructureTests|MainWindowViewModelWorkflowTests"
通过：46，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：216，失败：0，跳过：0
```

## 4. 保留项

以下能力未完成，但不属于当前节点配置最小主线的阻断项：

* 真实桌面截图/手动 smoke 还未执行。
* 字段级错误没有高质量视觉回填。
* array / object / unsupported 仍是 JSON fallback，不做结构化编辑。
* 没有节点专用编辑器注册体系。
* 没有 workflow 节点增删。
* 没有 connection 增删。
* 没有图形化画布。

## 5. 与 WORKFLOW-EDIT 的边界

节点配置主线只解决：

```text
编辑已有节点实例的 config
```

WORKFLOW-EDIT-1/2 应解决的是更大的 workflow definition 结构编辑，例如：

```text
新增节点实例
删除节点实例
修改节点基础字段
新增/删除 connections
结构化保存前校验
revision conflict 下的编辑保护
```

因此，不能把节点 config Apply 等同于完整 Workflow 编辑器。

## 6. 是否建议进入 WORKFLOW-EDIT

建议进入，但先只做前置边界分析，不直接实现。

原因：

* 当前节点配置能力已经形成 schema → input → Apply → draft JSON 的最小闭环。
* Workflow definition 的完整结构编辑会触碰 nodes / connections / revision / validation / Save，需要单独阶段。
* 直接加节点增删按钮风险较高，应先列清状态和 patch 边界。

## 7. 下一小步建议

```text
WORKFLOW-EDIT-1.0：
工作流结构化编辑前置边界分析。
```

建议只分析并列清：

* 当前 Workflow JSON 编辑能力。
* 当前结构化节点配置能力。
* nodes / connections 的最小编辑范围。
* 是否继续使用完整 `WorkflowDefinitionDraftJson` 作为唯一保存源。
* 第一小步应先做只读结构状态，还是先做新增节点草稿模型。
* 哪些能力必须后置到 WORKFLOW-EDIT-2。
