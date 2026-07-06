# FlowWeaver WORKFLOW-EDIT-2.5：结构化编辑阶段小结与后续边界分析

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：结构化只读解析、节点新增/删除、connection 新增/删除、ViewModel 命令、View 接入、用户友好 warning/error、节点/connection 输入体验和 smoke 复核已经落地。
> 未实现：自由画布、拖拽连线、完整撤销/重做和复杂 DAG 自动重排未在本阶段实现。
> 原因：这些能力超出结构化编辑最小闭环，已作为后续体验方向保留。

> 文档状态：WORKFLOW-EDIT-2.5 阶段小结完成
> 当前阶段：结构化编辑第二阶段收口
> 不适用范围：新功能实现、人工 Desktop 点击执行、port schema 深校验、图形画布

## 1. 阶段目标

对 WORKFLOW-EDIT-2 做阶段小结，明确当前结构化编辑已经完成的自动验收边界、仍未覆盖的真实人工路径，以及后续是否应继续扩展到 port/schema/画布能力。

本阶段只做文档复核，不新增源码或 XAML 改动。

## 2. 完成矩阵

| 小步 | 内容 | 状态 | 主要证据 |
| --- | --- | --- | --- |
| 2.0 | 结构化编辑可用性缺口边界分析 | 已完成 | `FlowWeaver_WORKFLOW-EDIT-2.0...md` |
| 2.1 | 用户友好 warning / error 映射 | 已完成 | `MainWindowViewModelWorkflowTests`、本地化测试 |
| 2.2 | node type 与 node instance id 输入体验 | 已完成 | `FlowWeaver_WORKFLOW-EDIT-2.2e...md` |
| 2.3 | connection source / target / id 输入体验 | 已完成 | `FlowWeaver_WORKFLOW-EDIT-2.3e...md` |
| 2.4a | 桌面 smoke 前置清单 | 已完成 | `FlowWeaver_WORKFLOW-EDIT-2.4a...md` |
| 2.4b | 发布 Desktop workflow run event 自动 smoke | 已完成 | `DesktopPublishWorkflowRunEventSmokeTests` |
| 2.4c | 人工 Desktop smoke 清单与后置复核 | 已完成 | `FlowWeaver_WORKFLOW-EDIT-2.4c...md` |
| 2.4d | Headless GUI 自动 smoke | 已完成 | `WorkflowSummaryViewHeadlessSmokeTests` |

## 3. 当前已支持的结构化编辑路径

当前已支持：

* 继续以 `WorkflowDefinitionDraftJson` 作为保存接口唯一输入。
* 加载 workflow definition 后生成 draft structure。
* 通过结构化表单新增 node。
* node type 可从 `NodeDefinitions` 中选择。
* 选择 node definition 后自动填充 type / version / display name。
* node instance id 可自动建议，且允许用户手动覆盖。
* 通过结构化表单删除 node。
* 删除仍被 connection 引用的 node 时给出用户可读错误。
* 通过结构化表单新增 connection。
* source / target node 可从当前 draft nodes 中选择。
* connection id 可自动建议，且允许用户手动覆盖。
* source / target port 继续手动输入。
* 通过结构化表单删除 connection。
* warning / error code 映射为用户可读文案。
* 复用既有 dirty、validation invalidation、revision conflict 和 save 流程。

## 4. 自动验证边界

当前自动验证覆盖：

* 纯模型：draft structure builder、node patcher、connection patcher。
* ViewModel：新增/删除 node，新增/删除 connection，选择状态，自动建议 ID，错误文案。
* View 结构：`WorkflowSummaryView` 中结构化编辑表单、ComboBox、输入字段和命令绑定。
* Headless GUI：`WorkflowSummaryView` 可以在 Avalonia Headless runtime 中加载，节点类型下拉和 connection source / target 下拉能获得 ViewModel 绑定数据。
* 发布路径：Desktop 发布 assembly 的 API client / RuntimeEvent WebSocket client 可连接 portable EngineHost 并完成 workflow run lifecycle smoke。

最近验证记录：

```text
dotnet build Avalonia_UI\Avalonia_UI.sln --no-restore
成功，0 警告，0 错误

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "WorkflowSummaryViewHeadlessSmokeTests"
通过：1，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：265，失败：0，跳过：0
```

## 5. 当前明确不支持的能力

以下能力仍不属于 WORKFLOW-EDIT-2 当前收口范围：

* source / target port 下拉选择。
* 端口方向、类型兼容和数据契约深校验。
* 根据 source / target 自动推荐 port。
* 自动连接推荐。
* 图形化画布。
* 拖拽连线。
* 自动布局。
* 撤销 / 重做。
* 多选批量编辑。
* 外部插件节点编辑器。
* 发布产物真实窗口的人工点击验收记录。

这些能力如果要继续推进，应拆成独立阶段；尤其 port 下拉和端口深校验应先回到后端 schema / workflow validation 契约，不应在当前 View 层硬做。

## 6. 人工 Desktop smoke 状态

当前已经有两类自动 smoke：

* 发布 Desktop API/WebSocket 正式路径 smoke。
* `WorkflowSummaryView` Headless GUI 运行时加载与关键绑定 smoke。

但这仍不等同于人工 Desktop 点击 smoke。人工点击仍需要在真实 Desktop 窗口中确认：

* health check。
* workflow 列表刷新。
* definition 加载。
* node catalog 刷新。
* node type 下拉选择。
* connection source / target 下拉选择。
* Add node / Add connection。
* Validate / Save。
* 重载 definition 后肉眼确认 JSON。

因此人工 Desktop smoke 更适合作为发布前验收或用户试用前清单，不应在本阶段通过代码绕过。

## 7. 后续建议

最稳下一步不是继续扩 port 或画布，而是先做一个很小的完成审计：

```text
WORKFLOW-EDIT-2.6：
结构化编辑目标完成审计与人工 Desktop smoke 决策。
```

该小步应只回答三件事：

* 当前 active goal 中 UI-NODE-CATALOG、NODE-CONFIG-SCHEMA、UI-SCHEMA、UI-NODE-CONFIG、WORKFLOW-EDIT-1/2 是否都有当前证据。
* 人工 Desktop smoke 是否作为当前目标阻塞项，还是转为发布前手动验收项。
* 若目标主线已满足，是否进入推送前总复核或等待用户确认下一阶段。
