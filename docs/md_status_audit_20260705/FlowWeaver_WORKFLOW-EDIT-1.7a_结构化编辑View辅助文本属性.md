# FlowWeaver WORKFLOW-EDIT-1.7a：结构化编辑 View 辅助文本属性

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：结构化只读解析、节点新增/删除、connection 新增/删除、ViewModel 命令、View 接入、用户友好 warning/error、节点/connection 输入体验和 smoke 复核已经落地。
> 未实现：自由画布、拖拽连线、完整撤销/重做和复杂 DAG 自动重排未在本阶段实现。
> 原因：这些能力超出结构化编辑最小闭环，已作为后续体验方向保留。

> 文档状态：WORKFLOW-EDIT-1.7a 已完成
> 当前阶段：Gemini View 接入前的本地化文本前置收口
> 不适用范围：XAML 改动、ViewModel 命令改动、模型改动

## 1. 本小步目标

本小步只补结构化编辑表单所需的 View 文本属性和本地化资源。

新增文本属性包括：

```text
StructuredEditSectionText
AddNodeText
DeleteNodeText
NodeInstanceIdText
NodeTypeText
NodeVersionText
DisplayNameText
ConfigJsonText
AddConnectionText
DeleteConnectionText
ConnectionIdText
SourceNodeText
SourcePortText
TargetNodeText
TargetPortText
```

## 2. 当前边界

本小步没有修改：

* `WorkflowSummaryView.axaml`
* 结构化编辑命令逻辑
* patcher
* 后端接口

这些文本属性只是为下一步 Gemini 纯 View 修改提供绑定基础，避免在 XAML 中写死英文或中文。

## 3. 验证结果

已执行：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "MainWindowViewModelLocalizationTests|JsonLocalizationServiceTests"
通过：28，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：256，失败：0，跳过：0
```

## 4. 下一小步建议

建议进入：

```text
WORKFLOW-EDIT-1.7b：
结构化编辑 Gemini View 修改任务说明。
```

建议只更新协作文档：

* 明确 Gemini 只改 `WorkflowSummaryView.axaml`。
* 使用 1.7a 新增文本属性，不写死文本。
* 绑定现有结构化编辑输入状态和命令。
* 不修改 ViewModel、模型、Localization、测试或后端。
