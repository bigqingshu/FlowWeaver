# FlowWeaver WORKFLOW-EDIT-2.4d：Headless GUI 自动 smoke

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：结构化只读解析、节点新增/删除、connection 新增/删除、ViewModel 命令、View 接入、用户友好 warning/error、节点/connection 输入体验和 smoke 复核已经落地。
> 未实现：自由画布、拖拽连线、完整撤销/重做和复杂 DAG 自动重排未在本阶段实现。
> 原因：这些能力超出结构化编辑最小闭环，已作为后续体验方向保留。

> 文档状态：WORKFLOW-EDIT-2.4d 自动 smoke 完成
> 当前阶段：结构化编辑真实路径验收
> 不适用范围：人工 Desktop 点击、真实窗口肉眼确认、port schema 深校验、图形画布

## 1. 阶段目标

在不启动真实 Desktop 窗口、不接入 EngineHost 的前提下，为 `WorkflowSummaryView` 增加一层 Avalonia Headless GUI smoke，确认当前结构化编辑 View 能在 Avalonia 运行时中加载，并且关键下拉控件能够从 `MainWindowViewModel` 状态获得真实绑定数据。

该 smoke 用于补齐“字符串结构测试”和“人工 Desktop 点击 smoke”之间的空档。

## 2. 本次实现

新增测试：

```text
Avalonia_UI.Tests/WorkflowSummaryViewHeadlessSmokeTests.cs
```

新增依赖：

```text
Avalonia_UI.Tests/Avalonia_UI.Tests.csproj
Avalonia.Headless 11.3.12
```

测试覆盖：

* 使用测试专用 `AppBuilder` 启动 Avalonia Headless runtime。
* 构造一个包含两节点、一条连接的 workflow definition draft。
* 将 `WorkflowSummaryView` 加载到 headless `Window`。
* 确认结构化编辑区域的 `ComboBox` 控件被实际物化。
* 确认新增节点类型下拉绑定到 `NodeDefinitions`。
* 确认 connection source / target 下拉绑定到草稿节点列表。

## 3. 验证命令

```text
dotnet build Avalonia_UI\Avalonia_UI.sln --no-restore
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "WorkflowSummaryViewHeadlessSmokeTests"
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
```

## 4. 验证结果

```text
dotnet build：
成功，0 警告，0 错误

Headless smoke：
通过：1，失败：0，跳过：0

Avalonia 全量测试：
通过：265，失败：0，跳过：0
```

## 5. 边界说明

本 smoke 已覆盖：

* View 能在 Avalonia Headless runtime 中加载。
* App 资源、样式和 View XAML 加载未破坏。
* 结构化编辑关键 ComboBox 控件可被运行时物化。
* 节点定义下拉和连接 source / target 下拉能够获得 ViewModel 绑定数据。

本 smoke 仍不覆盖：

* 人工打开真实 Desktop 窗口。
* 鼠标点击、键盘输入和肉眼确认。
* 通过真实 GUI 调用 Validate / Save。
* 与常开 EngineHost 的人工联调。
* 发布产物真实窗口 smoke。

## 6. 当前结论

WORKFLOW-EDIT-2.4d 已完成一个可自动回归的 Headless GUI smoke。它不能替代人工 Desktop 点击 smoke，但可以作为结构化编辑 View 层的最小自动 GUI 验收边界，后续继续调整 `WorkflowSummaryView` 时应保留该测试。

建议下一步：

```text
WORKFLOW-EDIT-2.5：
结构化编辑阶段小结与后续边界分析。
```
