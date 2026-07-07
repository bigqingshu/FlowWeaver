# FlowWeaver UI-MAINWINDOW-SPLIT-0：MainWindowViewModel 拆分阶段计划

> 文档状态：拆分前置计划
> 当前目标：在不改变 XAML 绑定面和用户行为的前提下，分阶段降低 `MainWindowViewModel.cs` 体量
> 执行规则：每完成一个阶段单独提交一次；提交信息使用中文；优先保持行为等价

## 1. 背景

当前 `MainWindowViewModel.cs` 已经承载多个领域：

```text
应用壳导航
连接配置与健康检查
Workflow 列表、详情、草稿编辑、结构化节点/连接编辑
节点定义目录和节点配置表单
Runtime options 编辑
运行列表、节点运行状态、取消
Runtime event stream 和日志查询
数据预览与数据预览工作台
共享发布列表
通知与最近事件
语言、主题和本地化刷新
```

该文件已经成为后续 UI 缓存优化、节点配置优化和数据预览优化的主要维护阻力。

本计划先做“低风险拆细”，再做“领域状态下沉”。第一轮不直接改成多个页面 ViewModel，避免一次性牵动大量 XAML `x:DataType="vm:MainWindowViewModel"` 绑定和既有测试。

## 2. 拆分原则

### 2.1 保留公开绑定面

第一轮拆分必须保持：

```text
MainWindowViewModel 类型名不变
现有 public 属性名不变
现有 RelayCommand 生成的 Command 名不变
现有 XAML DataContext 不变
现有测试构造入口不变
```

因此第一轮主要使用 C# `partial class` 进行物理拆分。

### 2.2 不做混合型大重构

每个提交只做一种事情：

```text
只移动代码，不改逻辑
或只抽纯模型，不改 UI 绑定
或只替换内部调用，不改外部契约
```

避免在同一个提交里同时移动代码、改命名、改行为和改测试。

### 2.3 先拆热点，再拆边缘

优先处理后续 UI-CACHE 会直接触碰的区域：

```text
Workflow draft / selected node config / runtime options
Node definitions catalog
Data preview
```

通知、Shell、Localization 等虽然也能拆，但更适合作为低风险热身阶段。

## 3. 目标文件布局

建议第一轮形成以下文件：

```text
Avalonia_UI/ViewModels/MainWindowViewModel.cs
Avalonia_UI/ViewModels/MainWindowViewModel.Notifications.cs
Avalonia_UI/ViewModels/MainWindowViewModel.Shell.cs
Avalonia_UI/ViewModels/MainWindowViewModel.Localization.cs
Avalonia_UI/ViewModels/MainWindowViewModel.Connection.cs
Avalonia_UI/ViewModels/MainWindowViewModel.Workflow.cs
Avalonia_UI/ViewModels/MainWindowViewModel.WorkflowDraft.cs
Avalonia_UI/ViewModels/MainWindowViewModel.RuntimeOptions.cs
Avalonia_UI/ViewModels/MainWindowViewModel.Runs.cs
Avalonia_UI/ViewModels/MainWindowViewModel.Logs.cs
Avalonia_UI/ViewModels/MainWindowViewModel.DataPreview.cs
Avalonia_UI/ViewModels/MainWindowViewModel.SharedPublications.cs
```

`MainWindowViewModel.cs` 最终保留：

```text
共享 using
类声明
跨领域常量与依赖字段
构造器
核心集合属性
少量跨领域协调方法
```

后续如果需要真正子 ViewModel，再另开 `UI-MAINWINDOW-SPLIT-1` 计划。

## 4. 阶段计划

### UI-MAINWINDOW-SPLIT-0a：计划文档提交

目标：

* 新增本拆分计划。
* 不改代码。

验收：

```text
git diff --cached --stat
```

提交：

```text
docs：新增 MainWindowViewModel 拆分阶段计划
```

### UI-MAINWINDOW-SPLIT-0b：通知与最近事件 partial 拆分

目标：

* 新增 `MainWindowViewModel.Notifications.cs`。
* 移动通知弹层、倒计时、最近事件相关字段、命令和辅助方法。
* 不改任何 public 属性名和命令名。

范围示例：

```text
Notification* ObservableProperty
IsRecentEventsExpanded
ShowNotification(...)
CloseNotificationCommand
ViewAllRecentEventsCommand
ShowWorkflowNotification(...)
ShowDataPreviewNotification(...)
AddRecentEvent(...)
NotifyRecentEventsChanged(...)
```

验收：

```powershell
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "MainWindowViewModelNotificationTests"
dotnet build Avalonia_UI\Avalonia_UI.sln --no-restore
```

提交：

```text
重构：拆分 MainWindowViewModel 通知状态
```

### UI-MAINWINDOW-SPLIT-0c：Shell 与本地化 partial 拆分

目标：

* 新增 `MainWindowViewModel.Shell.cs`。
* 新增 `MainWindowViewModel.Localization.cs`。
* 移动 Shell 导航、语言/主题、本地化文本刷新相关逻辑。

范围示例：

```text
CurrentLanguageCode
CurrentThemeVariant
SelectedShellPageKey
SelectedShellPageIndex
Languages / Themes / ShellNavigationItems
ChangeLanguageCommand
ChangeThemeCommand
RefreshShellNavigationItems(...)
NotifyLocalizedTextChanged(...)
T(...)
F(...)
```

验收：

```powershell
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "MainWindowViewModelLocalizationTests|BuiltinShellPagesTests|MainWindowShellStructureTests"
dotnet build Avalonia_UI\Avalonia_UI.sln --no-restore
```

提交：

```text
重构：拆分 MainWindowViewModel 壳层与本地化状态
```

### UI-MAINWINDOW-SPLIT-0d：连接与事件流 partial 拆分

目标：

* 新增 `MainWindowViewModel.Connection.cs`。
* 移动 BaseUrl/token、健康检查、连接配置保存、runtime event stream 连接循环相关逻辑。

范围示例：

```text
BaseUrl / Token / ConnectionStatus
StatusMessage / ErrorMessage
RuntimeEventStream*
CheckConnectionCommand
StartRuntimeEventStreamCommand
StopRuntimeEventStreamCommand
BuildSettings()
SaveConnectionSettingsAsync(...)
DescribeError(...)
RunRuntimeEventStreamLoopAsync(...)
AcceptRuntimeEventAsync(...)
RecoverRuntimeStateAsync(...)
```

验收：

```powershell
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "MainWindowViewModelConnectionSettingsTests|MainWindowViewModelRuntimeEventTests|EngineHostConnectionDiagnosticsTests"
dotnet build Avalonia_UI\Avalonia_UI.sln --no-restore
```

提交：

```text
重构：拆分 MainWindowViewModel 连接与事件流状态
```

### UI-MAINWINDOW-SPLIT-0e：Workflow 列表与运行控制 partial 拆分

目标：

* 新增 `MainWindowViewModel.Workflow.cs`。
* 新增 `MainWindowViewModel.Runs.cs`。
* 移动 workflow 列表、创建、删除、启动、运行列表、节点运行状态、取消相关逻辑。

范围示例：

```text
Workflows / SelectedWorkflow
Runs / SelectedRun / NodeRuns
RefreshWorkflowsCommand
CreateTemplateWorkflowCommand
DeleteSelectedWorkflowCommand
StartSelectedWorkflowCommand
PreviewSelectedWorkflowNodeCommand
RefreshRunsCommand
CancelSelectedRunCommand
RefreshNodeRunsCommand
LoadRunsAsync(...)
LoadNodeRunsForSelectedRunAsync(...)
```

验收：

```powershell
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "MainWindowViewModelWorkflowTests|MainWindowViewModelRuntimeEventTests"
dotnet build Avalonia_UI\Avalonia_UI.sln --no-restore
```

提交：

```text
重构：拆分 MainWindowViewModel 工作流与运行状态
```

### UI-MAINWINDOW-SPLIT-0f：Workflow draft 与 Runtime options partial 拆分

目标：

* 新增 `MainWindowViewModel.WorkflowDraft.cs`。
* 新增 `MainWindowViewModel.RuntimeOptions.cs`。
* 移动 workflow draft JSON、节点/连接结构化编辑、节点配置草稿、runtime options 编辑相关逻辑。

范围示例：

```text
WorkflowDefinitionDetail
WorkflowDefinitionDraftJson
WorkflowDefinitionDraftStructure
WorkflowDefinitionDraftNodes
SelectedWorkflowDefinitionNode
NodeDefinitions
SelectedNodeConfigDraft / EditableDraft
Add/Delete/Copy/Move node commands
Add/Delete connection commands
Validate/Save/Restore draft commands
RuntimeOptions* properties and commands
```

验收：

```powershell
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "MainWindowViewModelWorkflowTests|WorkflowDefinitionDraftNodePatcherTests|WorkflowDefinitionDraftConnectionPatcherTests|WorkflowDefinitionDraftRuntimeOptionsPatcherTests"
dotnet build Avalonia_UI\Avalonia_UI.sln --no-restore
```

提交：

```text
重构：拆分 MainWindowViewModel 草稿编辑状态
```

### UI-MAINWINDOW-SPLIT-0g：Logs、DataPreview、SharedPublications partial 拆分

目标：

* 新增 `MainWindowViewModel.Logs.cs`。
* 新增 `MainWindowViewModel.DataPreview.cs`。
* 新增 `MainWindowViewModel.SharedPublications.cs`。
* 移动日志筛选、数据预览、共享发布相关逻辑。

范围示例：

```text
RuntimeEventLogEntries and filters
RefreshRuntimeEventLogCommand
TableRefs / DataPreview* / DataPreviewWorkbench*
RefreshTableRefsCommand
RefreshSelectedWorkflowNodeDataPreviewCommand
LoadSelectedDataPreviewTableCommand
SharedPublications / SharedPublicationVersions
RefreshSharedPublicationsCommand
RefreshSharedPublicationVersionsCommand
```

验收：

```powershell
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "MainWindowViewModelDataTests|MainWindowViewModelLogTests"
dotnet build Avalonia_UI\Avalonia_UI.sln --no-restore
```

提交：

```text
重构：拆分 MainWindowViewModel 数据与日志状态
```

### UI-MAINWINDOW-SPLIT-0h：收口复核

目标：

* 检查 `MainWindowViewModel.cs` 是否只保留共享骨架。
* 检查 partial 文件职责边界。
* 不做行为改动。

验收：

```powershell
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
```

提交：

```text
复核：收口 MainWindowViewModel 拆分阶段
```

## 5. 暂不处理

第一轮不处理：

```text
不改 XAML DataContext
不拆真正页面级 ViewModel
不新增事件总线
不改变命令命名
不调整后端 API
不做 UI-CACHE parsed state 缓存实现
```

这些能力放到后续阶段：

```text
UI-MAINWINDOW-SPLIT-1：页面级 ViewModel 迁移评估
UI-CACHE-2：Workflow draft parsed state 缓存
UI-CACHE-3：Node definitions 目录字典与 schema 复用
```

## 6. 风险点

### 6.1 Source generator 边界

`ObservableProperty` 和 `RelayCommand` 位于 partial 文件中时仍应生成到同一个 `MainWindowViewModel` 类型。

验收必须覆盖 build，不能只跑测试。

### 6.2 private 成员依赖

partial 文件之间可以互相访问 private 成员，但移动代码时容易漏 using 或漏同组 helper。

每阶段移动后应优先处理编译错误，不做顺手重构。

### 6.3 测试文件同步膨胀

`MainWindowViewModelWorkflowTests.cs` 也很大，但本轮只在必要时移动测试辅助，不主动重排测试。

测试拆分建议另开：

```text
UI-MAINWINDOW-TEST-SPLIT-0
```

## 7. 执行规则

每个阶段执行顺序：

```text
1. 确认 git status，避免混入无关改动
2. 只移动或修改本阶段文件
3. 运行本阶段验收命令
4. 单独 stage 本阶段文件
5. 使用中文提交信息提交
6. 进入下一阶段
```

如果某阶段测试耗时过长，至少运行：

```powershell
dotnet build Avalonia_UI\Avalonia_UI.sln --no-restore
```

并在提交说明或最终汇报中标记未运行的完整测试。

## 8. 完成定义

本计划完成时应满足：

```text
MainWindowViewModel 对外类型和绑定保持兼容
核心领域逻辑已按 partial 文件分组
MainWindowViewModel.cs 不再承载所有领域实现
所有阶段均有独立提交
后续 UI-CACHE 实施可以集中修改 WorkflowDraft / DataPreview 文件
```
