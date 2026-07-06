# FlowWeaver WORKFLOW-EDIT-2.1：用户友好 warning / error 映射

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：结构化只读解析、节点新增/删除、connection 新增/删除、ViewModel 命令、View 接入、用户友好 warning/error、节点/connection 输入体验和 smoke 复核已经落地。
> 未实现：自由画布、拖拽连线、完整撤销/重做和复杂 DAG 自动重排未在本阶段实现。
> 原因：这些能力超出结构化编辑最小闭环，已作为后续体验方向保留。

> 文档状态：WORKFLOW-EDIT-2.1 已完成
> 当前阶段：结构化编辑可用性收口
> 不适用范围：patcher 行为修改、XAML 调整、后端 API 改动、port schema 深校验

## 1. 阶段目标

将结构化编辑命令失败时展示的内部 warning code，转换为用户可读文案：

```text
NODE_ALREADY_EXISTS
-> A node with this instance ID already exists.
```

本阶段只改变 UI 展示层，不改变 patcher 返回码和测试边界。

## 2. 修改范围

已修改：

* `Avalonia_UI/ViewModels/MainWindowViewModel.cs`
* `Avalonia_UI/Localization/en-US.json`
* `Avalonia_UI/Localization/zh-Hans.json`
* `Avalonia_UI.Tests/MainWindowViewModelWorkflowTests.cs`
* `Avalonia_UI.Tests/JsonLocalizationServiceTests.cs`

未修改：

* `WorkflowDefinitionDraftNodePatcher`
* `WorkflowDefinitionDraftConnectionPatcher`
* `WorkflowSummaryView.axaml`
* 后端 API

## 3. 实现边界

新增 `LocalizeWorkflowDefinitionDraftWarning`，只在以下四个命令失败分支调用：

* `AddWorkflowDefinitionDraftNode`
* `DeleteWorkflowDefinitionDraftNode`
* `AddWorkflowDefinitionDraftConnection`
* `DeleteWorkflowDefinitionDraftConnection`

未知 warning code 仍回退原始 code，方便后续发现遗漏。

## 4. 覆盖的 warning code

当前覆盖：

```text
WORKFLOW_DRAFT_JSON_INVALID
WORKFLOW_DRAFT_ROOT_NOT_OBJECT
WORKFLOW_DRAFT_NODES_MISSING
WORKFLOW_DRAFT_CONNECTIONS_MISSING
NODE_INSTANCE_ID_REQUIRED
NODE_TYPE_REQUIRED
NODE_VERSION_REQUIRED
CONFIG_UNSUPPORTED
NODE_ALREADY_EXISTS
NODE_NOT_FOUND
NODE_HAS_CONNECTIONS
CONNECTION_ID_REQUIRED
CONNECTION_ALREADY_EXISTS
CONNECTION_NOT_FOUND
SOURCE_NODE_ID_REQUIRED
SOURCE_NODE_NOT_FOUND
SOURCE_PORT_REQUIRED
TARGET_NODE_ID_REQUIRED
TARGET_NODE_NOT_FOUND
TARGET_PORT_REQUIRED
```

## 5. 测试覆盖

已更新 / 补充：

* 重复 node id 展示用户可读文案。
* 删除仍被 connection 引用的 node 展示“先删除连接”类文案。
* 缺失 target node 展示用户可读文案。
* 重复 connection id 展示用户可读文案。
* JSON 本地化资源覆盖新增中英文 warning key。

当前已运行：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "MainWindowViewModelWorkflowTests|JsonLocalizationServiceTests"
通过：61，失败：0，跳过：0

dotnet build Avalonia_UI\Avalonia_UI.sln --no-restore
成功，警告：0，错误：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：258，失败：0，跳过：0
```

## 6. 保留项

本阶段仍未处理：

* node type 下拉选择。
* node instance id 自动建议。
* connection id 自动建议。
* source / target node 下拉选择。
* port 下拉与端口 schema 深校验。
* 桌面真实 smoke。

## 7. 下一小步建议

建议进入：

```text
WORKFLOW-EDIT-2.2：
node type 与 node instance id 输入体验收口。
```

建议先做前置分析，明确是否复用已有 node catalog 数据，以及在 catalog 加载失败时如何降级回手动输入。
