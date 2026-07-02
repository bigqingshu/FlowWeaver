# FlowWeaver Avalonia 组件管理与可扩展界面实施方案

> 文档状态：WORKFLOW-EDIT-2.5 结构化编辑阶段小结已完成
> 当前执行点：下一步可进入 WORKFLOW-EDIT-2.6 结构化编辑目标完成审计与人工 Desktop smoke 决策
> 适用范围：`Avalonia_UI/Views/MainWindow.axaml`、现有五个页面、Shell 区域契约、后续组件注册方向
> 不适用范围：外部 DLL 加载、模块安装/更新、代码签名、自动更新、后台服务、系统托盘、self-contained Desktop

## UI-COMPONENT-0：MainWindow Shell 边界分析与组件化最小计划

### 0.1 当前事实

当前 Avalonia UI 已经完成页面和组件拆分：

```text
Avalonia_UI/Views/Pages/
Avalonia_UI/Views/Components/
Avalonia_UI/ViewModels/
Avalonia_UI/Localization/
Avalonia_UI/Styles/
```

但 `MainWindow.axaml` 仍直接承担以下职责：

```text
Window 级样式
五个 TabItem 导航
WorkflowPage / RunMonitorPage / DataPage / LogsAuditPage / SettingsPage 页面引用
窗口主布局和页面承载
```

`MainWindowViewModel.cs` 仍是集中式 ViewModel，承载连接、工作流、运行、数据、日志、设置、语言、主题和 ActionState 等大量状态。

因此，UI-COMPONENT-0 的结论是：

```text
先冻结 MainWindow Shell 职责
再考虑注册中心
最后才考虑外部模块
```

### 0.2 本小步目标

本小步只确认下一阶段 UI 组件化的最小入口：

1. 明确 `MainWindow.axaml` 应逐步收敛为 AppShell。
2. 明确近期只允许处理内置页面和 Shell 区域。
3. 明确现有五个页面行为、Command、ActionState、语言和主题不能回归。
4. 明确外部 DLL、模块安装、签名、热更新全部后置。

### 0.3 近期可执行范围

近期只建议执行：

```text
COMPONENT-0
冻结 Shell 区域和 MainWindow 职责

COMPONENT-1
整理 MainWindow 当前职责清单与 AppShell 目标结构

COMPONENT-2
建立内置页面清单最小实现方案，必要时再迁移硬编码 TabItem
```

近期不引入：

```text
IServiceProvider 强依赖
外部 DLL
AssemblyLoadContext
ui-modules 目录
模块安装器
模块签名
运行时卸载
热更新
```

### 0.4 COMPONENT-0 验收标准

COMPONENT-0 完成时应满足：

* 只产生文档或极薄 Shell 契约，不迁移现有页面。
* `MainWindow.axaml` 的当前硬编码页面现状被记录清楚。
* 后续迁移顺序明确，不要求一次性完成组件平台。
* 不改变 `MainWindowViewModel` 的业务状态和 Command。
* 不改变现有五个页面的用户行为。
* 不改变 P 阶段正式发布前置 strict 路径。

### 0.5 与阶段 P / Distribution 的关系

阶段 P 已完成正式发布前置收口，当前 UI-COMPONENT 方向不应反向扩大 P 阶段。

本文后半部分涉及：

```text
外部模块目录
模块安装和更新
签名或白名单
模块发布归档
```

这些内容属于远期 UI 插件化或 Distribution 方向参考，不作为 UI-COMPONENT-0 到 COMPONENT-2 的实施依据。

### 0.6 下一小步建议

从 COMPONENT-0 进入下一小步时，建议仍保持文档优先：

```text
UI-COMPONENT-1：MainWindow 当前职责清单与 AppShell 目标结构
```

建议只列清：

* 当前 `MainWindow.axaml` 中哪些内容属于 Shell。
* 哪些内容属于页面导航。
* 哪些 Window 级样式应后续迁移到 ResourceDictionary。
* 哪些现有行为必须保持不变。
* 第一版迁移不碰哪些内容。

---

## UI-COMPONENT-1：MainWindow 当前职责清单与 AppShell 目标结构

### 1.1 当前 `MainWindow.axaml` 职责清单

当前 `MainWindow.axaml` 不是单纯页面容器，它同时承担以下职责：

| 职责 | 当前位置 | 处理建议 |
| --- | --- | --- |
| Window 元信息 | `Window` 根节点的 `Title`、`Icon`、尺寸、最小尺寸、背景、`x:DataType` | 暂时保留在 `MainWindow.axaml` |
| 设计期 DataContext | `Design.DataContext` | 暂时保留，避免影响设计器 |
| Window 级样式 | `Window.Styles` 内的 `Button`、`ListBoxItem`、`TabControl`、`TabItem`、`Border.Card` | 后续迁移到 ResourceDictionary，COMPONENT-1 不迁移 |
| Shell Header | 顶部 `Grid`、标题、副标题、`ConnectionStatusView` | 属于 AppShell 固定区域 |
| 导航区域 | 左侧 `TabControl` 和五个 `TabItem` | 当前是硬编码导航，后续迁移为内置页面清单 |
| 页面承载 | `WorkflowPage`、`RunMonitorPage`、`DataPage`、`LogsAuditPage`、`SettingsPage` | 当前由 TabItem 直接承载，后续由 Shell 主区域承载 |
| 页面命名空间引用 | `xmlns:pages`、`xmlns:components` | 第一版保留，等页面清单稳定后再收敛 |

当前 `MainWindow.axaml.cs` 只负责 `InitializeComponent()`，不包含业务逻辑。这个状态应保持，不应在组件化过程中把页面切换、后端调用或 ActionState 逻辑放进 code-behind。

### 1.2 现有五个内置页面清单

第一版组件化只处理现有内置页面，不引入外部模块：

| 页面键 | 当前 Header 绑定 | 当前页面 View | 当前性质 |
| --- | --- | --- | --- |
| `workflows` | `WorkflowsSectionText` | `WorkflowPage` | 工作流定义、草稿和运行入口 |
| `runs` | `RunsSectionText` | `RunMonitorPage` | WorkflowRun 和 NodeRun 运行监控 |
| `data` | `DataTabText` | `DataPage` | TableRef 和 SharedPublication 只读数据视图 |
| `logs` | `LogsTabText` | `LogsAuditPage` | RuntimeEvent 和 AuditEvent 查询 |
| `settings` | `SettingsMenuText` | `SettingsPage` | 连接、语言、主题和流配置 |

这些页面在 COMPONENT-1 中只作为事实清单记录，不改变页面布局、不改变绑定、不改变命令启用条件。

### 1.3 AppShell 第一版目标结构

第一版目标不是建立完整插件平台，而是把 `MainWindow` 的职责收敛为稳定 Shell：

```text
MainWindow
└─ AppShell
   ├─ WindowFrame
   ├─ HeaderRegion
   ├─ NavigationRegion
   └─ MainRegion
```

各区域的边界如下：

| 区域 | 第一版职责 | 不承担 |
| --- | --- | --- |
| `WindowFrame` | 窗口标题、图标、尺寸、背景、主题资源引用 | 不承载业务状态 |
| `HeaderRegion` | 应用标题、副标题、连接状态组件 | 不发起后端请求 |
| `NavigationRegion` | 展示内置页面导航项、维护当前选中页 | 不决定工作流业务动作 |
| `MainRegion` | 承载当前选中页面 | 不直接知道节点、表、审计等领域细节 |

第一版可以继续使用 `TabControl`，也可以在后续最小实现时把 TabItem 来源改为内置页面清单；但不能在这一阶段引入外部 DLL 扫描或插件安装。

### 1.4 后续可抽出的最小导航描述

后续 COMPONENT-2 如需进入代码实现，建议只设计内置页面描述，不暴露外部插件协议：

```text
ShellPageDescriptor
- Key
- HeaderTextBinding 或 TextKey
- SortOrder
- ViewType 或 ViewFactory
- IsVisible
- IsEnabled
```

其中 `IsVisible` 和 `IsEnabled` 第一版可固定为 `true`，仅为后续连接状态、权限或实验页面预留边界；不要在 COMPONENT-2 中顺手实现权限系统或远程模块能力。

### 1.5 第一版必须保持不变的行为

组件化迁移时必须保持以下行为不回归：

* 顶部标题和副标题仍走本地化绑定。
* 五个导航 Header 仍随语言切换刷新。
* 连接状态仍由 `ConnectionStatusView` 展示。
* 五个页面的 ViewModel 绑定上下文不变化。
* Run、Workflow、Data、Logs、Settings 的 ActionState 不变化。
* 主题切换和现有动态资源不变化。
* 发布 strict 路径不新增发布物或外部模块目录。

### 1.6 第一版明确不做

UI-COMPONENT-1 和紧随其后的 COMPONENT-2 不做以下内容：

```text
拆分 MainWindowViewModel 的业务状态
把页面改为外部 DLL
引入 AssemblyLoadContext
引入 IServiceProvider 作为 Shell 强依赖
引入模块安装、卸载、签名、热更新
改变五个页面内部组件结构
改变后端 API 或 WebSocket 协议
改变发布归档结构
```

`MainWindowViewModel` 当前仍是集中式 ViewModel。后续可以分析 Shell 专用状态投影，但不应在页面导航清单落地前拆分连接、工作流、运行、数据、日志和设置等业务状态。

### 1.7 COMPONENT-1 验收标准

COMPONENT-1 完成时应满足：

* `MainWindow.axaml` 当前职责已经按 Shell、导航、页面承载、样式分组记录。
* 现有五个内置页面及 Header 绑定已经形成清单。
* AppShell 第一版目标结构明确。
* 后续 COMPONENT-2 的最小代码入口是内置页面清单，而不是外部插件平台。
* 没有修改 Avalonia 代码。
* 没有扩大到 Distribution、签名、安装器或热更新。

### 1.8 下一小步建议

下一小步建议仍保持小范围：

```text
UI-COMPONENT-2：内置页面清单最小实现方案
```

建议先分析两种实现路线，再决定是否写代码：

1. 保守路线：只新增 Shell 页面描述模型和静态清单，`MainWindow.axaml` 暂不迁移。
2. 最小迁移路线：让 `TabControl` 使用内置页面清单承载现有五个页面。

如果进入代码，优先选择风险更低的一步，先保证 `dotnet build`、现有绑定和语言/主题切换不回归。

---

## UI-COMPONENT-2：内置页面清单最小实现方案

### 2.1 当前约束

根据当前代码复核，COMPONENT-2 需要遵守以下约束：

* `MainWindow.axaml` 当前直接声明五个 `TabItem`，每个 `TabItem` 内直接承载一个页面 View。
* `MainWindowViewModel.cs` 当前集中提供五个导航 Header 的本地化文本。
* 项目启用了 `AvaloniaUseCompiledBindingsByDefault`，XAML 迁移必须注意绑定类型可解析。
* `ViewLocator` 目前按 `ViewModel` 到 `View` 的命名约定创建页面，不适合直接用来承载现有页面 View。
* 当前五个页面没有独立页面级 ViewModel，仍共享 `MainWindowViewModel` 作为 DataContext。
* `MainWindow.axaml.cs` 只有 `InitializeComponent()`，组件化不应把业务逻辑放入 code-behind。

因此，COMPONENT-2 的目标不是拆分业务 ViewModel，而是先让“内置页面清单”成为 Shell 导航的唯一事实来源。

### 2.2 路线对比

| 路线 | 做法 | 优点 | 风险 | 结论 |
| --- | --- | --- | --- | --- |
| A. 保守路线 | 新增内置页面描述模型和静态清单，暂不改 `MainWindow.axaml` 的五个 `TabItem` | 风险最低，可先用测试锁定页面清单顺序和 Header 绑定 | `MainWindow.axaml` 仍硬编码页面 | 推荐先做 |
| B. 最小迁移路线 | 让 `TabControl` 绑定内置页面清单，并用模板承载现有五个页面 | 能减少 `MainWindow.axaml` 硬编码 | XAML 模板、页面实例、DataContext 和 compiled binding 风险更高 | 等 A 稳定后再做 |
| C. 插件化路线 | 引入注册中心、外部模块或 ViewFactory 扩展 | 与远期目标一致 | 超出 COMPONENT-2，容易牵动 Distribution 和签名策略 | 当前禁止 |

本阶段建议采用路线 A，先形成代码可验证的内置页面清单；是否迁移 `TabControl` 放到下一小步决定。

### 2.3 推荐的最小代码边界

若进入代码实现，建议只新增 Shell 层模型和清单，不改变现有页面布局：

```text
Avalonia_UI/Models/ShellPageKey.cs
Avalonia_UI/Models/ShellPageDescriptor.cs
Avalonia_UI/Models/BuiltinShellPages.cs
```

职责建议如下：

| 文件 | 职责 |
| --- | --- |
| `ShellPageKey.cs` | 定义五个稳定页面键：`Workflows`、`Runs`、`Data`、`Logs`、`Settings` |
| `ShellPageDescriptor.cs` | 定义页面键、排序、Header 文本属性名或本地化 key、页面 View 类型名 |
| `BuiltinShellPages.cs` | 返回固定顺序的五个内置页面描述 |

第一版不建议把页面 View 实例放进 descriptor，避免 View 生命周期和 DataContext 提前复杂化。

### 2.4 页面描述字段

建议第一版 descriptor 只包含稳定、可测试、不会引入 View 生命周期问题的字段：

```text
ShellPageDescriptor
- Key
- SortOrder
- HeaderPropertyName
- ViewTypeName
- IsVisible
- IsEnabled
```

字段含义：

| 字段 | 说明 | 第一版取值 |
| --- | --- | --- |
| `Key` | 稳定页面键 | 固定五个内置页面 |
| `SortOrder` | 导航顺序 | 10、20、30、40、50 |
| `HeaderPropertyName` | 当前 Header 绑定属性名 | `WorkflowsSectionText` 等 |
| `ViewTypeName` | 当前页面 View 类型名 | `WorkflowPage` 等 |
| `IsVisible` | 是否显示 | 固定 `true` |
| `IsEnabled` | 是否可用 | 固定 `true` |

这里使用 `HeaderPropertyName` 而不是直接保存 Header 文本，是为了避免语言切换时清单内缓存旧文本。当前 Header 文本仍由 `MainWindowViewModel` 的本地化属性提供。

### 2.5 五个内置页面的目标清单

第一版清单应与现有 `MainWindow.axaml` 完全一致：

| Key | SortOrder | HeaderPropertyName | ViewTypeName |
| --- | ---: | --- | --- |
| `Workflows` | 10 | `WorkflowsSectionText` | `Avalonia_UI.Views.Pages.WorkflowPage` |
| `Runs` | 20 | `RunsSectionText` | `Avalonia_UI.Views.Pages.RunMonitorPage` |
| `Data` | 30 | `DataTabText` | `Avalonia_UI.Views.Pages.DataPage` |
| `Logs` | 40 | `LogsTabText` | `Avalonia_UI.Views.Pages.LogsAuditPage` |
| `Settings` | 50 | `SettingsMenuText` | `Avalonia_UI.Views.Pages.SettingsPage` |

验收时应确认顺序、Header 来源和页面类型与当前 XAML 完全一致。

### 2.6 暂不迁移 XAML 的原因

COMPONENT-2 的第一小步建议暂不迁移 `MainWindow.axaml`，原因是：

* 当前五个页面共享 `MainWindowViewModel`，直接使用动态页面实例可能引入 DataContext 继承差异。
* `TabControl` 的 `ItemsSource`、`ItemTemplate`、`ContentTemplate` 迁移会同时触碰导航和页面承载两个边界。
* 编译绑定开启后，模板内绑定字段需要额外确认类型。
* 语言切换当前靠 ViewModel 属性通知刷新，若 Header 改为字符串缓存，容易出现旧语言文本。

因此最稳顺序是：

```text
先新增清单
再用测试确认清单与现有 XAML 等价
最后再决定是否迁移 TabControl
```

### 2.7 如果下一小步进入 XAML 迁移

当清单模型稳定后，才考虑下一步迁移：

```text
MainWindow.axaml
- TabControl 继续作为左侧导航控件
- Header 来源改为 ViewModel 暴露的 ShellNavigationItems 投影
- Header 仍从 MainWindowViewModel 的本地化属性解析
- Content 仍承载原五个页面 View
```

迁移时必须一次只处理 Header 读取清单这一件事，不拆页面内部组件，不拆 `MainWindowViewModel`，不同时迁移 `TabControl.ItemsSource`。

### 2.8 测试建议

代码实现时至少补充以下测试：

* `BuiltinShellPages` 返回五个页面。
* 页面顺序是 Workflows、Runs、Data、Logs、Settings。
* 每个页面的 `HeaderPropertyName` 与现有 `MainWindowViewModel` 属性存在。
* 每个 `ViewTypeName` 可通过反射解析到现有页面类型。
* 所有页面第一版 `IsVisible` 和 `IsEnabled` 均为 `true`。

如果后续迁移 XAML，还需要补充或手动验证：

* `dotnet build` 通过。
* 启动后五个导航项可见且顺序不变。
* 中英文切换后五个导航 Header 刷新。
* 明暗主题切换不影响导航选中态。
* 连接状态组件仍显示在 Header 区域。

### 2.9 COMPONENT-2 明确不做

本阶段不做：

```text
外部 DLL 页面加载
AssemblyLoadContext
UiComponentRegistry 完整注册中心
模块安装、更新、回滚
页面运行时卸载
页面权限控制
页面懒加载策略
拆分 MainWindowViewModel
改后端 API
改发布归档结构
```

这些内容等内置页面清单和 AppShell 基础稳定后，再进入中期或远期阶段。

### 2.10 COMPONENT-2 验收标准

COMPONENT-2 完成时应满足：

* 明确采用保守路线，先做内置页面清单，不直接进入外部插件平台。
* 页面描述字段足够表达当前五个页面，但不承载页面实例。
* 五个内置页面清单与当前 `MainWindow.axaml` 一致。
* 明确 `HeaderPropertyName` 继续指向本地化属性，避免语言切换回归。
* 明确代码实现文件边界和测试清单。
* 没有修改 Avalonia 代码。

### 2.11 下一小步建议

UI-COMPONENT-2a 已按保守路线完成：

```text
UI-COMPONENT-2a：新增 ShellPageDescriptor / BuiltinShellPages，只写模型和测试，不迁移 MainWindow.axaml
```

已落地文件：

```text
Avalonia_UI/Models/ShellPageKey.cs
Avalonia_UI/Models/ShellPageDescriptor.cs
Avalonia_UI/Models/BuiltinShellPages.cs
Avalonia_UI.Tests/BuiltinShellPagesTests.cs
```

下一小步建议先做迁移前评估，再决定是否进入：

```text
UI-COMPONENT-2b：让 MainWindow 导航读取内置页面清单
```

2b 开始前需要再次确认：

* 是否继续使用 `TabControl` 作为左侧导航控件。
* Header 是否仍通过 `MainWindowViewModel` 本地化属性动态解析。
* 页面 View 是否仍继承 `MainWindowViewModel` DataContext。
* 是否需要先增加一个 Shell 专用导航项 ViewModel，避免在 XAML 模板内做复杂反射。

### 2.12 UI-COMPONENT-2b 前置分析

2b 的目标是让 `MainWindow` 导航开始读取 2a 已落地的内置页面清单，但仍然不进入外部插件平台。

当前判断：

```text
可以进入 2b，但不建议直接在 XAML 模板内反射 HeaderPropertyName 或动态创建页面实例。
```

更稳的路线是先增加一个 Shell 专用导航项投影：

```text
ShellNavigationItemViewModel
- Descriptor
- Key
- HeaderText
- SortOrder
- IsVisible
- IsEnabled
```

`ShellNavigationItemViewModel` 从 `ShellPageDescriptor` 派生，但对 XAML 暴露的是已经解析好的 `HeaderText`。这样 `MainWindow.axaml` 不需要知道 `HeaderPropertyName`，也不需要在模板里做反射。

### 2.13 2b 推荐实现顺序

2b 建议拆成两个极小步骤：

```text
UI-COMPONENT-2b.1
新增 ShellNavigationItemViewModel，并在 MainWindowViewModel 暴露只读 ShellNavigationItems。

UI-COMPONENT-2b.2
再让 MainWindow.axaml 的 TabControl 读取 ShellNavigationItems。
```

这样做的好处是：

* 先验证导航项投影不会影响现有页面。
* 先解决语言切换时 HeaderText 刷新问题。
* XAML 迁移时先处理 Header-only bridge，不同时引入 `ItemsSource` 和模板。
* 如果 2b.2 风险较大，可以停在 2b.1，不影响当前 UI。

### 2.14 Header 刷新策略

当前 `MainWindowViewModel` 已在语言切换时对以下属性触发通知：

```text
WorkflowsSectionText
RunsSectionText
DataTabText
LogsTabText
SettingsMenuText
```

如果新增 `ShellNavigationItems`，需要同时保证：

* 语言切换后每个导航项的 `HeaderText` 刷新。
* 不把本地化后的 Header 字符串缓存成不可更新状态。
* `ShellPageDescriptor.HeaderPropertyName` 仍作为 descriptor 与 ViewModel 的契约测试来源。

推荐实现方式：

```text
MainWindowViewModel.RefreshShellNavigationItems()
```

在初始化和语言切换后重建或刷新导航项。第一版可以重建集合，暂不追求复杂的逐项属性通知。

### 2.15 页面承载策略

2b 不建议让 descriptor 直接保存页面实例。页面承载可选方案如下：

| 方案 | 做法 | 风险 | 建议 |
| --- | --- | --- | --- |
| 保留硬编码页面内容 | 只让导航 Header/顺序读取清单，页面内容暂时仍保留原五个页面 | `TabItem` 内容仍重复写在 XAML | 可作为最小迁移 |
| ShellNavigationItemViewModel 暴露 `ViewTypeName` | XAML 或 code-behind 根据类型创建 View | 会引入动态创建和 DataContext 风险 | 暂不做 |
| ShellNavigationItemViewModel 暴露页面 View 实例 | ViewModel 持有 View | 破坏 MVVM 边界 | 禁止 |
| 为五个页面建立页面级 ViewModel | 用 ViewLocator 承载页面 | 会扩大到业务 ViewModel 拆分 | 后置 |

因此 2b.2 如果进入 XAML，建议只迁移导航来源，不迁移页面创建机制；页面承载完全动态化应放到后续独立小步。

### 2.16 2b 必须避免的实现

2b 不应采用以下做法：

```text
在 XAML 里用反射解析 HeaderPropertyName
在 MainWindow.axaml.cs 写页面切换业务逻辑
让 MainWindowViewModel 持有 UserControl 实例
直接用外部 DLL 或 AssemblyLoadContext 作为页面来源
顺手拆分 MainWindowViewModel 的工作流、运行、数据、日志状态
改变五个页面内部绑定
改变后端 API 或发布结构
```

这些做法要么扩大范围，要么会让后续测试和发布 strict 路径变复杂。

### 2.17 2b 验收标准

如果进入 2b 代码实现，验收标准建议为：

* `BuiltinShellPages.All` 仍是导航顺序事实源。
* `MainWindowViewModel` 暴露的导航项顺序与 `BuiltinShellPages.All` 一致。
* 导航项 Header 在中文和英文之间切换时能刷新。
* `MainWindow.axaml` 如果改动，只改导航来源，不改五个页面内部布局。
* 五个页面仍共享当前 `MainWindowViewModel` DataContext。
* `MainWindow.axaml.cs` 仍不加入业务逻辑。
* `dotnet test "Avalonia_UI\Avalonia_UI.sln" --no-restore` 通过。

### 2.18 2b 结论和下一小步

结论：

```text
2b 可以做，但应先做 2b.1：ShellNavigationItemViewModel + MainWindowViewModel.ShellNavigationItems。
```

下一小步建议：

```text
UI-COMPONENT-2b.1：新增 ShellNavigationItemViewModel 和 ShellNavigationItems，只补 ViewModel 投影与测试，不改 MainWindow.axaml
```

### 2.19 UI-COMPONENT-2b.1 完成记录

2b.1 已完成最小代码实现：

```text
Avalonia_UI/ViewModels/ShellNavigationItemViewModel.cs
Avalonia_UI/ViewModels/MainWindowViewModel.cs
Avalonia_UI.Tests/MainWindowViewModelLocalizationTests.cs
```

已实现内容：

* `ShellNavigationItemViewModel` 从 `ShellPageDescriptor` 派生导航项投影。
* `MainWindowViewModel.ShellNavigationItems` 暴露固定顺序的 Shell 导航项集合。
* 初始化时根据 `BuiltinShellPages.All` 构建导航项。
* 语言切换时重建导航项，使 `HeaderText` 随中英文切换刷新。
* `MainWindow.axaml` 未迁移，现有五个 `TabItem` 仍保持原状。

测试覆盖：

* 导航项顺序与 `BuiltinShellPages.All` 一致。
* Header 属性、页面类型、默认可见和默认可用状态保持一致。
* 语言切换后导航项 Header 从英文刷新为简体中文。

下一小步建议：

```text
UI-COMPONENT-2b.2 前置复核：评估 MainWindow.axaml 是否可以只迁移导航 Header，不迁移 ItemsSource 和页面实例创建。
```

### 2.20 UI-COMPONENT-2b.2 前置复核结论

2b.2 的复核结论是：

```text
可以先让 MainWindow.axaml 的导航 Header 读取 ShellNavigationItems。
不建议同时迁移 TabControl.ItemsSource。
```

原因是当前 `MainWindow.axaml` 的五个 `TabItem` 同时承担两件事：

* 导航 Header。
* 页面内容承载。

如果只迁移 Header，页面内容仍然可以保持现有结构：

```text
TabItem Header -> ShellNavigationItems 派生文本
TabItem Content -> 现有 WorkflowPage / RunMonitorPage / DataPage / LogsAuditPage / SettingsPage
```

如果迁移 `ItemsSource`，`TabControl` 的 item 会变成 `ShellNavigationItemViewModel`，此时必须同时解决 selected content 的页面创建问题。那会立即牵动以下边界：

* `ContentTemplate` 或自定义模板选择器。
* 页面 View 创建生命周期。
* 页面 DataContext 继承。
* compiled binding 的模板类型。
* 是否允许 Shell 层动态创建 `UserControl`。

这些问题已经超出“只迁移导航读取清单”的最小范围。

### 2.21 2b.2 可选方案对比

| 方案 | 做法 | 风险 | 结论 |
| --- | --- | --- | --- |
| Header-only bridge | 保留五个硬编码 `TabItem` 内容，只把 Header 改为读取 `ShellNavigationItems` 投影 | 风险最低，页面内容不动 | 推荐 |
| Full ItemsSource | `TabControl.ItemsSource` 绑定 `ShellNavigationItems`，同时补 `ItemTemplate` 和 `ContentTemplate` | 会牵动页面创建和 DataContext | 暂不做 |
| Code-behind selector | 在 `MainWindow.axaml.cs` 按 Key 创建页面 | 破坏当前 code-behind 无业务逻辑状态 | 禁止 |
| ViewModel 持有 UserControl | 导航项直接带页面实例 | 破坏 MVVM 边界 | 禁止 |

因此 2b.2 不应理解为“完整动态 TabControl”，而应拆成更小的：

```text
UI-COMPONENT-2b.2a：MainWindow Header-only bridge
```

### 2.22 Header-only bridge 的推荐实现边界

如果进入代码，推荐只做：

```text
MainWindow.axaml
- 五个 TabItem 仍保留
- 五个页面内容仍保留
- Header 改为绑定 ShellNavigationItems 派生出的稳定 Header 文本
```

为避免 XAML 直接使用集合下标导致 compiled binding 风险，可以先在 `MainWindowViewModel` 暴露稳定的导航项属性：

```text
WorkflowsNavigationItem
RunsNavigationItem
DataNavigationItem
LogsNavigationItem
SettingsNavigationItem
```

然后 XAML Header 只做普通属性绑定：

```text
Header="{Binding WorkflowsNavigationItem.HeaderText}"
```

这样 `MainWindow.axaml` 开始读取 Shell 导航清单，同时不改变页面承载方式。

### 2.23 2b.2a 验收标准

如果进入 2b.2a，实现后应满足：

* `MainWindow.axaml` 只改五个 `TabItem.Header` 绑定。
* 五个 `TabItem` 的内容仍是原有五个页面。
* 不新增 `ContentTemplate`、模板选择器或页面工厂。
* `MainWindow.axaml.cs` 仍只有 `InitializeComponent()`。
* 中英文切换后五个导航 Header 仍刷新。
* 五个页面仍可正常显示。
* `dotnet test "Avalonia_UI\Avalonia_UI.sln" --no-restore` 通过。

### 2.24 2b.2 后置方向

Header-only bridge 稳定后，才重新评估：

```text
UI-COMPONENT-2b.3：是否引入 ShellPageContentTemplateSelector 或 AppShellPageHost
```

该后置方向才会讨论真正的 `ItemsSource + ContentTemplate`，不应和 2b.2a 混在同一个提交里。

### 2.25 UI-COMPONENT-2b.2a 完成记录

2b.2a 已完成 Header-only bridge：

```text
Avalonia_UI/ViewModels/MainWindowViewModel.cs
Avalonia_UI/Views/MainWindow.axaml
Avalonia_UI.Tests/MainWindowViewModelLocalizationTests.cs
```

已实现内容：

* `MainWindowViewModel` 暴露五个稳定导航项属性：`WorkflowsNavigationItem`、`RunsNavigationItem`、`DataNavigationItem`、`LogsNavigationItem`、`SettingsNavigationItem`。
* `MainWindow.axaml` 的五个 `TabItem.Header` 改为读取对应导航项的 `HeaderText`。
* 五个 `TabItem` 的页面内容仍保持原有 `WorkflowPage`、`RunMonitorPage`、`DataPage`、`LogsAuditPage`、`SettingsPage`。
* 未迁移 `TabControl.ItemsSource`。
* 未新增 `ContentTemplate`、模板选择器、页面工厂或 code-behind 页面切换逻辑。

测试覆盖：

* 导航项集合与五个稳定属性保持一致。
* 中英文切换后导航项 HeaderText 刷新。
* 全量 Avalonia 测试通过。

下一小步建议：

```text
UI-COMPONENT-2b.3 前置分析：是否引入 ShellPageContentTemplateSelector 或 AppShellPageHost，先只分析，不直接迁移 ItemsSource。
```

### 2.26 UI-COMPONENT-2b.3 前置分析

2b.3 需要回答的问题是：

```text
要不要从 Header-only bridge 继续推进到真正的 TabControl.ItemsSource + 页面内容动态承载？
```

当前结论：

```text
可以继续推进，但不建议下一步直接实现 TabControl.ItemsSource + ContentTemplateSelector。
更稳路线是先引入 AppShellPageHost，把五个页面承载从 MainWindow.axaml 中隔离出去。
```

原因是当前 `MainWindow.axaml` 中五个 `TabItem` 的页面内容仍是直接写死的：

```text
WorkflowPage
RunMonitorPage
DataPage
LogsAuditPage
SettingsPage
```

如果马上迁移 `TabControl.ItemsSource`，必须同时解决“选中导航项如何变成对应页面 View”的问题。这一步会把页面创建、DataContext、模板绑定和页面缓存策略揉在一起，风险高于 Header-only bridge。

### 2.27 方案对比

| 方案 | 做法 | 优点 | 风险 | 结论 |
| --- | --- | --- | --- | --- |
| 继续硬编码 | 维持五个 `TabItem` 内容不动 | 零风险 | `MainWindow.axaml` 仍承担页面承载 | 只是暂停，不是演进 |
| `ShellPageContentTemplateSelector` | `TabControl.ItemsSource` 绑定导航项，由模板选择器返回页面 View | 一步完成动态导航和内容 | 会立即引入页面创建策略、缓存策略和模板调试成本 | 暂不推荐 |
| `AppShellPageHost` | 先新建一个 Shell 页面承载组件，内部仍用五个固定页面 | 先把页面承载职责从 MainWindow 隔离出去，风险较低 | 仍未完全动态化 | 推荐下一小步 |
| 页面级 ViewModel + ViewLocator | 为五个页面建立独立 ViewModel，再由现有 `ViewLocator` 承载 | 长期更干净 | 会牵动业务状态拆分，范围过大 | 后置 |

2b.3 推荐先采用 `AppShellPageHost` 前置隔离，而不是直接做完整 `ItemsSource + ContentTemplateSelector`。

### 2.28 AppShellPageHost 的推荐边界

`AppShellPageHost` 第一版只做页面承载隔离：

```text
Avalonia_UI/Views/Components/Shell/AppShellPageHost.axaml
Avalonia_UI/Views/Components/Shell/AppShellPageHost.axaml.cs
```

第一版职责：

* 承载当前固定 `TabControl` 和五个页面 View。
* 继续继承 `MainWindowViewModel` DataContext。
* 不创建页面级 ViewModel。
* 不通过反射创建 View。
* 不读取外部 DLL。
* 不改变五个页面内部布局。

第一版可以仍使用固定结构，例如内部保留五个页面槽位；目标只是让 `MainWindow.axaml` 从“知道所有页面内容”收敛为“把页面承载交给 Shell 组件”。

### 2.29 暂不直接做 ContentTemplateSelector 的原因

`ShellPageContentTemplateSelector` 会让设计变得更接近最终形态，但此刻直接实现会带来几个额外决策：

* 页面是否每次选中都重新创建。
* 页面是否需要缓存。
* 页面创建失败如何显示。
* `ShellNavigationItemViewModel.ViewTypeName` 是否允许反射创建 View。
* 是否把页面 View 类型从字符串改为 `Type`。
* 模板内 DataContext 是导航项还是 `MainWindowViewModel`。
* 当前五个页面共享 `MainWindowViewModel` 的状态如何继承。

这些决策都不应该和 `MainWindow.axaml` 瘦身放在同一步。

### 2.30 2b.3 推荐拆分

推荐拆分为：

```text
UI-COMPONENT-2b.3a
新增 AppShellPageHost 组件，把五个页面内容从 MainWindow.axaml 移进去，不迁移 TabControl.ItemsSource。

UI-COMPONENT-2b.3b
复核 AppShellPageHost 稳定性，再评估是否让它根据 ShellNavigationItemViewModel.Key 显示页面。

UI-COMPONENT-2b.3c
最后才评估 ShellPageContentTemplateSelector 或页面工厂。
```

其中 2b.3a 的目标不是“动态页面系统”，而是“MainWindow 页面承载瘦身”。

### 2.31 2b.3a 验收标准

如果进入 2b.3a，实现后应满足：

* `MainWindow.axaml` 不再直接列出五个页面 View。
* 固定 `TabControl` 和五个页面 View 迁移到 `AppShellPageHost` 内部。
* `TabItem.Header` 仍读取 `ShellNavigationItems`。
* 五个页面仍继承当前 `MainWindowViewModel` DataContext。
* 不新增页面工厂、模板选择器或反射创建。
* `MainWindow.axaml.cs` 仍只有 `InitializeComponent()`。
* `dotnet test "Avalonia_UI\Avalonia_UI.sln" --no-restore` 通过。

### 2.32 2b.3 前置分析结论

结论：

```text
不直接做 ShellPageContentTemplateSelector。
下一步建议做 UI-COMPONENT-2b.3a：AppShellPageHost 页面承载隔离。
```

这样可以继续让 `MainWindow.axaml` 变薄，同时不把页面动态创建、页面缓存和 ViewModel 拆分提前拉进当前小步。

### 2.33 UI-COMPONENT-2b.3a 完成记录

2b.3a 已完成页面承载隔离：

```text
Avalonia_UI/Views/Components/Shell/AppShellPageHost.axaml
Avalonia_UI/Views/Components/Shell/AppShellPageHost.axaml.cs
Avalonia_UI/Views/MainWindow.axaml
```

已实现内容：

* 新增 `AppShellPageHost` 组件。
* 将固定 `TabControl` 和五个页面 View 从 `MainWindow.axaml` 移入 `AppShellPageHost`。
* `MainWindow.axaml` 只保留 Shell Header 和 `AppShellPageHost` 引用。
* `TabItem.Header` 仍读取 `ShellNavigationItems` 派生文本。
* 未迁移 `TabControl.ItemsSource`。
* 未新增 `ContentTemplate`、模板选择器、页面工厂、反射创建或 code-behind 页面切换逻辑。

测试结果：

* `dotnet test "Avalonia_UI\Avalonia_UI.sln" --no-restore --filter "BuiltinShellPagesTests|MainWindowViewModelLocalizationTests"` 通过。
* `dotnet test "Avalonia_UI\Avalonia_UI.sln" --no-restore` 通过。

下一小步建议：

```text
UI-COMPONENT-2b.3b：AppShellPageHost 稳定性复核，先确认 MainWindow 瘦身后的布局、DataContext 和语言切换边界，再决定是否进入 ItemsSource。
```

### 2.34 UI-COMPONENT-2b.3b 稳定性复核

2b.3b 的目标是复核 2b.3a 的边界是否稳定，而不是进入动态页面系统。

已补充结构测试：

```text
Avalonia_UI.Tests/AppShellPageHostStructureTests.cs
```

测试锁定以下事实：

* `MainWindow.axaml` 只引用 `AppShellPageHost`，不再直接引用五个页面 View。
* `AppShellPageHost.axaml` 内部仍使用固定 `TabControl`。
* 五个 `TabItem.Header` 仍读取稳定导航项的 `HeaderText`。
* 五个页面 View 仍固定存在于 `AppShellPageHost`。
* `AppShellPageHost` 仍未引入 `ItemsSource` 或 `ContentTemplate`。

2b.3b 完成后，才能进入下一步分析：

```text
UI-COMPONENT-2b.4：是否继续做 ItemsSource 前置模型，先分析，不直接改页面承载。
```

### 2.35 UI-COMPONENT-2b.4 ItemsSource 前置模型分析

2b.4 的问题不是“马上把 `TabControl.ItemsSource` 接上”，而是：

```text
在真正迁移 ItemsSource 之前，是否需要先补一个显式页面内容模型？
```

当前结论：

```text
需要，但仍不直接迁移 ItemsSource。
```

原因是当前 `ShellNavigationItemViewModel` 已有：

```text
Key
HeaderText
SortOrder
ViewTypeName
IsVisible
IsEnabled
```

这些字段足够表达导航项，但还不足以稳定表达“选中导航项后显示哪个页面内容”。如果直接让 XAML 根据 `ViewTypeName` 反射创建页面，会把页面创建策略、错误处理和 DataContext 继承都推到模板里，风险仍然偏高。

### 2.36 前置模型候选

建议在进入真实 `ItemsSource` 前，先考虑显式模型：

```text
ShellPageContentKey
- Workflows
- Runs
- Data
- Logs
- Settings
```

并让 `ShellNavigationItemViewModel` 派生出：

```text
ContentKey
```

这样后续 `AppShellPageHost` 可以基于稳定枚举切换页面内容，而不是基于 `ViewTypeName` 字符串反射。

### 2.37 方案对比

| 方案 | 做法 | 优点 | 风险 | 结论 |
| --- | --- | --- | --- | --- |
| 继续用 `ViewTypeName` | XAML 或 Host 根据类型名创建 View | 字段已存在 | 依赖反射和字符串，错误更晚暴露 | 暂不推荐 |
| 新增 `ShellPageContentKey` | 用枚举表示页面内容槽位 | 明确、可测试、无反射 | 需要多一个模型字段 | 推荐 |
| 直接页面实例 | 导航项持有 `UserControl` | 实现直观 | 破坏 MVVM 和生命周期边界 | 禁止 |
| 页面级 ViewModel | 先拆五个页面 ViewModel | 长期干净 | 范围过大 | 后置 |

推荐先做 `ShellPageContentKey`，然后再让 Host 根据枚举显式切换固定页面。

### 2.38 建议拆分顺序

2b.4 后续建议继续小步拆：

```text
UI-COMPONENT-2b.4a
新增 ShellPageContentKey，并让 ShellNavigationItemViewModel 暴露 ContentKey；补测试，不改 XAML。

UI-COMPONENT-2b.4b
新增 SelectedShellNavigationItem 或 SelectedShellPageKey 前置状态；补测试，不改页面承载。

UI-COMPONENT-2b.4c
再评估 AppShellPageHost 是否根据 SelectedShellPageKey 显示固定页面。

UI-COMPONENT-2b.4d
最后才评估 TabControl.ItemsSource。
```

其中 2b.4a 和 2b.4b 都仍是模型/ViewModel 前置，不改变用户界面。

### 2.39 2b.4 明确不做

本小步不做：

```text
不改 AppShellPageHost.axaml
不改 MainWindow.axaml
不迁移 TabControl.ItemsSource
不新增 ContentTemplate 或模板选择器
不新增页面工厂
不使用反射创建页面
不拆分五个页面的业务 ViewModel
```

### 2.40 2b.4 结论

结论：

```text
可以继续推进，但下一步只做 UI-COMPONENT-2b.4a：ShellPageContentKey 前置模型。
```

该小步完成后，后续动态页面承载才有稳定的内容键，不需要依赖 `ViewTypeName` 字符串或页面反射。

### 2.41 UI-COMPONENT-2b.4a 完成记录

2b.4a 已完成前置模型落地：

```text
Avalonia_UI/Models/ShellPageContentKey.cs
Avalonia_UI/Models/ShellPageDescriptor.cs
Avalonia_UI/Models/BuiltinShellPages.cs
Avalonia_UI/ViewModels/ShellNavigationItemViewModel.cs
Avalonia_UI.Tests/BuiltinShellPagesTests.cs
Avalonia_UI.Tests/MainWindowViewModelLocalizationTests.cs
```

已实现内容：

* 新增 `ShellPageContentKey`。
* `ShellPageDescriptor` 增加必填 `ContentKey`。
* `BuiltinShellPages` 为五个内置页面显式绑定内容键。
* `ShellNavigationItemViewModel` 暴露 `ContentKey`。
* 测试锁定内置页面清单和导航项投影的 `ContentKey` 映射。

仍未做：

* 未改 `MainWindow.axaml`。
* 未改 `AppShellPageHost.axaml`。
* 未迁移 `TabControl.ItemsSource`。
* 未新增 `ContentTemplate`、模板选择器、页面工厂或反射创建。

下一小步建议：

```text
UI-COMPONENT-2b.4b：SelectedShellNavigationItem / SelectedShellPageKey 前置状态分析，先只分析。
```

### 2.42 UI-COMPONENT-2b.4b 选中状态前置分析

2b.4b 的问题是：

```text
在 AppShellPageHost 能根据页面键显示内容之前，是否需要先把“当前选中的 Shell 页面”变成显式状态？
```

当前结论：

```text
需要，但本小步只分析，不直接新增状态代码。
```

原因是当前导航仍由固定 `TabControl` 自己维护选中项，`MainWindowViewModel` 并不知道当前 Shell 页面。后续如果想让 `AppShellPageHost` 根据内容键显示页面，必须先有一个稳定的 Shell 选中状态，否则 Host 只能继续依赖 XAML 固定 TabItem。

### 2.43 选中状态候选

可选方案如下：

| 方案 | 做法 | 优点 | 风险 | 结论 |
| --- | --- | --- | --- | --- |
| `SelectedShellPageKey` | ViewModel 保存当前 `ShellPageKey` | 简单、稳定、易测试 | 需要通过 key 再找到导航项和内容键 | 推荐 |
| `SelectedShellNavigationItem` | ViewModel 保存当前导航项对象 | XAML 绑定直观 | 语言切换重建集合时对象引用容易失效 | 暂不推荐作为唯一状态 |
| `SelectedShellPageContentKey` | ViewModel 保存内容键 | 适合 Host 显示内容 | 会丢失导航项身份和 Header 信息 | 可作为派生属性 |
| 直接让 Host 查询 TabControl | Host 自己读控件选中状态 | 不改 ViewModel | 控件耦合强，不利于测试 | 禁止 |

推荐以 `SelectedShellPageKey` 作为源状态，再派生：

```text
SelectedShellNavigationItem
SelectedShellPageContentKey
```

这样语言切换导致 `ShellNavigationItems` 重建时，可以通过稳定 key 重新解析当前导航项。

### 2.44 推荐状态边界

后续最小实现可考虑：

```text
private ShellPageKey selectedShellPageKey = ShellPageKey.Workflows;

public ShellPageKey SelectedShellPageKey
public ShellNavigationItemViewModel SelectedShellNavigationItem
public ShellPageContentKey SelectedShellPageContentKey
```

第一版只作为状态模型，不接 `TabControl.SelectedItem`，也不驱动 Host 内容切换。

状态刷新要求：

* 默认选中 `Workflows`。
* 语言切换重建 `ShellNavigationItems` 后，`SelectedShellNavigationItem` 仍能按 key 找回。
* `SelectedShellPageContentKey` 来自当前导航项的 `ContentKey`。
* 选中 key 非法时启动即拒绝或抛出明确错误，不做静默回退。

### 2.45 与 ItemsSource 的关系

`SelectedShellPageKey` 不是 `ItemsSource` 迁移本身，而是 ItemsSource 前置条件：

```text
2b.4b.1 先有稳定选中状态
2b.4c 再考虑 Host 是否根据 SelectedShellPageContentKey 显示固定页面
2b.4d 最后才考虑 TabControl.ItemsSource
```

因此本阶段仍不做：

```text
不改 MainWindow.axaml
不改 AppShellPageHost.axaml
不绑定 TabControl.SelectedItem
不迁移 TabControl.ItemsSource
不新增 ContentTemplate
不新增页面工厂
不创建或缓存页面实例
```

### 2.46 2b.4b 建议验收

如果进入代码实现，验收标准建议为：

* 默认 `SelectedShellPageKey` 为 `Workflows`。
* `SelectedShellNavigationItem.Key` 与 `SelectedShellPageKey` 一致。
* `SelectedShellPageContentKey` 与当前导航项 `ContentKey` 一致。
* 切换语言后选中状态仍保持同一个 key。
* 不改任何 XAML。
* 全量 Avalonia 测试通过。

### 2.47 2b.4b 结论

结论：

```text
下一步建议做 UI-COMPONENT-2b.4b.1：SelectedShellPageKey 前置状态，只补 ViewModel 状态和测试，不改 XAML。
```

### 2.48 UI-COMPONENT-2b.4b.1 完成记录

2b.4b.1 已完成前置状态落地：

```text
Avalonia_UI/ViewModels/MainWindowViewModel.cs
Avalonia_UI.Tests/MainWindowViewModelLocalizationTests.cs
```

已实现内容：

* 新增 `SelectedShellPageKey`，默认值为 `Workflows`。
* 新增派生属性 `SelectedShellNavigationItem`。
* 新增派生属性 `SelectedShellPageContentKey`。
* 切换语言导致 `ShellNavigationItems` 重建后，选中状态仍通过稳定 key 找回。
* 未知 `ShellPageKey` 会被明确拒绝。

界面显示影响：

```text
无。
```

本小步没有修改 `MainWindow.axaml`、`AppShellPageHost.axaml` 或任何页面/组件 XAML，也没有绑定 `TabControl.SelectedItem`。因此不需要提供 Gemini UI 修改文档。

下一小步建议：

```text
UI-COMPONENT-2b.4c 前置分析：AppShellPageHost 是否根据 SelectedShellPageContentKey 显示固定页面，先只分析。
```

### 2.49 UI-COMPONENT-2b.4c 前置分析

问题：

```text
AppShellPageHost 是否应该现在就根据 SelectedShellPageContentKey 显示固定页面？
```

当前事实：

* `MainWindowViewModel` 已有 `SelectedShellPageKey`。
* `SelectedShellNavigationItem` 可以从稳定 key 找回当前导航项。
* `SelectedShellPageContentKey` 已能派生出当前页面内容键。
* `AppShellPageHost.axaml` 内部仍是固定 `TabControl` 和五个固定 `TabItem`。
* 当前 `TabControl` 的选中状态仍由 Avalonia 控件内部维护，尚未与 `SelectedShellPageKey` 建立绑定或同步。

因此，现阶段不建议直接让 `AppShellPageHost` 按 `SelectedShellPageContentKey` 显示固定页面。

原因：

* `SelectedShellPageContentKey` 目前只代表 ViewModel 默认/程序侧状态，不代表用户在左侧 Tab 中实际点选的页面。
* 如果直接用内容键控制 Host 显隐页面，可能出现 ViewModel 认为选中了 A 页面，但 TabControl 实际仍停留在 B 页面的状态分裂。
* 这会让后续测试只能验证“派生属性存在”，不能验证“用户导航动作驱动页面承载”。
* 直接跳到内容键显隐也容易诱导提前实现 `ContentTemplateSelector`、页面工厂或 `ItemsSource` 迁移，不符合当前小步边界。

本小步结论：

```text
2b.4c 只确认边界：

暂不让 AppShellPageHost 根据 SelectedShellPageContentKey 显示页面。
先补一个更小的选中状态同步边界，让固定 TabControl 的当前页与 SelectedShellPageKey 对齐。
```

建议后续顺序：

| 小步 | 目标 | 是否改 XAML | 是否有可见变化 |
| --- | --- | --- | --- |
| 2b.4c.1 | 选中状态同步前置方案，明确 TabControl 与 SelectedShellPageKey 的绑定/桥接方式 | 否，先分析 | 否 |
| 2b.4c.2 | 最小同步实现，让固定 TabControl 选中项能更新 SelectedShellPageKey | 是，绑定级修改 | 理论无视觉变化 |
| 2b.4c.3 | 同步稳定性测试，覆盖默认页、用户切换、语言切换后仍保持同一页 | 视测试需要 | 否 |
| 2b.4c.4 | 再评估是否让 Host 按 SelectedShellPageContentKey 做固定内容分发 | 待定 | 待定 |

2b.4c.2 如果进入实现，应继续禁止：

* `TabControl.ItemsSource`
* `ContentTemplateSelector`
* 页面工厂
* 反射创建页面
* 外部插件化
* 动态模块加载

界面显示影响：

```text
本分析小步无界面显示变化。

后续 2b.4c.2 可能改 AppShellPageHost.axaml 的绑定方式，但目标只是让现有固定 TabControl 的选中状态同步到 ViewModel，不改变五个页面、左侧 Tab 形态、布局、文案或视觉层级。
```

Gemini 协作判断：

```text
当前 2b.4c 只改文档，不需要 Gemini 修改 View。

如果后续进入 2b.4c.2，属于绑定级 XAML 调整，原则上也不需要重新设计界面；
只有当需要改变 Tab 外观、布局层级或页面承载视觉结构时，才单独提供 Gemini View 层任务文档。
```

2b.4c 验收标准：

* 文档明确“不直接按 `SelectedShellPageContentKey` 显示页面”的原因。
* 文档明确下一步先做选中状态同步边界。
* 文档继续禁止 `ItemsSource`、模板选择器、页面工厂、反射创建和外部插件化。
* 不修改 Avalonia 源码。

下一小步建议：

```text
UI-COMPONENT-2b.4c.1：AppShellPageHost / TabControl 选中状态同步前置方案，先只分析绑定边界。
```

### 2.50 UI-COMPONENT-2b.4c.1 选中状态同步前置方案

目标：

```text
在不迁移 TabControl.ItemsSource、不引入模板选择器、不创建页面工厂的前提下，
让 AppShellPageHost 内部固定 TabControl 的当前选中页可以同步到 MainWindowViewModel 的 SelectedShellPageKey。
```

可选方案：

| 方案 | 做法 | 优点 | 风险 | 结论 |
| --- | --- | --- | --- | --- |
| A | 绑定 `TabControl.SelectedIndex` 到 ViewModel 新增的 `SelectedShellPageIndex` | 与当前固定五页 TabControl 最匹配，实现小，测试清楚 | index 是 UI 顺序语义，需要由内置页面清单统一约束 | 推荐 |
| B | 绑定每个 `TabItem.IsSelected` 到 `SelectedShellPageKey` | key 语义更直接 | 需要 converter 或多个布尔派生属性，XAML 噪声更大 | 暂不采用 |
| C | 绑定 `TabControl.SelectedItem` 到 `SelectedShellNavigationItem` | 语义接近导航项 | 当前 TabItem 不是由导航项生成，SelectedItem 实际是 TabItem 控件，容易错位 | 不采用 |
| D | 立即迁移为 `ItemsSource + ContentTemplateSelector` | 长期更动态 | 范围过大，会提前进入后续阶段 | 禁止 |

推荐方案：

```text
采用方案 A：

新增 SelectedShellPageIndex 作为固定 TabControl 的桥接属性。
SelectedShellPageIndex 只负责 UI 固定顺序与 SelectedShellPageKey 之间的同步。
业务语义仍以 SelectedShellPageKey / SelectedShellPageContentKey 为准。
```

推荐实现边界：

```text
MainWindowViewModel
  SelectedShellPageKey
  SelectedShellNavigationItem
  SelectedShellPageContentKey
  SelectedShellPageIndex

AppShellPageHost.axaml
  <TabControl TabStripPlacement="Left"
              SelectedIndex="{Binding SelectedShellPageIndex, Mode=TwoWay}">
      固定五个 TabItem
  </TabControl>
```

同步规则：

* `SelectedShellPageKey` 变更时，重新计算 `SelectedShellPageIndex`。
* `SelectedShellPageIndex` 变更时，按当前 `ShellNavigationItems` 顺序找回对应 `ShellPageKey`。
* 语言切换只刷新 Header，不应改变 `SelectedShellPageKey` 或 `SelectedShellPageIndex`。
* `SelectedShellPageIndex` 超出当前内置页面范围时应明确拒绝。
* `SelectedShellPageKey` 仍然拒绝未知 enum 值。

测试建议：

* 默认 `SelectedShellPageIndex == 0`。
* 设置 `SelectedShellPageIndex` 为日志页索引后，`SelectedShellPageKey == Logs`。
* 设置 `SelectedShellPageKey == Settings` 后，`SelectedShellPageIndex` 更新到设置页索引。
* 语言切换后，key、content key、index 均保持一致。
* 非法 index 被拒绝，且原选中状态不被破坏。
* `AppShellPageHost.axaml` 只增加 `SelectedIndex` 绑定，仍不包含 `ItemsSource` 或 `ContentTemplate`。

界面显示影响：

```text
预计无视觉变化。

用户仍看到同一个左侧 TabControl 和同五个页面；
变化只在内部状态同步，让用户点选页面后 ViewModel 能知道当前页。
```

Gemini 协作判断：

```text
不需要 Gemini 做视觉重设计。

如果需要让 Gemini 执行 View 层修改，只需给出绑定级任务：
在 AppShellPageHost.axaml 的现有固定 TabControl 上增加 SelectedIndex 双向绑定，
不得改页面顺序、样式、布局、Header 绑定或 TabItem 内容。
```

2b.4c.1 结论：

```text
下一步建议做 UI-COMPONENT-2b.4c.2：
实现 SelectedShellPageIndex 与固定 TabControl.SelectedIndex 的最小同步。
```

### 2.51 UI-COMPONENT-2b.4c.2 完成记录

2b.4c.2 已完成最小同步实现：

```text
Avalonia_UI/ViewModels/MainWindowViewModel.cs
Avalonia_UI/Views/Components/Shell/AppShellPageHost.axaml
Avalonia_UI.Tests/MainWindowViewModelLocalizationTests.cs
Avalonia_UI.Tests/AppShellPageHostStructureTests.cs
```

已实现内容：

* 新增 `SelectedShellPageIndex`，作为固定 `TabControl.SelectedIndex` 的桥接属性。
* `SelectedShellPageKey` 变更时，同步更新 `SelectedShellPageIndex`。
* `SelectedShellPageIndex` 变更时，同步更新 `SelectedShellPageKey`。
* 非法 `SelectedShellPageIndex` 会被明确拒绝，原选中状态保持不变。
* `AppShellPageHost.axaml` 只在现有固定 `TabControl` 上新增 `SelectedIndex="{Binding SelectedShellPageIndex, Mode=TwoWay}"`。
* 测试继续确认 `AppShellPageHost.axaml` 不包含 `ItemsSource` 或 `ContentTemplate`。

未实现内容：

* 未迁移 `TabControl.ItemsSource`。
* 未引入 `ContentTemplateSelector`。
* 未创建页面工厂。
* 未反射创建页面。
* 未引入外部插件化或动态模块加载。
* 未让 `AppShellPageHost` 根据 `SelectedShellPageContentKey` 做内容分发。

界面显示影响：

```text
理论无视觉变化。

用户仍看到原来的左侧 TabControl 和五个固定页面；
变化只是在用户切换页面后，ViewModel 能同步知道当前页。
```

测试结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore

通过：140
失败：0
跳过：0
```

下一小步建议：

```text
UI-COMPONENT-2b.4c.3：选中状态同步稳定性复核。

重点复核：
1. 是否需要补 UI 层 smoke 或截图确认无视觉变化。
2. 是否需要增加属性变更通知测试。
3. 是否可以进入“基于 SelectedShellPageContentKey 的固定内容分发”再次评估。
```

### 2.52 UI-COMPONENT-2b.4c.3 稳定性复核

复核结论：

```text
SelectedShellPageIndex 桥接已具备进入下一轮评估的最低稳定性。

但现阶段仍不建议立刻让 AppShellPageHost 根据 SelectedShellPageContentKey 做内容分发；
因为当前固定 TabControl 已经能承载五个固定页面，下一次改动应先单独评估内容分发是否真正降低复杂度。
```

本小步补充内容：

```text
Avalonia_UI.Tests/MainWindowViewModelLocalizationTests.cs
docs/UI组件MainWindow的后续计划.MD
```

已补测试：

* `SelectedShellPageKey` 变更时，会触发 `SelectedShellPageIndex` 和派生属性通知。
* `SelectedShellPageIndex` 变更时，会触发 `SelectedShellPageKey` 和派生属性通知。

UI smoke 判断：

```text
本小步未改 XAML。

2b.4c.2 的 XAML 改动只是固定 TabControl 的 SelectedIndex 绑定；
当前测试已覆盖绑定字符串、固定页面存在、无 ItemsSource、无 ContentTemplate。
暂不追加截图 smoke，避免为无视觉变化的小步扩大验证成本。
```

测试结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore

通过：142
失败：0
跳过：0
```

下一小步建议：

```text
UI-COMPONENT-2b.4d 前置分析：
再次评估“是否需要基于 SelectedShellPageContentKey 做固定内容分发”。

默认建议先不实现内容分发，除非能明确减少 AppShellPageHost 对 TabControl 的耦合，
并且仍然不引入 ItemsSource、ContentTemplateSelector、页面工厂或反射创建。
```

### 2.53 UI-COMPONENT-2b.4d 固定内容分发再评估

评估问题：

```text
在 SelectedShellPageKey / SelectedShellPageIndex 已经同步后，
是否应该继续让 AppShellPageHost 根据 SelectedShellPageContentKey 显示固定页面？
```

当前判断：

```text
暂不实现。
```

原因：

* 当前固定 `TabControl` 已同时承担导航和页面承载，且通过 `SelectedShellPageIndex` 与 ViewModel 同步。
* 如果此时再用 `SelectedShellPageContentKey` 做显隐分发，会让同一个页面选择同时由 `TabControl` 与额外内容分发逻辑维护，复杂度上升。
* `SelectedShellPageContentKey` 当前更适合作为后续内容承载解耦的语义前置，而不是马上驱动第二套页面显示逻辑。
* 真正要降低耦合时，更合理的下一阶段应先明确 Shell 导航区与内容区是否拆开，而不是在固定 `TabControl` 内部叠加内容键分发。

保留价值：

* `SelectedShellPageKey` 是当前稳定导航身份。
* `SelectedShellPageIndex` 是当前固定 `TabControl` 桥接属性。
* `SelectedShellPageContentKey` 保留为后续内容区解耦、页面注册或模板选择前的语义锚点。

明确不做：

* 不按 `SelectedShellPageContentKey` 增加页面显隐绑定。
* 不拆分当前 `TabControl` 的 Header 区和 Content 区。
* 不迁移 `ItemsSource`。
* 不引入 `ContentTemplateSelector`。
* 不创建页面工厂。
* 不反射创建页面。
* 不进入外部插件化。

后续建议：

```text
UI-COMPONENT-2b.4 可以在此收口。

下一轮如果继续组件化，建议进入 UI-COMPONENT-2b.5：
MainWindow / AppShellPageHost 边界总体验收与 Gemini View 协作说明整理。

如果要推进真正内容区解耦，应单独开 UI-COMPONENT-2c，
先做“Shell 导航区与内容区拆分边界分析”，再决定是否引入内容承载组件。
```

### 2.54 UI-COMPONENT-2b.5 MainWindow / AppShellPageHost 边界总体验收

验收目标：

```text
对 UI-COMPONENT-2b 当前成果做一次边界固化：

1. 明确 MainWindow 当前职责。
2. 明确 AppShellPageHost 当前职责。
3. 明确 Gemini 后续 View 层可改和不可改范围。
4. 明确下一阶段不应从哪里直接跳跃。
```

当前结构事实：

```text
Avalonia_UI/Views/MainWindow.axaml
  Window 声明
  Window.Styles
  Shell Header
  ConnectionStatusView
  AppShellPageHost 引用

Avalonia_UI/Views/Components/Shell/AppShellPageHost.axaml
  固定 TabControl
  SelectedIndex 双向绑定 SelectedShellPageIndex
  五个固定 TabItem
  五个固定页面 View
```

MainWindow 当前允许职责：

* 保留窗口级属性，例如标题、尺寸、背景。
* 保留窗口级样式，直到后续单独进入样式 ResourceDictionary 拆分。
* 保留 Shell Header 区域。
* 保留连接状态组件入口。
* 只通过 `<shell:AppShellPageHost />` 引入页面承载区。

MainWindow 当前不应恢复的职责：

* 不直接声明 `WorkflowPage`、`RunMonitorPage`、`DataPage`、`LogsAuditPage`、`SettingsPage`。
* 不重新接管页面 `TabControl`。
* 不在 `MainWindow.axaml` 中新增页面切换逻辑。
* 不在 `MainWindow.axaml` 中引入页面工厂、模板选择器或反射创建。

AppShellPageHost 当前允许职责：

* 固定承载现有五个内置页面。
* 使用固定 `TabControl` 做左侧导航。
* Header 继续绑定 `WorkflowsNavigationItem`、`RunsNavigationItem`、`DataNavigationItem`、`LogsNavigationItem`、`SettingsNavigationItem`。
* `SelectedIndex` 继续双向绑定 `SelectedShellPageIndex`。
* 页面内容仍使用固定页面 View。

AppShellPageHost 当前不应扩展的职责：

* 不迁移 `TabControl.ItemsSource`。
* 不引入 `ItemTemplate`。
* 不引入 `ContentTemplate` 或 `ContentTemplateSelector`。
* 不根据 `SelectedShellPageContentKey` 额外做一套显隐分发。
* 不创建页面工厂。
* 不反射创建页面。
* 不进入外部插件或模块加载。

ViewModel 当前边界：

* `ShellNavigationItems` 作为内置页面清单投影。
* `SelectedShellPageKey` 作为稳定导航身份。
* `SelectedShellNavigationItem` 作为当前导航项派生属性。
* `SelectedShellPageContentKey` 作为未来内容承载语义锚点。
* `SelectedShellPageIndex` 只作为固定 `TabControl.SelectedIndex` 的桥接属性。

测试边界：

```text
Avalonia_UI.Tests/BuiltinShellPagesTests.cs
Avalonia_UI.Tests/MainWindowViewModelLocalizationTests.cs
Avalonia_UI.Tests/AppShellPageHostStructureTests.cs
```

现有测试应继续保证：

* 内置页面清单顺序稳定。
* Header 本地化更新稳定。
* 选中 key / index / content key 同步稳定。
* MainWindow 不直接承载五个页面。
* AppShellPageHost 保持固定页面承载。
* AppShellPageHost 不包含 `ItemsSource` 或 `ContentTemplate`。

Gemini View 协作说明：

```text
当前阶段 Gemini 可以做 View 层美化和局部组件整理，但不得改变 Shell 承载架构。
```

Gemini 可改范围：

* 调整 `MainWindow.axaml` 中 Header 区域的视觉细节。
* 调整窗口级样式的视觉参数。
* 调整 `AppShellPageHost.axaml` 中固定 `TabControl` 的样式、间距和视觉状态。
* 在不改变绑定语义的前提下整理 XAML 层级。
* 继续拆分纯 View 组件，但必须保持 DataContext 和绑定路径不变。

Gemini 不可改范围：

* 不把五个页面移回 `MainWindow.axaml`。
* 不移除 `<shell:AppShellPageHost />`。
* 不删除 `SelectedIndex="{Binding SelectedShellPageIndex, Mode=TwoWay}"`。
* 不替换 `WorkflowsNavigationItem.HeaderText` 等 Header 绑定。
* 不引入 `ItemsSource`、`ItemTemplate`、`ContentTemplate`、`ContentTemplateSelector`。
* 不新增页面实例创建逻辑。
* 不新增外部模块扫描、插件加载或热更新。
* 不改变现有五个页面顺序。

Gemini 执行后的 Codex 复核要求：

* 运行 `dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore`。
* 复核 `MainWindow.axaml` 仍只引用 `AppShellPageHost`，不直接引用五个页面。
* 复核 `AppShellPageHost.axaml` 仍固定承载五个页面。
* 复核 `SelectedShellPageIndex` 绑定仍存在。
* 复核未引入 `ItemsSource` 或 `ContentTemplate`。

2b.5 结论：

```text
UI-COMPONENT-2b 可以作为“内置页面固定承载解耦”阶段收口。

下一步如果继续小步推进，建议先做 UI-COMPONENT-2c.0：
Shell 导航区与内容区拆分边界分析。

不建议直接进入 ItemsSource、ContentTemplateSelector、页面工厂或外部插件化。
```

### 2.55 UI-COMPONENT-2c.0 Shell 导航区与内容区拆分边界分析

分析目标：

```text
先判断是否应该把 Shell 导航区和内容区从当前固定 TabControl 中拆开。

本小步只做边界分析，不改 Avalonia 源码。
```

当前结构：

```text
AppShellPageHost
  TabControl
    TabItem Header=WorkflowsNavigationItem.HeaderText
      WorkflowPage
    TabItem Header=RunsNavigationItem.HeaderText
      RunMonitorPage
    TabItem Header=DataNavigationItem.HeaderText
      DataPage
    TabItem Header=LogsNavigationItem.HeaderText
      LogsAuditPage
    TabItem Header=SettingsNavigationItem.HeaderText
      SettingsPage
```

当前 `TabControl` 同时承担两类职责：

* 导航区：显示五个页面入口、处理用户选择、呈现选中态。
* 内容区：承载五个页面 View、根据当前选中 Tab 展示对应内容。

已经具备的前置条件：

* `ShellNavigationItems` 已能表达五个内置页面入口。
* `SelectedShellPageKey` 已能表达稳定导航身份。
* `SelectedShellPageIndex` 已能桥接当前固定 `TabControl.SelectedIndex`。
* `SelectedShellPageContentKey` 已能表达未来内容承载语义。
* `AppShellPageHost` 已从 `MainWindow` 中隔离出页面承载职责。

拆分后期望结构：

```text
AppShellPageHost
  ShellNavigationRegion
    固定或清单驱动的导航项

  ShellContentRegion
    当前选中页面内容
```

但这只是方向，不代表下一小步直接实现。

拆分收益：

* 导航区可以独立调整视觉、键盘行为和可用状态。
* 内容区可以单独定义页面承载策略。
* 后续如果进入页面注册或插件化，不需要继续把所有事情塞进 `TabControl`。
* `SelectedShellPageContentKey` 可以从语义锚点变成内容区选择依据。

拆分风险：

* 需要重新保证导航选中态与内容显示一致。
* 需要决定未选中页面是否保持实例、是否重建、是否缓存。
* 需要处理页面 DataContext 是否仍继承 `MainWindowViewModel`。
* 需要避免一次性引入 `ItemsSource`、模板选择器、页面工厂和缓存策略。
* 如果过早拆分，可能把当前稳定的固定五页承载变复杂。

2c.0 结论：

```text
可以进入“导航区 / 内容区拆分”的前置设计。

但下一小步仍不应直接迁移到 ItemsSource + ContentTemplateSelector。
更稳路线是先做只读结构方案：

1. 明确 ShellNavigationRegion 的输入和输出。
2. 明确 ShellContentRegion 的输入和输出。
3. 明确当前阶段是否继续固定五页。
4. 明确页面实例生命周期暂时不变。
```

推荐下一小步：

```text
UI-COMPONENT-2c.1：
ShellNavigationRegion / ShellContentRegion 最小结构方案。

只写文档和验收标准，不改 XAML。
```

2c.1 应回答：

* `ShellNavigationRegion` 是否可以先继续使用固定五个导航项。
* `ShellContentRegion` 是否可以先继续使用固定五个页面 View。
* 两个区域之间是否只通过 `SelectedShellPageKey` / `SelectedShellPageContentKey` 通信。
* 是否需要新增 ViewModel，还是先继续使用 `MainWindowViewModel`。
* 是否需要 Gemini 参与 View 层拆分，还是先由 Codex 做结构边界。

2c.1 之前明确禁止：

* 不迁移 `TabControl.ItemsSource`。
* 不引入 `ContentTemplateSelector`。
* 不引入页面工厂。
* 不引入页面缓存策略。
* 不反射创建页面。
* 不引入外部插件或模块加载。
* 不改变五个页面顺序。

Gemini 协作判断：

```text
2c.0 不需要 Gemini 修改 View。

如果后续进入 2c.2 或更后面的实际 XAML 拆分，
应先给 Gemini 一份明确的 View-only 任务：

1. 只拆 ShellNavigationRegion 和 ShellContentRegion 的 XAML 层级。
2. 不改变视觉设计。
3. 不改变五页顺序。
4. 不引入动态模板或页面创建逻辑。
5. 保留所有现有绑定语义。
```

### 2.56 UI-COMPONENT-2c.1 ShellNavigationRegion / ShellContentRegion 最小结构方案

方案目标：

```text
定义 ShellNavigationRegion 和 ShellContentRegion 的最小职责、输入、输出和验收标准。

本小步只写结构方案，不改 XAML，不新增控件，不新增 ViewModel。
```

最小结构建议：

```text
AppShellPageHost
  ShellNavigationRegion
    负责显示导航项和发起选择变化

  ShellContentRegion
    负责显示当前选中页面内容
```

当前阶段仍保持：

* 五个页面固定。
* 页面顺序固定。
* 页面实例仍由 XAML 静态声明。
* DataContext 仍继承 `MainWindowViewModel`。
* 选中状态仍以 `SelectedShellPageKey` 为稳定身份。
* 当前固定 `TabControl` 桥接仍由 `SelectedShellPageIndex` 承担。

#### ShellNavigationRegion

职责：

* 显示五个内置页面入口。
* 呈现当前选中态。
* 将用户选择同步回 Shell 选中状态。
* 保留 Header 本地化绑定。

输入：

```text
ShellNavigationItems
WorkflowsNavigationItem.HeaderText
RunsNavigationItem.HeaderText
DataNavigationItem.HeaderText
LogsNavigationItem.HeaderText
SettingsNavigationItem.HeaderText
SelectedShellPageKey
SelectedShellPageIndex
```

输出：

```text
SelectedShellPageKey
SelectedShellPageIndex
```

当前 2c 阶段约束：

* 可以继续用固定五个导航项。
* 可以继续用 `SelectedShellPageIndex` 桥接固定顺序。
* 暂不要求 `ShellNavigationItems` 直接驱动 `ItemsSource`。
* 暂不新增 `ShellNavigationRegionViewModel`。

#### ShellContentRegion

职责：

* 显示当前选中页面对应的内容。
* 保持五个现有页面的 DataContext 不变。
* 不承担导航 Header 渲染职责。
* 不承担页面实例创建策略。

输入：

```text
SelectedShellPageKey
SelectedShellPageContentKey
SelectedShellPageIndex
```

输出：

```text
无直接输出。

页面内部仍通过 MainWindowViewModel 的现有命令、集合和状态执行交互。
```

当前 2c 阶段约束：

* 可以继续固定声明五个页面 View。
* 暂不根据 `SelectedShellPageContentKey` 新增显隐分发。
* 暂不新增页面缓存策略。
* 暂不新增页面工厂。
* 暂不反射创建页面。
* 暂不引入外部页面注册。

#### 两个区域之间的通信

推荐通信边界：

```text
ShellNavigationRegion
  -> 修改 SelectedShellPageKey 或 SelectedShellPageIndex

MainWindowViewModel
  -> 保持 SelectedShellPageKey / SelectedShellPageIndex / SelectedShellPageContentKey 一致

ShellContentRegion
  -> 读取当前选中状态并显示对应固定页面
```

当前阶段不要让两个区域互相直接引用对方控件。

#### 是否新增 ViewModel

2c.1 结论：

```text
暂不新增 ViewModel。
```

原因：

* 当前 Shell 状态已经集中在 `MainWindowViewModel`。
* 新增区域 ViewModel 会立刻牵动 DataContext 切换和页面内部绑定继承。
* 当前更需要先稳定 View 层区域边界，而不是拆状态所有权。

后续只有在满足以下条件时，才重新评估区域 ViewModel：

* `MainWindowViewModel` 的 Shell 状态继续明显膨胀。
* 导航区出现独立命令、过滤、分组或权限状态。
* 内容区出现页面缓存、页面生命周期或动态注册策略。

#### 是否需要 Gemini

2c.1 结论：

```text
本小步不需要 Gemini 修改 View。

如果进入 2c.2 的实际 XAML 拆分，可以给 Gemini 一份 View-only 任务。
```

Gemini 后续可执行的最小 View-only 任务：

```text
在 AppShellPageHost.axaml 内进行纯 XAML 层级拆分：

1. 把导航相关 XAML 标注/整理为 ShellNavigationRegion。
2. 把页面内容相关 XAML 标注/整理为 ShellContentRegion。
3. 保留固定 TabControl 或等价固定结构。
4. 不改变视觉效果。
5. 不改变五个页面顺序。
6. 不改变 Header 绑定。
7. 不删除 SelectedShellPageIndex 双向绑定。
8. 不引入 ItemsSource、模板选择器、页面工厂或反射创建。
```

#### 2c.1 验收标准

* 文档明确 `ShellNavigationRegion` 的职责、输入和输出。
* 文档明确 `ShellContentRegion` 的职责、输入和输出。
* 文档明确两个区域之间只通过 ViewModel 状态通信，不互相引用控件。
* 文档明确当前阶段继续固定五页、固定顺序、固定页面声明。
* 文档明确暂不新增 ViewModel。
* 文档明确 Gemini 后续只能做 View-only 层级整理。
* 不修改 Avalonia 源码。

#### 2c.1 后续建议

```text
UI-COMPONENT-2c.2 前置分析：
是否可以在不改变视觉和不引入动态承载的前提下，
对 AppShellPageHost.axaml 做一次纯 XAML 层级整理。

如果答案为可以，再给 Gemini 或 Codex 一个极小 View-only 任务；
如果答案为不可以，则继续保持当前固定 TabControl 结构，转向样式 ResourceDictionary 拆分或状态所有权复核。
```

### 2.57 UI-COMPONENT-2c.2 AppShellPageHost 纯 XAML 层级整理前置分析

分析问题：

```text
是否可以在不改变视觉、不引入动态承载的前提下，
对 AppShellPageHost.axaml 做一次纯 XAML 层级整理？
```

当前 `AppShellPageHost.axaml` 结构：

```xml
<TabControl TabStripPlacement="Left"
            SelectedIndex="{Binding SelectedShellPageIndex, Mode=TwoWay}">
    <TabItem Header="{Binding WorkflowsNavigationItem.HeaderText}">
        <pages:WorkflowPage />
    </TabItem>
    ...
</TabControl>
```

关键事实：

* 当前固定 `TabControl` 同时拥有导航 Header 和选中内容承载。
* `TabItem.Header` 是导航入口。
* `TabItem.Content` 是页面内容。
* `SelectedIndex` 是当前导航和内容同步的桥。
* Avalonia 的 `TabControl` 模板内部负责 Header 区和 SelectedContent 区的呈现。

因此，若仍保留固定 `TabControl`，就不能真正把导航区和内容区拆成两个独立 XAML 区域。

可做的整理级别：

| 整理方式 | 是否可做 | 风险 | 结论 |
| --- | --- | --- | --- |
| 增加 XAML 注释标明当前 `TabControl` 是 combined shell region | 可以 | 无视觉变化，但收益较小 | 可选 |
| 给 `TabControl` 增加 `x:Name` 或辅助属性 | 可以 | 可能引入无用字段或误导后续依赖控件名 | 暂不需要 |
| 用外层 `Grid`/`Border` 包一层并命名为 Shell region | 可以 | 可能影响布局、样式命中或视觉间距 | 暂不推荐 |
| 拆成 `ShellNavigationRegion` 和 `ShellContentRegion` 两个 UserControl | 不应现在做 | 会打破 `TabControl` 的 Header/Content 内聚，需要重建选择和内容显示 | 暂不做 |
| 改成 `ListBox + ContentControl` | 不应现在做 | 需要内容分发、模板、页面生命周期策略 | 暂不做 |
| 改成 `ItemsSource + ContentTemplateSelector` | 禁止 | 直接进入动态承载 | 不做 |

2c.2 结论：

```text
不建议现在对 AppShellPageHost.axaml 做真实 XAML 层级拆分。

当前最稳做法是继续保留固定 TabControl，
并把它明确命名为“CombinedShellRegion”语义：
它暂时同时承担 ShellNavigationRegion 和 ShellContentRegion 的固定承载职责。
```

原因：

* 真正拆开导航区和内容区，会迫使我们重新实现 `TabControl` 已经稳定处理的选择和内容显示。
* 如果不引入 `ItemsSource`、`ContentTemplateSelector` 或页面工厂，拆分后的内容区只能靠显隐绑定或重复条件逻辑驱动，复杂度会变高。
* 当前 `SelectedShellPageIndex` 桥接已经能满足固定五页阶段的选中同步。
* 现阶段继续用固定 `TabControl` 更符合“小步、低风险、可验收”的路线。

对 Gemini 的判断：

```text
暂不建议让 Gemini 执行 2c.2 的 XAML 拆分。

如果只是增加注释或调整格式，收益不足以抵消协作返工成本；
如果做真实拆分，又会超过当前边界。
```

后续方向建议：

```text
UI-COMPONENT-2c.2 可以作为“暂缓真实 XAML 层级拆分”的分析收口。

下一步更稳方向二选一：

A. UI-COMPONENT-2c.3：CombinedShellRegion 命名与结构守护清单
   只写文档/测试清单，明确当前固定 TabControl 的角色。

B. UI-COMPONENT-3.0：样式 ResourceDictionary 拆分前置分析
   从低风险样式拆分继续降低 MainWindow.axaml 体积。
```

建议优先：

```text
先做 A。

原因是当前还在 Shell 承载边界线上，
先把 CombinedShellRegion 的命名和守护清单补齐，再转向样式拆分更稳。
```

2c.2 验收标准：

* 文档明确当前固定 `TabControl` 不能在不改变承载策略的情况下真实拆成独立导航区和内容区。
* 文档明确暂缓 XAML 层级拆分。
* 文档明确暂不需要 Gemini 执行 View 修改。
* 文档明确下一步优先做 CombinedShellRegion 命名与结构守护清单。
* 不修改 Avalonia 源码。

### 2.58 UI-COMPONENT-2c.3 CombinedShellRegion 命名与结构守护清单

本小步目标：

```text
把当前 AppShellPageHost 内部的固定 TabControl 正式命名为 CombinedShellRegion。

CombinedShellRegion 表示：
当前阶段导航区和内容区尚未拆开，
由同一个固定 TabControl 同时承担 ShellNavigationRegion 和 ShellContentRegion 的职责。
```

命名说明：

| 名称 | 含义 | 当前载体 |
| --- | --- | --- |
| `CombinedShellRegion` | 导航和内容合并承载区 | `AppShellPageHost.axaml` 内部固定 `TabControl` |
| `ShellNavigationRegion` | 未来可独立的导航区 | 当前由 `TabItem.Header` 承担 |
| `ShellContentRegion` | 未来可独立的内容区 | 当前由 `TabItem.Content` 承担 |

当前结构守护对象：

```xml
<TabControl TabStripPlacement="Left"
            SelectedIndex="{Binding SelectedShellPageIndex, Mode=TwoWay}">
    <TabItem Header="{Binding WorkflowsNavigationItem.HeaderText}">
        <pages:WorkflowPage />
    </TabItem>
    ...
</TabControl>
```

CombinedShellRegion 当前职责：

* 显示五个内置页面入口。
* 承载五个内置页面内容。
* 使用固定 `TabItem.Header` 绑定 Header 文案。
* 使用固定 `TabItem.Content` 承载页面 View。
* 通过 `SelectedIndex="{Binding SelectedShellPageIndex, Mode=TwoWay}"` 与 ViewModel 同步当前页。
* 保持页面 DataContext 继承 `MainWindowViewModel`。

CombinedShellRegion 当前不承担：

* 不从 `ShellNavigationItems` 直接生成导航项。
* 不通过 `ItemsSource` 生成 `TabItem`。
* 不通过 `ContentTemplate` 或 `ContentTemplateSelector` 创建页面。
* 不通过页面工厂创建页面。
* 不缓存或释放页面实例。
* 不反射创建页面。
* 不加载外部页面模块。

必须守住的结构项：

* `AppShellPageHost.axaml` 内仍存在一个固定 `TabControl`。
* `TabControl` 仍设置 `TabStripPlacement="Left"`。
* `TabControl` 仍绑定 `SelectedShellPageIndex`，且必须是 `Mode=TwoWay`。
* 五个 `TabItem` 顺序保持为 `Workflows`、`Runs`、`Data`、`Logs`、`Settings`。
* 五个 Header 绑定保持为现有导航项 HeaderText。
* 五个页面 View 保持固定声明。
* `MainWindow.axaml` 不直接恢复五个页面 View。
* `AppShellPageHost.axaml` 不出现 `ItemsSource`。
* `AppShellPageHost.axaml` 不出现 `ContentTemplate`。

结构测试清单：

```text
Avalonia_UI.Tests/AppShellPageHostStructureTests.cs
```

该测试文件后续应继续守护：

* `MainWindow.axaml` 只引用 `AppShellPageHost`。
* `MainWindow.axaml` 不直接引用五个页面 View。
* `AppShellPageHost.axaml` 包含固定 `TabControl`。
* `AppShellPageHost.axaml` 包含 `SelectedShellPageIndex` 双向绑定。
* `AppShellPageHost.axaml` 包含五个固定页面 View。
* `AppShellPageHost.axaml` 不包含 `ItemsSource`。
* `AppShellPageHost.axaml` 不包含 `ContentTemplate`。

ViewModel 守护清单：

```text
Avalonia_UI.Tests/MainWindowViewModelLocalizationTests.cs
```

该测试文件后续应继续守护：

* `SelectedShellPageKey` 默认值为 `Workflows`。
* `SelectedShellPageIndex` 默认值为 `0`。
* key 改变会同步 index。
* index 改变会同步 key。
* 语言切换后 key、index、content key 保持一致。
* 非法 key 和非法 index 被明确拒绝。
* 属性通知覆盖 key、index 和派生属性。

进入真实拆分前的门槛：

只有同时满足以下条件，才重新评估是否拆开 `ShellNavigationRegion` 和 `ShellContentRegion`：

* 已明确页面实例生命周期策略。
* 已明确页面是否缓存、何时创建、何时释放。
* 已明确内容区如何从 `SelectedShellPageContentKey` 映射到页面。
* 已明确是否接受 `ItemsSource` 或模板选择器。
* 已明确 Gemini 或 Codex 谁负责 View 层拆分。
* 已准备对应结构测试和 ViewModel 测试。

仍然禁止：

* 不在本阶段迁移 `TabControl.ItemsSource`。
* 不在本阶段引入 `ContentTemplateSelector`。
* 不在本阶段引入页面工厂。
* 不在本阶段引入页面缓存策略。
* 不在本阶段反射创建页面。
* 不在本阶段引入外部插件化。

2c.3 结论：

```text
UI-COMPONENT-2c 可以作为 Shell 承载边界收口：

当前正式承认 CombinedShellRegion 是阶段内稳定结构，
ShellNavigationRegion / ShellContentRegion 先作为未来拆分方向保留。
```

下一步建议：

```text
UI-COMPONENT-3.0：
样式 ResourceDictionary 拆分前置分析。

原因：
当前 Shell 承载边界已经收紧，
继续降低 MainWindow.axaml 体积时，样式拆分比页面动态承载风险更低。
```

### 2.59 UI-COMPONENT-3.0 样式 ResourceDictionary 拆分前置分析

分析目标：

```text
复核 MainWindow.axaml 当前 Window.Styles，
明确后续哪些样式适合拆入 ResourceDictionary，
哪些样式暂不拆，
以及拆分后的验证清单。

本小步只写文档，不改 Avalonia 源码，不新增样式文件。
```

当前事实：

```text
Avalonia_UI/App.axaml
  Application.Resources
    ResourceInclude -> Styles/ColorPalette.axaml
  Application.Styles
    FluentTheme

Avalonia_UI/Styles/ColorPalette.axaml
  Light / Dark ThemeDictionaries
  Brush 资源

Avalonia_UI/Views/MainWindow.axaml
  Window.Styles
    Button
    Button.Primary
    ListBoxItem
    TabControl
    TabItem
    Border.Card
```

当前已经完成的样式分层：

* 颜色和主题 Brush 已在 `Styles/ColorPalette.axaml`。
* `App.axaml` 已通过 `ResourceInclude` 引入 `ColorPalette.axaml`。
* 页面和组件大量使用 `DynamicResource` 引用颜色资源。

当前尚未完成的样式分层：

* 控件样式仍集中在 `MainWindow.axaml` 的 `Window.Styles`。
* `Button`、`ListBoxItem`、`TabControl`、`TabItem`、`Border.Card` 样式还未独立成 ResourceDictionary。
* `MainWindow.axaml` 仍承担窗口布局和控件样式两个职责。

拆分候选分组：

| 分组 | 当前选择器 | 建议目标文件 | 风险 | 结论 |
| --- | --- | --- | --- | --- |
| 通用按钮样式 | `Button`、`Button:pointerover`、`Button:pressed`、`Button.Primary` | `Styles/Controls/ButtonStyles.axaml` 或 `Styles/ControlStyles.axaml` | 影响全局按钮视觉 | 可作为首批候选 |
| 列表项样式 | `ListBoxItem`、hover、selected | `Styles/Controls/ListStyles.axaml` 或 `Styles/ControlStyles.axaml` | 影响工作流、运行、日志、数据列表 | 第二批候选 |
| Shell 导航样式 | `TabControl`、`TabItem` 及 Fluent 模板部件选择器 | `Styles/Shell/ShellNavigationStyles.axaml` | 与 CombinedShellRegion 强绑定，模板选择器较敏感 | 暂缓，后拆 |
| 卡片边框样式 | `Border.Card` | `Styles/Controls/CardStyles.axaml` 或 `Styles/ControlStyles.axaml` | 影响所有 Card 外观 | 可作为首批候选 |

推荐拆分顺序：

```text
3.1
先建立样式拆分清单和目标文件命名，不改 XAML。

3.2
只迁移低风险通用样式：
Button + Border.Card。

3.3
迁移 ListBoxItem 样式。

3.4
再评估 TabControl / TabItem Shell 导航样式是否迁移。
```

不建议第一步就迁移 `TabControl` / `TabItem` 的原因：

* 它们是 `CombinedShellRegion` 当前视觉和交互的核心。
* 包含 FluentTheme 模板部件选择器，例如 `PART_SelectedContentHost`、`PART_ItemsPresenter`、`PART_SelectedPipe`。
* 一旦迁移错误，可能导致左侧导航间距、选中态或内容区 Padding 变化。
* 当前 Shell 承载刚刚收口，导航样式应等通用样式拆分验证稳定后再动。

ResourceDictionary 命名建议：

```text
Avalonia_UI/Styles/ColorPalette.axaml
  已存在，继续只负责颜色和 Brush。

Avalonia_UI/Styles/ControlStyles.axaml
  近期建议优先方案，先集中承载 Button、ListBoxItem、Border.Card。

Avalonia_UI/Styles/ShellStyles.axaml
  后续可选，承载 TabControl / TabItem / CombinedShellRegion 相关样式。
```

短期不建议立刻拆成太多文件：

```text
ButtonStyles.axaml
ListStyles.axaml
CardStyles.axaml
ShellNavigationStyles.axaml
```

原因：

* 当前样式数量还不大。
* 文件过细会增加 `App.axaml` ResourceInclude 维护成本。
* 第一轮更需要验证样式迁移机制，而不是追求最终文件颗粒度。

3.0 拆分边界：

* 只分析，不改 `MainWindow.axaml`。
* 不新增 `ResourceDictionary` 文件。
* 不修改 `App.axaml`。
* 不修改 `ColorPalette.axaml`。
* 不修改控件视觉参数。
* 不移动 `CombinedShellRegion`。
* 不触碰 `ItemsSource`、模板选择器、页面工厂或插件化。

后续实现时的验收清单：

* `dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore` 通过。
* `App.axaml` 正确引入新增样式 ResourceDictionary。
* `ColorPalette.axaml` 仍只负责颜色和 Brush。
* `MainWindow.axaml` 中被迁移的样式不再重复存在。
* 迁移前后 `Button.Primary` 仍存在。
* 迁移前后 `Border.Card` 仍存在。
* 迁移前后 `CombinedShellRegion` 结构测试仍通过。
* 若迁移 Tab 样式，必须额外复核左侧导航视觉和 `SelectedShellPageIndex` 绑定。

Gemini 协作判断：

```text
3.0 不需要 Gemini 修改 View。

后续 3.2 / 3.3 如果只是搬迁样式文件，也优先由 Codex 执行；
Gemini 仅在需要视觉重设计或样式参数调整时参与。
```

3.0 结论：

```text
可以进入样式 ResourceDictionary 拆分路线。

下一小步建议：
UI-COMPONENT-3.1：样式拆分清单与目标文件命名固化。

仍然只写文档和验收标准，不改 XAML。
```

### 2.60 UI-COMPONENT-3.1 样式拆分清单与目标文件命名固化

本小步目标：

```text
固化样式拆分清单、目标文件命名和后续最小实现顺序。

本小步仍只写文档，不改 MainWindow.axaml，不新增样式文件，不修改 App.axaml。
```

术语说明：

```text
颜色和 Brush：
继续使用 ResourceDictionary / ResourceInclude。

控件 Style：
后续实现时优先使用 Avalonia Styles / StyleInclude。

阶段名称中的 ResourceDictionary 拆分，表示“样式资源从 MainWindow.axaml 中拆出”的大方向；
具体实现形式以后续 Avalonia 可编译、可测试的 StyleInclude 方案为准。
```

现有文件职责：

| 文件 | 当前职责 | 3.1 结论 |
| --- | --- | --- |
| `Avalonia_UI/Styles/ColorPalette.axaml` | Light / Dark Brush 资源 | 保持不动 |
| `Avalonia_UI/App.axaml` | 引入 `ColorPalette.axaml` 和 `FluentTheme` | 3.1 不改 |
| `Avalonia_UI/Views/MainWindow.axaml` | 窗口布局 + `Window.Styles` 控件样式 | 后续逐步迁出控件样式 |

目标文件命名：

| 目标文件 | 用途 | 阶段 | 状态 |
| --- | --- | --- | --- |
| `Avalonia_UI/Styles/ControlStyles.axaml` | 通用控件样式：Button、ListBoxItem、Border.Card | 3.2 / 3.3 | 后续新增 |
| `Avalonia_UI/Styles/ShellStyles.axaml` | Shell 导航样式：TabControl、TabItem、CombinedShellRegion 相关样式 | 3.4 或更后 | 暂缓 |

短期不采用的文件命名：

| 文件 | 暂不采用原因 |
| --- | --- |
| `ButtonStyles.axaml` | 第一轮文件过细，增加 include 维护成本 |
| `ListStyles.axaml` | 可先并入 `ControlStyles.axaml` |
| `CardStyles.axaml` | 可先并入 `ControlStyles.axaml` |
| `ShellNavigationStyles.axaml` | 后续如 Shell 样式继续膨胀，再考虑从 `ShellStyles.axaml` 细分 |

#### 3.2 首批迁移清单

目标：

```text
新增 Avalonia_UI/Styles/ControlStyles.axaml，
迁移低风险通用样式：
Button + Button.Primary + Border.Card。
```

首批迁移选择器：

```text
Button
Button:pointerover /template/ ContentPresenter
Button:pointerover
Button:pressed /template/ ContentPresenter
Button:pressed
Button.Primary
Button.Primary:pointerover /template/ ContentPresenter
Button.Primary:pressed /template/ ContentPresenter
Border.Card
```

首批暂不迁移：

```text
ListBoxItem
TabControl
TabItem
```

原因：

* `Button` 和 `Border.Card` 是通用控件视觉，迁移后容易通过全量测试验证。
* `ListBoxItem` 影响大量列表页面，作为第二批更稳。
* `TabControl` / `TabItem` 与 `CombinedShellRegion` 强相关，必须等通用样式迁移稳定后再评估。

3.2 后续实现验收：

* `ControlStyles.axaml` 新增后能被应用加载。
* `MainWindow.axaml` 中首批迁移的样式不再重复存在。
* `Button.Primary` 仍能使用。
* `Border.Card` 仍能使用。
* `ColorPalette.axaml` 不被修改。
* `dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore` 通过。

#### 3.3 第二批迁移清单

目标：

```text
继续迁移 ListBoxItem 相关样式到 ControlStyles.axaml。
```

第二批迁移选择器：

```text
ListBoxItem
ListBoxItem:pointerover
ListBoxItem:selected
```

3.3 后续实现验收：

* 工作流、运行、日志、数据页列表仍能渲染。
* `ListBoxItem` hover 和 selected 状态样式仍存在。
* 不改变列表数据绑定。
* 不修改页面 XAML。
* `dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore` 通过。

#### 3.4 Shell 样式暂缓清单

目标：

```text
只在 3.2 / 3.3 稳定后，再评估是否新增 ShellStyles.axaml。
```

暂缓选择器：

```text
TabControl
TabControl[TabStripPlacement=Left] /template/ ContentPresenter#PART_SelectedContentHost
TabControl[TabStripPlacement=Left] /template/ ItemsPresenter#PART_ItemsPresenter
TabItem
TabItem > TextBlock
TabItem:pointerover /template/ Border#PART_LayoutRoot
TabItem:pointerover /template/ ContentPresenter
TabItem:pointerover
TabItem:selected /template/ ContentPresenter
TabItem:selected
TabItem:selected /template/ Border#PART_SelectedPipe
```

暂缓原因：

* 这些样式直接影响 `CombinedShellRegion` 的左侧导航。
* 包含 FluentTheme 模板部件选择器，迁移风险高于普通控件样式。
* 迁移后需要额外做视觉复核，而不只是编译和单元测试。

3.4 前置门槛：

* 3.2 / 3.3 已通过。
* `AppShellPageHostStructureTests` 仍通过。
* 明确是否需要截图或手工视觉复核。
* 明确 Gemini 是否需要参与视觉确认。

#### App.axaml 后续引入策略

后续实现时建议：

```xml
<Application.Styles>
    <FluentTheme />
    <StyleInclude Source="avares://Avalonia_UI/Styles/ControlStyles.axaml"/>
</Application.Styles>
```

如果后续新增 `ShellStyles.axaml`：

```xml
<Application.Styles>
    <FluentTheme />
    <StyleInclude Source="avares://Avalonia_UI/Styles/ControlStyles.axaml"/>
    <StyleInclude Source="avares://Avalonia_UI/Styles/ShellStyles.axaml"/>
</Application.Styles>
```

注意：

* `ColorPalette.axaml` 继续在 `Application.Resources` 中通过 `ResourceInclude` 引入。
* 控件 Style 后续在 `Application.Styles` 中通过 `StyleInclude` 引入。
* 不把 Brush 资源和 Style 样式混进同一个文件。

#### 3.1 验收标准

* 文档明确目标文件命名。
* 文档明确 3.2 首批迁移范围。
* 文档明确 3.3 第二批迁移范围。
* 文档明确 3.4 Shell 样式暂缓原因。
* 文档明确 `ResourceInclude` 与 `StyleInclude` 的职责区别。
* 不修改 Avalonia 源码。
* 不新增样式文件。
* 不改变视觉效果。

#### 3.1 后续建议

```text
UI-COMPONENT-3.2：
新增 ControlStyles.axaml，并只迁移 Button + Button.Primary + Border.Card。

这是第一步真实样式拆分，范围最小，风险低于迁移 ListBoxItem 或 TabItem。
```

### 2.61 UI-COMPONENT-3.2 首批 ControlStyles 迁移完成记录

3.2 已完成首批真实样式拆分：

```text
Avalonia_UI/Styles/ControlStyles.axaml
Avalonia_UI/App.axaml
Avalonia_UI/Views/MainWindow.axaml
Avalonia_UI.Tests/StyleStructureTests.cs
```

已实现内容：

* 新增 `Avalonia_UI/Styles/ControlStyles.axaml`。
* 使用 `Application.Styles` 中的 `StyleInclude` 引入 `ControlStyles.axaml`。
* 将以下样式从 `MainWindow.axaml` 迁移到 `ControlStyles.axaml`：
  * `Button`
  * `Button:pointerover /template/ ContentPresenter`
  * `Button:pointerover`
  * `Button:pressed /template/ ContentPresenter`
  * `Button:pressed`
  * `Button.Primary`
  * `Button.Primary:pointerover /template/ ContentPresenter`
  * `Button.Primary:pressed /template/ ContentPresenter`
  * `Border.Card`
* 新增结构测试，确认 `App.axaml` 引入 `ControlStyles.axaml`。
* 新增结构测试，确认首批样式不再留在 `MainWindow.axaml`。

仍未迁移内容：

* `ListBoxItem`
* `ListBoxItem:pointerover`
* `ListBoxItem:selected`
* `TabControl`
* `TabItem`
* `CombinedShellRegion` 相关 Shell 导航样式

边界确认：

* 未修改 `ColorPalette.axaml`。
* 未修改视觉参数。
* 未移动 `CombinedShellRegion`。
* 未触碰 `ItemsSource`。
* 未引入 `ContentTemplateSelector`。
* 未引入页面工厂、页面缓存或外部插件化。

测试结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore

通过：145
失败：0
跳过：0
```

下一步建议：

```text
UI-COMPONENT-3.3：
继续迁移 ListBoxItem 相关样式到 ControlStyles.axaml。
```

### 2.62 UI-COMPONENT-3.3 ListBoxItem 样式迁移完成记录

3.3 已完成第二批控件样式迁移：

```text
Avalonia_UI/Styles/ControlStyles.axaml
Avalonia_UI/Views/MainWindow.axaml
Avalonia_UI.Tests/StyleStructureTests.cs
docs/UI组件MainWindow的后续计划.MD
```

已实现内容：

* 将以下样式从 `MainWindow.axaml` 迁移到 `ControlStyles.axaml`：
  * `ListBoxItem`
  * `ListBoxItem:pointerover`
  * `ListBoxItem:selected`
* 更新结构测试，确认 `ControlStyles.axaml` 拥有 `ListBoxItem` 相关样式。
* 更新结构测试，确认 `MainWindow.axaml` 不再拥有 `ListBoxItem` 基础样式。

当前 `ControlStyles.axaml` 已包含：

* `Button`
* `Button.Primary`
* `ListBoxItem`
* `Border.Card`

仍未迁移内容：

* `TabControl`
* `TabControl[TabStripPlacement=Left] /template/ ContentPresenter#PART_SelectedContentHost`
* `TabControl[TabStripPlacement=Left] /template/ ItemsPresenter#PART_ItemsPresenter`
* `TabItem`
* `TabItem > TextBlock`
* `TabItem:pointerover`
* `TabItem:selected`
* `TabItem:selected /template/ Border#PART_SelectedPipe`

边界确认：

* 未修改 `App.axaml`。
* 未修改 `ColorPalette.axaml`。
* 未移动 `CombinedShellRegion`。
* 未改页面 XAML。
* 未触碰 `ItemsSource`、模板选择器、页面工厂、页面缓存或插件化。

测试结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore

通过：145
失败：0
跳过：0
```

下一步建议：

```text
UI-COMPONENT-3.4：
评估 TabControl / TabItem / CombinedShellRegion 相关 Shell 样式是否迁移。

建议先分析，不直接迁移。
```

### 2.63 UI-COMPONENT-3.4 Shell 样式迁移评估与守护

3.4 评估对象：

```text
MainWindow.axaml 中剩余的 Window.Styles：

TabControl
TabControl[TabStripPlacement=Left] /template/ ContentPresenter#PART_SelectedContentHost
TabControl[TabStripPlacement=Left] /template/ ItemsPresenter#PART_ItemsPresenter
TabItem
TabItem > TextBlock
TabItem:pointerover /template/ Border#PART_LayoutRoot
TabItem:pointerover /template/ ContentPresenter
TabItem:pointerover
TabItem:selected /template/ ContentPresenter
TabItem:selected
TabItem:selected /template/ Border#PART_SelectedPipe
```

当前结论：

```text
暂缓迁移 Shell 样式。
```

原因：

* 这些样式直接服务 `CombinedShellRegion` 的左侧导航。
* 样式中包含 FluentTheme 模板部件选择器，迁移风险高于普通控件样式。
* 如果迁移到 `Application.Styles`，`TabItem` 通用选择器会扩大到未来所有 Tab 控件。
* 如果要避免全局作用域，需要先设计 Shell 专属 class 或局部 `StyleInclude` 策略，这会进入新的 XAML 结构决策。
* 当前 `CombinedShellRegion` 刚刚完成边界收口，暂缓迁移更稳。

本小步实际处理：

```text
不迁移 TabControl / TabItem 样式。
补充结构测试，明确当前 Shell 样式仍由 MainWindow.axaml 持有。
```

涉及文件：

```text
Avalonia_UI.Tests/StyleStructureTests.cs
docs/UI组件MainWindow的后续计划.MD
```

新增/增强测试：

* 确认 `App.axaml` 未引入 `ShellStyles.axaml`。
* 确认 `ControlStyles.axaml` 不持有 `TabControl` / `TabItem` 样式。
* 确认 `MainWindow.axaml` 仍持有全部 `TabControl` / `TabItem` / Fluent 模板部件样式。

测试结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore

通过：146
失败：0
跳过：0
```

后续重新评估 Shell 样式迁移的门槛：

* 已明确是否允许 Shell 样式全局化。
* 或已设计 `CombinedShellRegion` 专属 class / 局部样式作用域。
* 已准备视觉复核方案，至少覆盖左侧导航间距、选中态、hover、内容区 Padding。
* 已明确是否需要 Gemini 参与视觉确认。

3.4 结论：

```text
UI-COMPONENT-3 的真实样式拆分到此收口：

ControlStyles.axaml 负责通用控件样式；
MainWindow.axaml 暂时保留 CombinedShellRegion 的 Shell 导航样式。
```

下一步建议：

```text
UI-COMPONENT-3 后置总体验收复核：
汇总 3.0 到 3.4 的完成矩阵、测试结果、未迁移项和后续风险。
```

### 2.64 UI-COMPONENT-3 阶段总体验收复核

阶段目标：

```text
降低 MainWindow.axaml 的样式职责，
将低风险通用控件样式迁入独立样式文件，
并明确 CombinedShellRegion 相关 Shell 样式暂缓迁移。
```

完成矩阵：

| 小阶段 | 内容 | 结果 |
| --- | --- | --- |
| 3.0 | 样式 ResourceDictionary 拆分前置分析 | 已完成 |
| 3.1 | 样式拆分清单与目标文件命名固化 | 已完成 |
| 3.2 | 新增 `ControlStyles.axaml`，迁移 `Button` / `Button.Primary` / `Border.Card` | 已完成 |
| 3.3 | 迁移 `ListBoxItem` 样式 | 已完成 |
| 3.4 | 评估 Shell 样式迁移，暂缓并补结构守护测试 | 已完成 |

当前文件职责：

```text
Avalonia_UI/Styles/ColorPalette.axaml
  Light / Dark Brush 资源

Avalonia_UI/Styles/ControlStyles.axaml
  Button
  Button.Primary
  ListBoxItem
  Border.Card

Avalonia_UI/Views/MainWindow.axaml
  Window 壳
  Shell Header
  AppShellPageHost 引用
  CombinedShellRegion 相关 TabControl / TabItem 样式
```

已迁移样式：

* `Button`
* `Button:pointerover /template/ ContentPresenter`
* `Button:pointerover`
* `Button:pressed /template/ ContentPresenter`
* `Button:pressed`
* `Button.Primary`
* `Button.Primary:pointerover /template/ ContentPresenter`
* `Button.Primary:pressed /template/ ContentPresenter`
* `ListBoxItem`
* `ListBoxItem:pointerover`
* `ListBoxItem:selected`
* `Border.Card`

未迁移样式：

* `TabControl`
* `TabControl[TabStripPlacement=Left] /template/ ContentPresenter#PART_SelectedContentHost`
* `TabControl[TabStripPlacement=Left] /template/ ItemsPresenter#PART_ItemsPresenter`
* `TabItem`
* `TabItem > TextBlock`
* `TabItem:pointerover /template/ Border#PART_LayoutRoot`
* `TabItem:pointerover /template/ ContentPresenter`
* `TabItem:pointerover`
* `TabItem:selected /template/ ContentPresenter`
* `TabItem:selected`
* `TabItem:selected /template/ Border#PART_SelectedPipe`

未迁移原因：

```text
这些样式属于 CombinedShellRegion 的 Shell 导航视觉。
直接迁入 Application.Styles 会扩大作用域；
局部迁移则需要先设计 Shell 专属 class 或局部 StyleInclude 策略。
```

测试覆盖：

```text
Avalonia_UI.Tests/StyleStructureTests.cs
Avalonia_UI.Tests/AppShellPageHostStructureTests.cs
Avalonia_UI.Tests/MainWindowViewModelLocalizationTests.cs
```

测试结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore

通过：146
失败：0
跳过：0
```

边界确认：

* 未修改 `ColorPalette.axaml`。
* 未修改视觉参数。
* 未移动 `CombinedShellRegion`。
* 未迁移 `TabControl.ItemsSource`。
* 未引入 `ContentTemplateSelector`。
* 未引入页面工厂。
* 未引入页面缓存策略。
* 未反射创建页面。
* 未引入外部插件化。

后续建议：

```text
UI-COMPONENT-3 可以收口。

下一阶段建议先做 UI-COMPONENT-4.0：
MainWindow 剩余职责复核与下一轮低风险拆分方向分析。

不要直接进入 ShellStyles 迁移，除非先明确 Shell 样式作用域策略。
```

### 2.65 UI-COMPONENT-4.0 MainWindow 剩余职责与拆分候选分析

阶段目标：

```text
在 UI-COMPONENT-3 完成样式拆分后，
复核 MainWindow.axaml 当前还承担哪些职责，
选择下一轮最低风险拆分方向。

本小步只写文档，不改 Avalonia 源码。
```

当前 `MainWindow.axaml` 剩余职责：

```text
Window 声明
  Title / Icon / Width / Height / MinWidth / MinHeight / Background

Design.DataContext
  设计时 MainWindowViewModel

Window.Styles
  CombinedShellRegion 相关 TabControl / TabItem 样式

Root Grid
  Shell Header
    AppTitleText
    AppSubtitleText
    ConnectionStatusView

  AppShellPageHost
    CombinedShellRegion
```

职责评估：

| 职责 | 是否仍应留在 MainWindow | 原因 |
| --- | --- | --- |
| Window 属性 | 是 | 属于窗口壳本身 |
| Design.DataContext | 是 | 设计时辅助，拆分收益低 |
| CombinedShellRegion 样式 | 暂时是 | TabControl / TabItem 样式暂缓迁移，已有测试守护 |
| Shell Header 布局 | 可拆 | Header 是独立固定区域，已有 `ConnectionStatusView` 组件，可继续组件化 |
| ConnectionStatusView | 已拆 | 当前由 Header 区引用 |
| AppShellPageHost | 已拆 | 页面承载已从 MainWindow 隔离 |

拆分候选：

| 候选 | 目标 | 风险 | 结论 |
| --- | --- | --- | --- |
| `ShellHeaderView` | 把顶部标题、副标题和连接状态组合抽成组件 | 低，绑定仍继承 `MainWindowViewModel` | 推荐 |
| `MainWindowShellLayout` | 把 Root Grid 整体抽成组件 | 中，会让 MainWindow 只剩 Window 壳，但组件边界更大 | 暂缓 |
| `ShellStyles.axaml` | 迁移 TabControl / TabItem 样式 | 中高，涉及 CombinedShellRegion 视觉和样式作用域 | 暂缓 |
| `WindowChrome` / 外壳组件 | 抽窗口级属性或窗口行为 | 高，收益不明显 | 不做 |

推荐下一步：

```text
UI-COMPONENT-4.1：
ShellHeaderView 最小抽取前置方案。

只分析组件边界、输入输出、文件路径、测试守护，不直接改 XAML。
```

ShellHeaderView 推荐边界：

```text
Avalonia_UI/Views/Components/Shell/ShellHeaderView.axaml
Avalonia_UI/Views/Components/Shell/ShellHeaderView.axaml.cs
```

预期内容：

* 标题 `AppTitleText`。
* 副标题 `AppSubtitleText`。
* `ConnectionStatusView`。

预期不包含：

* `AppShellPageHost`。
* `CombinedShellRegion`。
* TabControl / TabItem 样式。
* 页面内容。
* 连接配置表单。
* 任何命令逻辑。

4.0 边界确认：

* 不修改 Avalonia 源码。
* 不迁移 Shell 样式。
* 不改 `ControlStyles.axaml`。
* 不改页面承载。
* 不触碰 `ItemsSource`、模板选择器、页面工厂、页面缓存或插件化。

### 2.66 UI-COMPONENT-4.1 ShellHeaderView 最小抽取前置方案

本小步目标：

```text
明确 ShellHeaderView 的最小组件边界、文件路径、绑定继承和测试守护。

本小步只写文档，不改 Avalonia 源码。
```

目标文件：

```text
Avalonia_UI/Views/Components/Shell/ShellHeaderView.axaml
Avalonia_UI/Views/Components/Shell/ShellHeaderView.axaml.cs
```

组件职责：

* 显示应用标题 `AppTitleText`。
* 显示应用副标题 `AppSubtitleText`。
* 承载 `ConnectionStatusView`。
* 保持当前 Header 的两列布局。
* 保持现有 margin、spacing、font 和 brush 设置。

组件不承担：

* 不承载 `AppShellPageHost`。
* 不承载 `CombinedShellRegion`。
* 不声明 `TabControl` 或 `TabItem`。
* 不声明 Shell 导航样式。
* 不处理连接命令。
* 不处理主题、语言或运行状态逻辑。
* 不新增 ViewModel。

DataContext 策略：

```text
ShellHeaderView 继续继承 MainWindow 的 DataContext。
ShellHeaderView.axaml 使用 x:DataType="vm:MainWindowViewModel"。
ConnectionStatusView 继续继承同一个 DataContext。
```

推荐 XAML 边界：

```xml
<UserControl ... x:DataType="vm:MainWindowViewModel">
    <Grid ColumnDefinitions="*,Auto" Margin="0,0,0,24">
        <StackPanel Spacing="6" VerticalAlignment="Center">
            <TextBlock Text="{Binding AppTitleText}" .../>
            <TextBlock Text="{Binding AppSubtitleText}" .../>
        </StackPanel>

        <components:ConnectionStatusView Grid.Column="1" VerticalAlignment="Center"/>
    </Grid>
</UserControl>
```

`MainWindow.axaml` 目标变化：

```xml
<Grid RowDefinitions="Auto,*" Margin="24">
    <shell:ShellHeaderView />
    <shell:AppShellPageHost Grid.Row="1" />
</Grid>
```

测试守护建议：

```text
Avalonia_UI.Tests/MainWindowShellStructureTests.cs
```

该测试应覆盖：

* `MainWindow.axaml` 引用 `<shell:ShellHeaderView />`。
* `MainWindow.axaml` 不再直接绑定 `AppTitleText` / `AppSubtitleText`。
* `MainWindow.axaml` 不再直接引用 `ConnectionStatusView`。
* `ShellHeaderView.axaml` 绑定 `AppTitleText`。
* `ShellHeaderView.axaml` 绑定 `AppSubtitleText`。
* `ShellHeaderView.axaml` 引用 `ConnectionStatusView`。
* `ShellHeaderView.axaml` 不引用 `AppShellPageHost`。
* `ShellHeaderView.axaml` 不声明 `TabControl` / `TabItem`。

4.1 结论：

```text
可以进入 UI-COMPONENT-4.2：
最小实现 ShellHeaderView 组件。

实现时只移动 Header XAML，不改变视觉参数、不改绑定语义、不新增 ViewModel。
```

### 2.67 UI-COMPONENT-4.2 ShellHeaderView 最小实现完成记录

4.2 已完成最小实现：

```text
Avalonia_UI/Views/Components/Shell/ShellHeaderView.axaml
Avalonia_UI/Views/Components/Shell/ShellHeaderView.axaml.cs
Avalonia_UI/Views/MainWindow.axaml
Avalonia_UI.Tests/MainWindowShellStructureTests.cs
```

已实现内容：

* 新增 `ShellHeaderView` 组件。
* 将 `AppTitleText` / `AppSubtitleText` / `ConnectionStatusView` 从 `MainWindow.axaml` 移入 `ShellHeaderView.axaml`。
* `MainWindow.axaml` 改为引用 `<shell:ShellHeaderView />`。
* 移除 `MainWindow.axaml` 中不再使用的 `components` 命名空间。
* 新增结构测试，确认 `MainWindow.axaml` 不再直接持有 Header 绑定。
* 新增结构测试，确认 `ShellHeaderView.axaml` 持有 Header 绑定和 `ConnectionStatusView`。

边界确认：

* 未改变 Header 视觉参数。
* 未新增 ViewModel。
* 未修改 `ConnectionStatusView`。
* 未移动 `AppShellPageHost`。
* 未移动 `CombinedShellRegion`。
* 未修改 TabControl / TabItem 样式。
* 未触碰 `ItemsSource`、模板选择器、页面工厂、页面缓存或插件化。

测试结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore

通过：148
失败：0
跳过：0
```

下一步建议：

```text
UI-COMPONENT-4.3：
MainWindow 剩余职责与阶段总体验收复核。
```

### 2.68 UI-COMPONENT-4 阶段总体验收复核

阶段目标：

```text
复核 MainWindow 剩余职责，
并完成下一轮最低风险拆分：
将 Shell Header 从 MainWindow 中抽离为 ShellHeaderView。
```

完成矩阵：

| 小阶段 | 内容 | 结果 |
| --- | --- | --- |
| 4.0 | MainWindow 剩余职责与拆分候选分析 | 已完成 |
| 4.1 | ShellHeaderView 最小抽取前置方案 | 已完成 |
| 4.2 | ShellHeaderView 最小实现与测试 | 已完成 |
| 4.3 | 阶段总体验收复核 | 已完成 |

当前 `MainWindow.axaml` 职责：

```text
Window 壳
Design.DataContext
CombinedShellRegion 相关 TabControl / TabItem 样式
Root Grid
  ShellHeaderView
  AppShellPageHost
```

当前 Shell 组件职责：

```text
ShellHeaderView
  AppTitleText
  AppSubtitleText
  ConnectionStatusView

AppShellPageHost
  CombinedShellRegion
  固定 TabControl
  五个固定页面
```

测试覆盖：

```text
Avalonia_UI.Tests/MainWindowShellStructureTests.cs
Avalonia_UI.Tests/AppShellPageHostStructureTests.cs
Avalonia_UI.Tests/StyleStructureTests.cs
Avalonia_UI.Tests/MainWindowViewModelLocalizationTests.cs
```

测试结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore

通过：148
失败：0
跳过：0
```

边界确认：

* 未改变 Header 视觉参数。
* 未新增 Shell Header ViewModel。
* 未修改 `ConnectionStatusView`。
* 未移动 `CombinedShellRegion`。
* 未迁移 TabControl / TabItem 样式。
* 未迁移 `ItemsSource`。
* 未引入 `ContentTemplateSelector`。
* 未引入页面工厂。
* 未引入页面缓存策略。
* 未反射创建页面。
* 未引入外部插件化。

UI-COMPONENT-4 结论：

```text
UI-COMPONENT-4 可以收口。

MainWindow 当前已经只保留窗口壳、Shell 样式守护和两个 Shell 区域入口：
ShellHeaderView + AppShellPageHost。
```

下一步建议：

```text
UI-COMPONENT-5.0：
MainWindow 剩余 Shell 样式作用域策略分析。

重点回答：
是否继续保留 TabControl / TabItem 样式在 MainWindow，
还是为 CombinedShellRegion 设计专属 class / ShellStyles.axaml 的局部作用域。
```

### 2.69 UI-COMPONENT-5.0 Shell 样式作用域策略分析

本小步只做策略分析和边界固化，不修改 Avalonia 代码。

当前事实：

```text
MainWindow.axaml
  Window.Styles
    TabControl
    TabControl[TabStripPlacement=Left] template styles
    TabItem
    TabItem pointerover / selected template styles

AppShellPageHost.axaml
  固定 TabControl
  五个固定 TabItem
  五个固定页面
```

这说明 `MainWindow.axaml` 当前仍持有 Shell 导航外观，但它的作用域是窗口局部的，不会自动影响后续其他窗口或其他普通 `TabControl`。

可选方案对比：

| 方案 | 做法 | 收益 | 风险 | 当前结论 |
| --- | --- | --- | --- | --- |
| A | 继续保留在 `MainWindow.Window.Styles` | 作用域最小，行为已被现有测试覆盖 | MainWindow 仍保留少量 Shell 样式职责 | 当前采用 |
| B | 迁入全局 `ShellStyles.axaml` 并由 `App.axaml` 引入 | MainWindow 更薄 | 未加选择器作用域时，`TabControl` / `TabItem` 会影响全应用 | 暂不采用 |
| C | 先设计 CombinedShellRegion 专属 class / 局部选择器，再决定迁移 | 为后续 ShellStyles 做准备 | 需要先验证 Avalonia selector 和视觉无回归 | 后续小步评估 |
| D | 直接迁入 `AppShellPageHost.UserControl.Styles` | 样式靠近承载组件 | 容易让页面承载和样式策略同时变化 | 暂不采用 |

最稳结论：

```text
UI-COMPONENT-5 阶段不直接迁移 ShellStyles.axaml。

当前先保留 MainWindow.Window.Styles，
并用测试明确：
1. Shell Tab 样式没有进入全局 App.axaml；
2. Shell Tab 样式没有进入 ControlStyles.axaml；
3. AppShellPageHost 仍只负责固定页面承载；
4. 不引入 ItemsSource / ContentTemplateSelector / 页面工厂。
```

后续如果要把 Shell 样式迁出 MainWindow，必须先满足：

```text
TabControl 有明确 Shell 专属标识；
TabItem 有明确 Shell 专属标识或可靠祖先选择器；
迁移后的 selector 不影响普通 TabControl；
迁移前后 dotnet test 通过；
迁移前后需要做 UI 截图或手工视觉核验；
不得顺手改页面承载方式。
```

本小步完成内容：

* 明确不把 `TabControl` / `TabItem` 样式直接放入全局 `ShellStyles.axaml`。
* 明确保留 `MainWindow.Window.Styles` 是当前最小风险方案。
* 明确后续如果迁移，必须先做 Shell 专属 selector 设计。
* 明确 UI-COMPONENT-5.1 优先补结构守护，不改变视觉。

下一步建议：

```text
UI-COMPONENT-5.1：
补充 Shell 样式作用域结构守护。

只增强测试或前置约束，
不迁移 ShellStyles.axaml，
不改变 MainWindow / AppShellPageHost 的视觉结构。
```

### 2.70 UI-COMPONENT-5.1 Shell 样式作用域结构守护完成记录

本小步采用测试守护路线，不修改 Avalonia 视图结构和视觉参数。

完成内容：

```text
Avalonia_UI.Tests/StyleStructureTests.cs
  新增 CombinedShellRegionStylesRemainWindowScoped
```

新增守护点：

* `App.axaml` 仍不引入 `ShellStyles.axaml`。
* `AppShellPageHost.axaml` 不持有 `UserControl.Styles`。
* `AppShellPageHost.axaml` 不持有 `StyleInclude`。
* `AppShellPageHost.axaml` 不直接持有 `Selector`。
* `TabControl`、`TabItem`、`TabItem:selected` 选择器仍位于 `MainWindow.Window.Styles` 内。

测试结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore

通过：149
失败：0
跳过：0
```

边界确认：

* 未迁移 `ShellStyles.axaml`。
* 未新增 `ShellStyles.axaml`。
* 未修改 `App.axaml` 样式 include。
* 未修改 `MainWindow.axaml`。
* 未修改 `AppShellPageHost.axaml`。
* 未改变 TabControl / TabItem 视觉。
* 未引入 `ItemsSource`。
* 未引入 `ContentTemplateSelector`。
* 未引入页面工厂、页面缓存、反射创建或外部插件化。

下一步建议：

```text
UI-COMPONENT-5.2：
做阶段总体验收复核。

汇总 5.0 到 5.1 的完成矩阵、测试结果、未完成事项和后续方向。
```

### 2.71 UI-COMPONENT-5 阶段总体验收复核

阶段目标：

```text
围绕 MainWindow 剩余 Shell 样式职责，
明确 TabControl / TabItem 样式是否迁移，
并补充最小结构守护。
```

完成矩阵：

| 小阶段 | 内容 | 结果 |
| --- | --- | --- |
| 5.0 | Shell 样式作用域策略分析 | 已完成 |
| 5.1 | Shell 样式作用域结构守护测试 | 已完成 |
| 5.2 | 阶段总体验收复核 | 已完成 |

当前结论：

```text
MainWindow 仍保留 Window.Styles 中的 CombinedShellRegion TabControl / TabItem 样式。

这是当前最稳方案：
样式仍是窗口局部作用域，
不会因为全局 ShellStyles include 影响后续普通 TabControl。
```

已固化守护：

* `App.axaml` 不引入 `ShellStyles.axaml`。
* `ControlStyles.axaml` 不持有 `TabControl` / `TabItem` 样式。
* `AppShellPageHost.axaml` 不持有 `UserControl.Styles`、`StyleInclude` 或 `Selector`。
* `MainWindow.axaml` 仍在 `Window.Styles` 内持有 Shell Tab 样式。
* `AppShellPageHost.axaml` 仍使用固定 `TabControl` 和五个固定页面。

测试覆盖：

```text
Avalonia_UI.Tests/StyleStructureTests.cs
Avalonia_UI.Tests/MainWindowShellStructureTests.cs
Avalonia_UI.Tests/AppShellPageHostStructureTests.cs
Avalonia_UI.Tests/MainWindowViewModelLocalizationTests.cs
```

测试结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore

通过：149
失败：0
跳过：0
```

本阶段明确未做：

* 未新增 `ShellStyles.axaml`。
* 未迁移 `TabControl` / `TabItem` 样式。
* 未修改 `App.axaml` 样式 include。
* 未给 `TabControl` / `TabItem` 新增 class。
* 未修改页面承载结构。
* 未引入 `ItemsSource`。
* 未引入 `ContentTemplateSelector`。
* 未引入页面工厂、页面缓存策略或反射创建页面。
* 未引入外部 DLL、模块扫描、插件安装或热更新。

后续如需继续迁移 Shell 样式，应另起小阶段先做：

```text
Shell 专属 selector 设计
→ 最小 XAML class 标识
→ dotnet test
→ UI 截图或手工视觉核验
→ 再决定是否新增 ShellStyles.axaml
```

UI-COMPONENT-5 结论：

```text
UI-COMPONENT-5 可以收口。

MainWindow 当前仍保留少量窗口级 Shell 样式，
这是有意保留的局部作用域边界，不是遗漏迁移。
```

### 2.72 UI-NODE-EDITOR-0 NodeEditorRegistry 边界分析

本小步开始从 Shell 组件化转入节点编辑入口主线，只做边界分析，不修改 Avalonia 代码。

当前代码事实：

```text
后端：
GET /api/v1/node-definitions 已存在。
NodeDefinitionView 返回 node_type、node_version、display_name、ports、execution_mode、timeout、retry_safe、ui_visibility。
Fault / Delay 测试节点不会出现在普通 node-definitions 返回中。
当前 API 明确不返回 implementation_path。
当前 API 明确不返回 config_schema。

桌面端：
EngineHostApiClient 已有 ListNodeDefinitionsAsync。
NodeDefinitionDto 已有 ui_visibility、ports、retry_safe 等只读字段。
WorkflowEditorView 当前仍是 JSON 草稿编辑器。
Avalonia_UI 还没有 NodeEditorRegistry / NodeEditorDescriptor / 节点专用编辑器承载层。
```

因此，`NodeEditorRegistry` 在当前阶段的定位不是后端节点目录，也不是 Schema 动态表单：

```text
NodeDefinition API
  负责告诉 UI 后端有哪些可用节点类型和只读元数据。

NodeEditorRegistry
  负责告诉 UI 某个 node_type 是否有内置专用编辑器。

JSON Draft Editor
  仍作为所有节点和工作流定义的兜底编辑入口。

JSON Schema Form
  后置到配置 Schema 明确返回后再做。
```

建议的最小职责：

| 对象 | 第一版职责 | 暂不负责 |
| --- | --- | --- |
| `NodeEditorDescriptor` | 描述一个内置编辑器支持的 `node_type`、显示名称、回退能力 | 创建外部程序集、动态加载 View |
| `NodeEditorRegistry` | 注册和查询内置编辑器描述 | 扫描 DLL、生命周期管理、热更新 |
| `WorkflowEditorView` | 继续保留 JSON 草稿编辑与校验保存 | 直接生成节点配置表单 |
| `NodeDefinitionDto` | 提供后端节点目录只读事实 | 暴露内部 dataclass 或 implementation_path |

最小可执行顺序建议：

```text
UI-NODE-EDITOR-1：
新增 NodeEditorDescriptor / NodeEditorRegistry 模型和单元测试。
只支持内存内置注册，不接入 XAML。

UI-NODE-EDITOR-2：
增加 BuiltinNodeEditors 只读清单。
先覆盖现有可见内置节点，编辑器类型统一为 JsonFallback。

UI-NODE-EDITOR-3：
在 ViewModel 层增加“当前选中节点可用编辑器状态”的派生模型。
不改变 WorkflowEditorView 视觉。

UI-NODE-EDITOR-4：
再决定是否给 Gemini 一份 UI 方案，
展示节点目录和编辑器可用状态，
但仍不做拖拽画布和 Schema 表单。
```

明确禁止提前实现：

* 不新增外部 DLL 加载。
* 不新增 `AssemblyLoadContext`。
* 不新增 `ui-modules` 扫描。
* 不实现 JSON Schema 动态表单。
* 不把后端 `NodeDefinitionSpec` dataclass 直接暴露给 UI。
* 不把 `implementation_path` 暴露给桌面端。
* 不实现拖拽画布。
* 不改变 Workflow 保存和 revision 冲突语义。

当前阶段建议：

```text
进入 UI-NODE-EDITOR-1。

先做纯模型和测试：
NodeEditorDescriptor / NodeEditorRegistry。
提交后再决定是否进入 BuiltinNodeEditors 清单。
```

### 2.73 UI-NODE-EDITOR-1 NodeEditorRegistry 最小模型完成记录

本小步只实现纯模型和单元测试，不接入 XAML、不改变界面。

完成内容：

```text
Avalonia_UI/Models/NodeEditorKind.cs
Avalonia_UI/Models/NodeEditorDescriptor.cs
Avalonia_UI/Models/NodeEditorRegistry.cs
Avalonia_UI.Tests/NodeEditorRegistryTests.cs
```

模型边界：

* `NodeEditorKind.JsonFallback` 表示当前只能回退 JSON 草稿编辑。
* `NodeEditorKind.BuiltIn` 预留内置专用编辑器类型。
* `NodeEditorDescriptor` 只描述前端编辑器能力，不复制后端 `NodeDefinitionSpec`。
* `NodeEditorRegistry` 只支持内存注册、稳定排序列表和按 `node_type` 查询。
* 重复 `node_type` 注册会直接拒绝。
* 空 `node_type` / 空显示名会直接拒绝。
* `BuiltIn` 编辑器必须声明 `ViewTypeName`。

测试结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore

通过：154
失败：0
跳过：0
```

边界确认：

* 未接入 `WorkflowEditorView`。
* 未修改 `MainWindowViewModel`。
* 未新增节点配置表单。
* 未新增 JSON Schema 渲染器。
* 未接入 `GET /api/v1/node-definitions` 的 UI 展示。
* 未实现外部 DLL、模块扫描、页面工厂或热更新。

下一步建议：

```text
UI-NODE-EDITOR-2：
增加 BuiltinNodeEditors 只读清单。

先为当前四个可见内置节点注册 JsonFallback 编辑器，
并用测试确认 Fault / Delay 测试节点不进入普通内置编辑器清单。
```

### 2.74 UI-NODE-EDITOR-2 BuiltinNodeEditors 只读清单完成记录

本小步只增加前端内置节点编辑器清单，不接入界面。

完成内容：

```text
Avalonia_UI/Models/BuiltinNodeEditors.cs
Avalonia_UI.Tests/BuiltinNodeEditorsTests.cs
```

当前注册清单：

| node_type | display_name | editor kind |
| --- | --- | --- |
| `GenerateTestTableNode` | `Generate Test Table` | `JsonFallback` |
| `FilterRowsNode` | `Filter Rows` | `JsonFallback` |
| `PublishSharedTablesNode` | `Publish Shared Tables` | `JsonFallback` |
| `ReadSharedTablesNode` | `Read Shared Tables` | `JsonFallback` |

测试节点规则：

```text
DelayTestNode 不进入 BuiltinNodeEditors。
FaultTestNode 不进入 BuiltinNodeEditors。
```

测试结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore

通过：157
失败：0
跳过：0
```

边界确认：

* 只读清单只用于前端编辑器能力注册。
* 未接入节点目录 UI。
* 未接入工作流编辑器。
* 未生成配置表单。
* 未新增专用节点编辑 View。
* 未暴露后端 `implementation_path`。
* 未引入外部 DLL 或模块扫描。

下一步建议：

```text
UI-NODE-EDITOR-3：
增加节点编辑器解析服务或派生模型。

输入：
NodeDefinitionDto 或 node_type。

输出：
是否有内置编辑器；
当前编辑器类型；
用户可读编辑器状态；
是否只能回退 JSON。

仍不修改 XAML。
```

### 2.75 UI-NODE-EDITOR-3 节点编辑器解析边界完成记录

本小步只增加编辑器解析模型，不接入 XAML、不改变工作流编辑器。

完成内容：

```text
Avalonia_UI/Models/NodeEditorResolution.cs
Avalonia_UI/Models/NodeEditorResolver.cs
Avalonia_UI.Tests/NodeEditorResolverTests.cs
```

解析输入：

```text
node_type
可选 display_name
NodeEditorRegistry
```

解析输出：

```text
NodeEditorResolution
  NodeType
  Kind
  DisplayName
  HasRegisteredEditor
  UsesJsonFallback
  StatusText
```

当前规则：

* 已注册 `JsonFallback` 编辑器的节点，返回 `HasRegisteredEditor=true` 且 `UsesJsonFallback=true`。
* 未注册节点仍可回退 JSON，返回 `HasRegisteredEditor=false` 且 `UsesJsonFallback=true`。
* 预留 `BuiltIn` 专用编辑器解析，返回 `UsesJsonFallback=false`。
* 未知节点没有显示名时，以 `node_type` 作为用户可读显示文本。

测试结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore

通过：161
失败：0
跳过：0
```

边界确认：

* 未修改 `WorkflowDefinitionDetailViewModel`。
* 未修改 `WorkflowEditorView`。
* 未新增节点目录 UI。
* 未新增专用节点编辑 View。
* 未实现 JSON Schema 表单。
* 未接入外部 DLL、模块扫描或动态页面承载。

下一步建议：

```text
UI-NODE-EDITOR-4：
做阶段小结与 Gemini 协作边界说明。

如果后续要让 UI 显示节点编辑器状态，
先给 Gemini 一份只读展示方案，
不要直接进入节点配置表单或拖拽画布。
```

### 2.76 UI-NODE-EDITOR-4 阶段小结与 Gemini 协作边界

本小步只做阶段复核和协作边界说明，不新增代码。

完成矩阵：

| 小阶段 | 内容 | 结果 |
| --- | --- | --- |
| UI-NODE-EDITOR-0 | NodeEditorRegistry 边界分析 | 已完成 |
| UI-NODE-EDITOR-1 | NodeEditorDescriptor / NodeEditorRegistry 最小模型 | 已完成 |
| UI-NODE-EDITOR-2 | BuiltinNodeEditors 只读清单 | 已完成 |
| UI-NODE-EDITOR-3 | NodeEditorResolver / NodeEditorResolution 解析层 | 已完成 |
| UI-NODE-EDITOR-4 | 阶段小结与协作边界 | 已完成 |

当前代码能力：

```text
前端可以在纯模型层完成：
node_type
→ NodeEditorRegistry
→ NodeEditorResolution
→ 判断是否有内置编辑器、是否回退 JSON、显示什么状态文本
```

当前仍不具备：

* 节点列表中展示编辑器状态。
* 点击节点后打开专用编辑器。
* JSON Schema 配置表单。
* 拖拽画布。
* 外部 DLL 模块加载。
* 节点配置保存的细粒度 UI。

测试结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore

通过：161
失败：0
跳过：0
```

如果交给 Gemini 做下一步 UI，只允许做只读展示设计：

```text
允许：
在 WorkflowDefinition 的节点列表中显示只读编辑器状态。
例如：
Editor: JSON fallback
Editor: Built-in editor
Editor: Not registered, JSON fallback

允许：
复用现有 WorkflowDefinitionDetailViewModel 的节点只读列表。

禁止：
新增节点配置表单。
新增拖拽画布。
改变 WorkflowDefinitionDraftJson 保存流程。
改变 Validate / Save / revision conflict 语义。
接入外部 DLL 或模块扫描。
把 node-definitions 变成创建节点按钮协议。
```

建议下一步：

```text
UI-NODE-EDITOR-5：
先做 ViewModel 只读状态接入前置分析。

重点确认：
WorkflowDefinitionNodeListItemViewModel 是否可以增加 NodeEditorResolution 派生字段；
是否需要本地化 StatusText；
是否需要把 BuiltinNodeEditors.CreateRegistry 注入 MainWindowViewModel；
如何避免异步 node-definitions 旧请求覆盖工作流草稿。
```

当前阶段结论：

```text
节点编辑入口主线已经完成纯模型基础。

下一步可以进入只读 UI 状态展示，
但仍不建议直接进入配置表单、Schema renderer 或拖拽式工作流编辑。
```

### 2.77 UI-NODE-EDITOR-5 ViewModel 只读状态接入前置分析

本小步只做接入方案分析，不修改 Avalonia 代码。

当前 UI 事实：

```text
WorkflowDefinitionDetailViewModel
  从 WorkflowDefinitionDto.definition.nodes 解析节点。
  生成 WorkflowDefinitionNodeListItemViewModel 列表。

WorkflowDefinitionNodeListItemViewModel
  当前字段：
    NodeInstanceId
    NodeType
    NodeVersion
    DisplayName
    Enabled
    ConfigJson
    TypeText
    DisplayNameText
    EnabledText

WorkflowSummaryView.axaml
  当前只读展示节点列表。
  已展示 node_instance_id、enabled、type、display_name、config json。
```

当前编辑器模型事实：

```text
BuiltinNodeEditors.CreateRegistry()
  当前注册四个普通内置节点。

NodeEditorResolver
  输入 node_type 和可选 display_name。
  输出 NodeEditorResolution。

NodeEditorResolution
  可表达：
    是否有注册编辑器；
    是否 JSON fallback；
    是否 BuiltIn 专用编辑器；
    状态文本。
```

候选接入点对比：

| 方案 | 做法 | 优点 | 风险 | 结论 |
| --- | --- | --- | --- | --- |
| A | `WorkflowDefinitionNodeListItemViewModel` 增加 `NodeEditorResolution` / 派生字段 | 最贴近节点只读列表；不碰主窗口全局状态；适合测试 | 需要向 `WorkflowDefinitionDetailViewModel` 传入 resolver | 推荐 |
| B | `MainWindowViewModel` 维护全局 `NodeEditorResolver` 并在 UI 绑定时查询 | 集中管理 | 容易把节点编辑状态塞回巨型 ViewModel | 暂不采用 |
| C | `WorkflowSummaryView.axaml` 直接根据 `NodeType` 展示文案 | 实现快 | XAML 写死业务规则，不利于后续专用编辑器 | 不采用 |
| D | 先接入 `GET /api/v1/node-definitions` 再生成编辑器状态 | 可结合后端可见性 | 需要处理异步加载、旧请求覆盖和缺失目录，范围变大 | 后置 |

推荐最小实现边界：

```text
UI-NODE-EDITOR-6：
只改 ViewModel 层和测试。

WorkflowDefinitionDetailViewModel
  新增可选 NodeEditorResolver 参数。
  默认使用 BuiltinNodeEditors.CreateRegistry() 创建 resolver。

WorkflowDefinitionNodeListItemViewModel
  新增 NodeEditorResolution 属性。
  新增只读派生字段：
    NodeEditorStatusText
    UsesJsonFallback
    HasRegisteredNodeEditor

WorkflowSummaryView.axaml
  暂不修改。
```

本地化判断：

```text
UI-NODE-EDITOR-6 不做本地化。

原因：
1. 该小步不展示到 UI；
2. NodeEditorResolution.StatusText 当前只是内部只读状态；
3. 等 Gemini 做只读展示方案时，再统一增加 l10n key。
```

关于 `BuiltinNodeEditors.CreateRegistry()` 注入：

```text
不建议直接注入 MainWindowViewModel 构造函数。

第一步更稳：
WorkflowDefinitionDetailViewModel 构造函数增加可选 NodeEditorResolver。
生产路径不传时使用 BuiltinNodeEditors.CreateRegistry()。
测试路径可传自定义 resolver。
```

关于异步 `node-definitions` 旧请求覆盖：

```text
UI-NODE-EDITOR-6 暂不接入 node-definitions 异步刷新。

原因：
当前只读编辑器能力来自本地 BuiltinNodeEditors，
不依赖网络请求，
因此不会新增旧请求覆盖工作流草稿的问题。

等进入节点目录 UI 或后端动态目录同步时，
再沿用 workflowDefinitionLoadVersion / loadVersion 机制处理竞态。
```

明确不做：

* 不修改 `WorkflowSummaryView.axaml`。
* 不新增节点编辑器状态可见 UI。
* 不修改 `MainWindowViewModel` 构造注入。
* 不调用 `ListNodeDefinitionsAsync`。
* 不生成配置表单。
* 不改变 Validate / Save / revision conflict 流程。
* 不改变 `WorkflowDefinitionDraftJson`。

建议下一步：

```text
UI-NODE-EDITOR-6：
按上述边界做 ViewModel 只读状态最小接入。

测试重点：
1. 已注册内置节点返回 JSON fallback registered 状态；
2. 未知节点返回 unregistered JSON fallback 状态；
3. 现有 WorkflowDefinition 解析和本地化测试不回归；
4. 不修改 XAML。
```

### 2.78 UI-NODE-EDITOR-6 ViewModel 只读状态最小接入完成记录

本小步只接入 ViewModel 层和测试，不修改 XAML。

完成内容：

```text
Avalonia_UI/ViewModels/WorkflowDefinitionDetailViewModel.cs
Avalonia_UI.Tests/MainWindowViewModelWorkflowTests.cs
```

接入方式：

```text
WorkflowDefinitionDetailViewModel
  新增可选 NodeEditorResolver 参数。
  默认使用 BuiltinNodeEditors.CreateRegistry()。
  解析 definition.nodes 时为每个节点生成 NodeEditorResolution。

WorkflowDefinitionNodeListItemViewModel
  新增 NodeEditorResolution。
  新增 NodeEditorStatusText。
  新增 HasRegisteredNodeEditor。
  新增 UsesJsonFallback。
```

当前行为：

* 已注册内置节点返回 `HasRegisteredNodeEditor=true`。
* 当前四个普通内置节点仍使用 `JsonFallback`。
* 未知节点返回 `HasRegisteredNodeEditor=false`。
* 未知节点仍可回退 JSON。
* `NodeEditorStatusText` 当前为内部英文状态文本，尚未展示到 UI。

测试结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore

通过：162
失败：0
跳过：0
```

边界确认：

* 未修改 `WorkflowSummaryView.axaml`。
* 未修改 `WorkflowEditorView.axaml`。
* 未修改 `MainWindow.axaml`。
* 未调用 `ListNodeDefinitionsAsync`。
* 未接入异步 node-definitions 刷新。
* 未新增节点配置表单。
* 未新增 JSON Schema renderer。
* 未新增拖拽画布。
* 未改变 Validate / Save / revision conflict 语义。

下一步建议：

```text
UI-NODE-EDITOR-7：
给 Gemini 准备只读 UI 展示说明。

允许：
在 WorkflowSummaryView 节点列表中增加只读编辑器状态文本。

禁止：
新增编辑按钮；
新增配置表单；
新增拖拽画布；
改变保存流程。
```

### 2.79 UI-NODE-EDITOR-7 Gemini 只读展示说明完成记录

本小步只补充 Gemini 协作任务说明，不修改 Avalonia XAML。

新增文档：

```text
docs/FlowWeaver_UI_NODE_EDITOR_7_Gemini只读展示任务说明.md
```

说明范围：

* 目标 View 为 `Avalonia_UI/Views/Components/Workflow/WorkflowSummaryView.axaml`。
* 目标列表为 WorkflowDefinition 的 Nodes Card。
* 允许只读展示 `NodeEditorStatusText`。
* 推荐展示文案为 `Editor: {NodeEditorStatusText}`。
* 推荐仅增加一行只读 `TextBlock`。
* `ConfigJson` 仍保留显示。

明确禁止：

* 不新增编辑按钮。
* 不新增配置按钮。
* 不新增打开编辑器命令。
* 不新增节点配置表单。
* 不新增 JSON Schema renderer。
* 不新增拖拽画布。
* 不调用 `ListNodeDefinitionsAsync`。
* 不修改保存、校验和 revision conflict 流程。

交给 Gemini 前的状态：

```text
Codex 已完成 ViewModel 只读状态字段：
NodeEditorStatusText
HasRegisteredNodeEditor
UsesJsonFallback

Gemini 只负责 View 层只读显示。
```

建议下一步：

```text
让 Gemini 按 docs/FlowWeaver_UI_NODE_EDITOR_7_Gemini只读展示任务说明.md 执行。

Gemini 完成后由 Codex 做：
UI-NODE-EDITOR-8 只读展示复核与本地化策略分析。
```

### 2.80 UI-NODE-EDITOR-8 只读展示复核与本地化策略

本小步复核 Gemini 的 View 层改动，并补充只读展示结构守护。

Gemini 实际改动：

```text
Avalonia_UI/Views/Components/Workflow/WorkflowSummaryView.axaml
```

改动内容：

* Nodes Card 的节点模板从 3 行调整为 4 行。
* 新增只读 `TextBlock`，绑定 `NodeEditorStatusText`。
* 原 `ConfigJson` 下移到第 4 行继续显示。
* 未新增按钮。
* 未新增命令。
* 未新增配置表单。

Codex 补充守护：

```text
Avalonia_UI.Tests/WorkflowSummaryViewStructureTests.cs
```

守护内容：

* 节点模板必须包含 `Text="{Binding NodeEditorStatusText}"`。
* 节点模板必须继续包含 `Text="{Binding ConfigJson}"`。
* 节点模板保留四行布局。
* 不引入 `EditNode`、`ConfigureNode`、`OpenNodeEditor`、`SaveNode`。
* 不引入 `ListNodeDefinitionsAsync`。

测试结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore

通过：164
失败：0
跳过：0
```

本地化策略：

```text
当前暂不新增 l10n key。

原因：
1. NodeEditorStatusText 仍是低风险只读状态文本；
2. 当前值来自模型层，主要用于确认状态链路；
3. 还没有正式设计“编辑器状态”用户文案；
4. 若现在本地化，容易把状态枚举、展示文案和后续专用编辑器语义提前固化。
```

后续如果要本地化，应另起小步：

```text
UI-NODE-EDITOR-L10N-1：
将 NodeEditorResolution.StatusText 改为稳定状态 key。

建议 key：
node_editor.status.json_fallback
node_editor.status.builtin
node_editor.status.unregistered_json_fallback

ViewModel 再通过 DisplayTextFormatter 或 LocalizationService 输出当前语言文本。
```

边界确认：

* 未新增节点编辑按钮。
* 未新增配置按钮。
* 未新增打开编辑器命令。
* 未新增 JSON Schema renderer。
* 未新增拖拽画布。
* 未修改 Validate / Save / revision conflict 流程。
* 未调用后端 node-definitions API。
* 未接入外部 DLL 或模块扫描。

建议下一步：

```text
UI-NODE-EDITOR-9：
做 NodeEditorRegistry / 只读展示阶段总体验收复核。

汇总 UI-NODE-EDITOR-0 到 UI-NODE-EDITOR-8，
明确当前已完成能力、测试、未完成能力和下一大方向。
```

### 2.81 UI-NODE-EDITOR-9 阶段总体验收复核

阶段目标：

```text
从 Shell 组件化转入节点编辑入口主线，
先建立前端 NodeEditorRegistry 基础，
再把节点编辑器状态以只读方式展示到 WorkflowDefinition 节点列表中。
```

完成矩阵：

| 小阶段 | 内容 | 结果 |
| --- | --- | --- |
| UI-NODE-EDITOR-0 | NodeEditorRegistry 边界分析 | 已完成 |
| UI-NODE-EDITOR-1 | NodeEditorDescriptor / NodeEditorRegistry 最小模型 | 已完成 |
| UI-NODE-EDITOR-2 | BuiltinNodeEditors 只读清单 | 已完成 |
| UI-NODE-EDITOR-3 | NodeEditorResolver / NodeEditorResolution 解析层 | 已完成 |
| UI-NODE-EDITOR-4 | 阶段小结与 Gemini 协作边界 | 已完成 |
| UI-NODE-EDITOR-5 | ViewModel 只读状态接入前置分析 | 已完成 |
| UI-NODE-EDITOR-6 | WorkflowDefinition 节点只读状态接入 | 已完成 |
| UI-NODE-EDITOR-7 | Gemini 只读展示任务说明 | 已完成 |
| UI-NODE-EDITOR-8 | 只读展示复核与本地化策略 | 已完成 |
| UI-NODE-EDITOR-9 | 阶段总体验收复核 | 已完成 |

当前已完成能力：

```text
NodeEditorDescriptor
NodeEditorRegistry
BuiltinNodeEditors
NodeEditorResolver
NodeEditorResolution
WorkflowDefinitionNodeListItemViewModel.NodeEditorResolution
WorkflowDefinitionNodeListItemViewModel.NodeEditorStatusText
WorkflowSummaryView 节点列表只读展示 NodeEditorStatusText
```

当前内置节点编辑器清单：

| node_type | editor |
| --- | --- |
| `GenerateTestTableNode` | `JsonFallback` |
| `FilterRowsNode` | `JsonFallback` |
| `PublishSharedTablesNode` | `JsonFallback` |
| `ReadSharedTablesNode` | `JsonFallback` |

测试覆盖：

```text
Avalonia_UI.Tests/NodeEditorRegistryTests.cs
Avalonia_UI.Tests/BuiltinNodeEditorsTests.cs
Avalonia_UI.Tests/NodeEditorResolverTests.cs
Avalonia_UI.Tests/MainWindowViewModelWorkflowTests.cs
Avalonia_UI.Tests/WorkflowSummaryViewStructureTests.cs
```

最终测试结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore

通过：164
失败：0
跳过：0
```

明确未完成能力：

* 没有节点专用编辑器 View。
* 没有节点配置表单。
* 没有 JSON Schema renderer。
* 没有拖拽画布。
* 没有节点添加/删除入口。
* 没有接入 `GET /api/v1/node-definitions` 的动态目录同步。
* 编辑器状态文本已完成简体中文 / English 本地化。
* 没有外部 DLL / `ui-modules` 扫描。
* 没有改变 Workflow 保存、校验、revision conflict 语义。

当前边界结论：

```text
NodeEditorRegistry 主线已经完成第一层基础：
前端知道某个 node_type 是否有编辑器能力，
并能在工作流定义只读视图中展示当前编辑器状态。

但它仍只是只读状态层，
不是节点配置编辑系统。
```

后续方向建议：

```text
方向 A：UI-NODE-EDITOR-L10N-1
先把 NodeEditorStatusText 从硬编码英文状态调整为本地化 key。
适合继续打磨只读用户体验。

方向 B：UI-NODE-CATALOG-1
接入 /api/v1/node-definitions 的只读节点目录页或面板。
适合开始展示后端可用节点，但仍不做创建/拖拽。

方向 C：NODE-CONFIG-SCHEMA-0
先回后端固定最小 config_schema 契约。
适合为未来配置表单打基础。
```

最稳建议：

```text
如果继续 UI 小步：
先做 UI-NODE-EDITOR-L10N-1。

如果准备进入真实节点配置：
先做 NODE-CONFIG-SCHEMA-0，不要直接在前端手写表单。
```

### 2.82 UI-NODE-EDITOR-L10N-1 节点编辑器状态本地化

阶段目标：

```text
把 NodeEditorStatusText 从模型层硬编码英文文案，
调整为稳定状态 key + DisplayTextFormatter 本地化输出。
```

完成内容：

```text
NodeEditorResolution.StatusText -> NodeEditorResolution.StatusKey
DisplayTextFormatter.FormatNodeEditorStatus(...)
Avalonia_UI/Localization/en-US.json 增加 node_editor.status.*
Avalonia_UI/Localization/zh-Hans.json 增加 node_editor.status.*
WorkflowDefinitionNodeListItemViewModel.NodeEditorStatusText 使用当前语言格式化
```

状态 key：

| key | English | 简体中文 |
| --- | --- | --- |
| `node_editor.status.builtin` | Built-in editor | 内置编辑器 |
| `node_editor.status.json_fallback` | JSON fallback | JSON 回退编辑器 |
| `node_editor.status.unregistered_json_fallback` | Not registered, JSON fallback | 未注册，使用 JSON 回退 |

测试覆盖：

```text
Avalonia_UI.Tests/NodeEditorResolverTests.cs
Avalonia_UI.Tests/MainWindowViewModelWorkflowTests.cs
Avalonia_UI.Tests/MainWindowViewModelLocalizationTests.cs
```

边界确认：

* 未修改 `WorkflowSummaryView.axaml` 的绑定结构。
* 未新增节点编辑按钮。
* 未新增节点配置表单。
* 本阶段未接入后端 node-definitions API；后续已由 UI-NODE-CATALOG-1 接入只读目录。
* 未改变 Workflow 保存、校验、revision conflict 语义。
* 语言切换后，新加载的 Workflow definition 会使用当前语言显示节点编辑器状态。

建议下一步：

```text
如果继续 UI 只读信息：
进入 UI-NODE-CATALOG-1，接入后端 /api/v1/node-definitions 的只读节点目录。

如果进入真实节点配置：
先做 NODE-CONFIG-SCHEMA-0，固定后端 config_schema 契约。
```

### 2.83 UI-NODE-CATALOG-1 只读节点目录接入

阶段目标：

```text
在 Avalonia Workflow 页接入后端 /api/v1/node-definitions，
展示普通 UI 可见节点的只读目录。
```

完成内容：

```text
NodeDefinitionListItemViewModel
MainWindowViewModel.NodeDefinitions
MainWindowViewModel.RefreshNodeDefinitionsCommand
WorkflowNodeCatalogView
WorkflowPage 右侧 Draft JSON 下方接入节点目录卡片
node_catalog.* 简体中文 / English 文案
```

只读展示字段：

| 字段 | 来源 | 用途 |
| --- | --- | --- |
| `display_name` | `NodeDefinitionDto` | 节点目录主标题 |
| `node_type` / `node_version` | `NodeDefinitionDto` | 稳定节点类型标识 |
| `input_ports` | `NodeDefinitionDto` | 输入端口摘要，必填端口以 `*` 标记 |
| `output_ports` | `NodeDefinitionDto` | 输出端口摘要 |
| `execution_mode` | `NodeDefinitionDto` | 执行模式只读展示 |
| `default_timeout_seconds` | `NodeDefinitionDto` | 默认超时只读展示 |

边界确认：

* 不新增节点创建按钮。
* 不新增节点删除按钮。
* 不新增节点配置表单。
* 不新增 JSON Schema renderer。
* 不新增拖拽画布。
* 不改变 Workflow 保存、校验、revision conflict 语义。
* 不在前端扫描测试节点或外部模块。
* Fault / Delay 测试节点仍由后端 `GET /api/v1/node-definitions` 过滤。

测试覆盖：

```text
Avalonia_UI.Tests/NodeDefinitionListItemViewModelTests.cs
Avalonia_UI.Tests/MainWindowViewModelWorkflowTests.cs
Avalonia_UI.Tests/WorkflowNodeCatalogViewStructureTests.cs
```

建议下一步：

```text
如果继续 UI 只读体验：
做 UI-NODE-CATALOG-2，补节点目录空态、错误态和视觉微调复核。

如果进入真实节点配置：
先做 NODE-CONFIG-SCHEMA-0，固定后端 config_schema 契约。
```

### 2.84 UI-NODE-CATALOG-2 只读节点目录状态复核

阶段目标：

```text
在不进入节点配置编辑的前提下，
补齐节点目录的空态、加载态、错误态、未连接禁用提示和本地化复核。
```

完成内容：

```text
HasNodeDefinitionCatalogEmptyState
RefreshNodeDefinitionsDisabledReasonText
NodeCatalogEmptyStateText
WorkflowNodeCatalogView 空态占位
WorkflowNodeCatalogView 禁用刷新 tooltip
node_catalog.empty_state 简体中文 / English 文案
```

状态边界：

| 状态 | 行为 |
| --- | --- |
| 未加载 / 空列表 | 显示空态占位，不显示表头和列表 |
| 加载中 | 显示 progress，刷新命令禁用，禁用原因为 busy |
| 加载成功有数据 | 显示表头和节点定义列表 |
| 加载成功无数据 | 显示空态，占位文案提示连接并刷新 |
| 加载失败 | 保留空态/已有列表状态，底部显示错误消息 |
| 未连接或未鉴权 | 刷新命令禁用，tooltip 显示 EngineHost 未连接或未鉴权 |

测试覆盖：

```text
Avalonia_UI.Tests/MainWindowViewModelWorkflowTests.cs
Avalonia_UI.Tests/MainWindowViewModelLocalizationTests.cs
Avalonia_UI.Tests/WorkflowNodeCatalogViewStructureTests.cs
```

验证结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore

通过：174
失败：0
跳过：0
```

边界确认：

* 未新增节点创建按钮。
* 未新增节点配置表单。
* 未新增 JSON Schema renderer。
* 未新增拖拽画布。
* 未改变 Workflow 保存、校验、revision conflict 语义。
* 未修改后端 `/api/v1/node-definitions`。
* 未进入 `config_schema` 契约设计或实现。

建议下一步：

```text
进入 NODE-CONFIG-SCHEMA-0。

先只做后端 config_schema 边界分析和契约清单，
不要直接实现 API 字段或前端表单。
```

### 2.85 NODE-CONFIG-SCHEMA-0 后端配置 Schema 边界清单

阶段目标：

```text
从只读节点目录进入真实节点配置前，
先固定后端 config_schema 的语义边界和最小契约。
```

完成文档：

```text
docs/FlowWeaver_NODE-CONFIG-SCHEMA-0_后端配置Schema边界清单.md
```

当前结论：

* 当前 `NodeDefinitionSpec` 还没有 `config_schema`。
* 当前 `GET /api/v1/node-definitions` 还没有返回 `config_schema`。
* 当前 workflow validation 还没有校验节点 config。
* 第一版建议新增 `config_schema_version` 和 `config_schema`。
* 第一版 schema 采用 FlowWeaver 最小子集，不承诺完整 JSON Schema。
* NODE-CONFIG-SCHEMA-1 只落后端字段、API 映射和 DTO 测试，不做 UI 表单。

四个普通内置节点的字段草案：

| 节点 | 字段 |
| --- | --- |
| `GenerateTestTableNode` | `rows`、`seed`、`columns` |
| `FilterRowsNode` | `field`、`operator`、`value` |
| `PublishSharedTablesNode` | `share_name`、`export_names`、`retention_seconds` |
| `ReadSharedTablesNode` | `share_name`、`version_policy`、`exact_version`、`selected_members` |

边界确认：

* 不实现 Avalonia 动态表单。
* 不实现节点添加/删除。
* 不实现拖拽画布。
* 不实现字段选择器或表选择器。
* 不改变 Workflow Save / Validate / revision conflict 流程。
* 不改变节点运行时 config 校验行为。
* 不把 Fault / Delay 测试节点暴露给普通 UI。

建议下一步：

```text
NODE-CONFIG-SCHEMA-1：
增加后端 config_schema_version / config_schema 最小 API 字段，
并补后端 API 测试与 Avalonia DTO 反序列化测试。
```

### 2.86 NODE-CONFIG-SCHEMA-1 后端配置 Schema 最小 API 字段

阶段目标：

```text
在不进入 UI 动态表单和 workflow config 校验的前提下，
让节点定义只读 API 返回后端声明的最小 config_schema 契约。
```

已完成：

* `NodeDefinitionSpec` 新增 `config_schema_version` 与 `config_schema`。
* 新增内部 `NodeConfigSchemaSpec` / `NodeConfigFieldSpec`，由 API 显式投影为普通 JSON 对象。
* `GET /api/v1/node-definitions` 返回 `config_schema_version` 和 `config_schema`。
* 四个普通内置节点补齐第一版配置字段事实：
  * `GenerateTestTableNode`：`rows`、`seed`、`columns`
  * `FilterRowsNode`：`field`、`operator`、`value`
  * `PublishSharedTablesNode`：`share_name`、`export_names`、`retention_seconds`
  * `ReadSharedTablesNode`：`share_name`、`version_policy`、`exact_version`、`selected_members`
* Avalonia `NodeDefinitionDto` 增加 `ConfigSchemaVersion` 和 `ConfigSchema`，只做 DTO 承接。
* 后端 API 测试覆盖 schema 关键事实、Fault / Delay 仍不暴露、`implementation_path` 仍不泄露。
* Avalonia API client 测试覆盖新字段反序列化。

本阶段明确未做：

* 不实现 Avalonia 动态表单。
* 不实现 workflow definition config 静态校验。
* 不改变 Workflow Save / Validate / revision conflict 流程。
* 不改变节点运行时 config 校验行为。
* 不把 Fault / Delay 测试节点暴露给普通 UI。

验证结果：

```text
.\python312\python.exe -m ruff check src\flowweaver\nodes\registry.py src\flowweaver\nodes\default_registry.py src\flowweaver\api\api_models.py src\flowweaver\api\routes_node_definitions.py tests\integration\test_api.py
.\python312\python.exe -m pytest -q tests\integration\test_api.py -k "node_definitions"
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "EngineHostApiClientTests"
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
```

下一步建议：

```text
UI-SCHEMA-0：
只做 Avalonia schema 解析模型与渲染边界分析，
不要直接生成节点配置表单。
```

### 2.87 UI-SCHEMA-0 Avalonia 配置 Schema 解析模型边界清单

阶段目标：

```text
在后端 config_schema API 字段可用之后，
先固定 Avalonia 如何解析、回退和承接 schema，
不直接进入动态表单生成。
```

完成文档：

```text
docs/FlowWeaver_UI-SCHEMA-0_Avalonia配置Schema解析模型边界清单.md
```

当前结论：

* schema 解析模型建议放在 `Avalonia_UI/Models`。
* 第一版 descriptor 只承接字段名、类型、标题、必填、默认值、最小值、枚举、数组 item type、描述和 warning。
* `ConfigSchema` 缺失、未知版本、根类型不支持、字段类型未知时，UI 应回退为只读提示或 JSON fallback，不阻断节点目录加载。
* 专用节点编辑器优先，通用 schema editor 次之，JSON editor 兜底。
* 第一版只允许只读摘要，不写回 `WorkflowDefinitionDraftJson`，不改变 Save / Validate / revision conflict 行为。
* Gemini 视图协作只允许做只读 schema 摘要展示，不要求动态控件生成。

本阶段明确未做：

* 不改 Avalonia 代码。
* 不实现动态配置表单。
* 不实现 config 草稿对象模型。
* 不实现 workflow definition 写回。
* 不实现字段选择器、表选择器或复杂数组对象编辑器。

建议下一步：

```text
UI-SCHEMA-1：
新增 Avalonia schema 解析模型和 parser 测试，
只解析 NodeDefinitionDto.ConfigSchema，
不生成 UI 表单。
```

### 2.88 UI-SCHEMA-1 Avalonia 配置 Schema 解析模型与 parser 测试

阶段目标：

```text
在不生成动态表单的前提下，
让 Avalonia 能把 NodeDefinitionDto.ConfigSchema 解析为稳定 UI 领域模型。
```

已完成：

* 新增 `NodeConfigFieldType`。
* 新增 `NodeConfigFieldDescriptor`。
* 新增 `NodeConfigSchemaDescriptor`。
* 新增 `NodeConfigSchemaParseResult`。
* 新增 `NodeConfigSchemaParser`。
* 新增 `NodeConfigSchemaParserTests`。

parser 当前支持：

* `config_schema_version == "1.0"`。
* 根 schema `type == "object"`。
* 字段类型：`string`、`integer`、`number`、`boolean`、`enum`、`array`、`object`。
* 字段属性：`title`、`required`、`default`、`minimum`、`enum`、`items.type`、`description`。
* 缺失 schema、缺失版本、未知版本、非 object 根类型的 unsupported 回退。
* properties 缺失、未知字段类型、非法 enum、非法 items 的 warning 保留。

本阶段明确未做：

* 不改 XAML。
* 不展示配置摘要。
* 不生成动态表单。
* 不创建 config 草稿对象。
* 不写回 `WorkflowDefinitionDraftJson`。
* 不改变 Save / Validate / revision conflict 行为。

验证结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "NodeConfigSchemaParserTests"
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
```

下一步建议：

```text
UI-NODE-CONFIG-1：
基于 parser 结果给节点目录或节点定义详情增加只读配置摘要，
不进入编辑控件、不写回 workflow JSON。
```

### 2.89 UI-NODE-CONFIG-1 只读节点配置摘要

阶段目标：

```text
基于 UI-SCHEMA-1 的 parser 结果，
在节点目录中展示只读配置字段摘要，
但不提供编辑控件，也不写回 workflow JSON。
```

已完成：

* `NodeDefinitionListItemViewModel` 解析 `NodeDefinitionDto.ConfigSchema`。
* 节点目录项新增 `ConfigSchemaSummaryText`。
* `DisplayTextFormatter` 新增配置 schema 摘要格式化入口。
* `WorkflowNodeCatalogView` 在节点目录项中显示只读配置摘要。
* `MainWindowViewModel` 创建节点目录项时传入当前本地化 formatter。
* 中英文资源补齐配置摘要文本。
* 测试覆盖有 schema、无 schema 和 XAML 只读绑定。

本阶段明确未做：

* 不新增配置按钮。
* 不新增动态表单控件。
* 不创建 config 草稿对象。
* 不写回 `WorkflowDefinitionDraftJson`。
* 不改变 Validate / Save / revision conflict 行为。

验证结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "NodeDefinitionListItemViewModelTests|WorkflowNodeCatalogViewStructureTests|NodeConfigSchemaParserTests"
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
```

下一步建议：

```text
UI-NODE-CONFIG-2 前置分析：
先确认配置草稿对象、字段控件映射、JSON fallback、
以及保存前如何与 WorkflowDefinitionDraftJson 建立边界，
不要直接做大表单。
```

### 2.90 UI-NODE-CONFIG-2 配置草稿与表单写回边界前置分析

阶段目标：

```text
在进入任何动态表单实现前，
先确认节点实例选择、配置草稿、JSON fallback 和写回 WorkflowDefinitionDraftJson 的边界。
```

完成文档：

```text
docs/FlowWeaver_UI-NODE-CONFIG-2_配置草稿与表单写回边界前置分析.md
```

当前结论：

* `NodeDefinition` 是节点类型目录，workflow node instance 的 `config` 才是可编辑对象。
* 配置草稿读取来源必须是 `WorkflowDefinitionDraftJson`，不能直接读旧的 `WorkflowDefinitionDetail.RawDefinitionJson`。
* 结构化配置编辑只能显式 Apply 回 `WorkflowDefinitionDraftJson`，再沿用现有 Validate / Save。
* Save 必须继续走 `UpdateWorkflowAsync(..., base_revision_id)`，不能绕过 revision conflict。
* 第一版可编辑字段只考虑 `string`、`integer`、`number`、`boolean`、`enum`。
* `array`、`object`、`unsupported` 先走只读摘要或 JSON fallback。
* 后端 config 静态校验不混入 UI-NODE-CONFIG-2。

本阶段明确未做：

* 不改 Avalonia 代码。
* 不新增动态表单。
* 不新增 Apply 命令。
* 不写回 workflow JSON。
* 不改后端 API。
* 不改变 Save / Validate / revision conflict 行为。

建议下一步：

```text
UI-NODE-CONFIG-2a：
新增 SelectedWorkflowDefinitionNode 前置状态和测试，
允许在 WorkflowDefinitionDetail.Nodes 中选择节点实例，
不生成配置表单，不写回 JSON。
```

### 2.91 UI-NODE-CONFIG-2a 选中 workflow 节点实例状态

阶段目标：

```text
为后续节点配置草稿提供稳定的 workflow node instance 选择状态，
但不生成配置表单，不读取 config draft，不写回 JSON。
```

已完成：

* `MainWindowViewModel` 新增 `SelectedWorkflowDefinitionNode`。
* 成功加载 workflow definition 后默认选中第一个节点实例。
* workflow detail 加载失败、revision 加载失败或切换 workflow 时清空选中节点实例。
* `WorkflowSummaryView` 的节点列表绑定 `SelectedItem`。
* 测试覆盖默认选中、切换 workflow 清空以及 XAML 选择绑定。

本阶段明确未做：

* 不生成配置表单。
* 不构建 `NodeConfigDraft`。
* 不读取或修改节点 `config`。
* 不写回 `WorkflowDefinitionDraftJson`。
* 不改变 Validate / Save / revision conflict 行为。

验证结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "MainWindowViewModelWorkflowTests|WorkflowSummaryViewStructureTests"
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
```

下一步建议：

```text
UI-NODE-CONFIG-2b：
新增 NodeConfigDraft 纯模型和 builder 测试，
从 WorkflowDefinitionDraftJson + selected node + node definition schema 生成草稿，
不显示表单，不写回 JSON。
```

### 2.92 UI-NODE-CONFIG-2b NodeConfigDraft 纯模型和 builder 测试

阶段目标：

```text
在不接入 ViewModel 和 XAML 的前提下，
建立从 WorkflowDefinitionDraftJson + selected node + schema 生成配置草稿的纯模型边界。
```

已完成：

* 新增 `NodeConfigDraftStatus`。
* 新增 `NodeConfigDraftField`。
* 新增 `NodeConfigDraft`。
* 新增 `NodeConfigDraftBuilder`。
* 新增 `NodeConfigDraftBuilderTests`。

builder 当前能力：

* 从 `WorkflowDefinitionDraftJson` 的 `nodes[]` 中定位 `node_instance_id`。
* 读取节点实例 `config`，缺失时按 `{}` 处理。
* 结合 `NodeConfigSchemaDescriptor` 生成字段草稿。
* 标记当前值、默认值、required、可编辑性和 warning。
* 对 invalid JSON、找不到节点、schema unsupported 返回状态和 warning。

本阶段明确未做：

* 不接入 `MainWindowViewModel`。
* 不改 XAML。
* 不展示 config draft。
* 不生成动态表单。
* 不提供 Apply 写回。
* 不修改 `WorkflowDefinitionDraftJson`。

验证结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "NodeConfigDraftBuilderTests|NodeConfigSchemaParserTests"
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
```

下一步建议：

```text
UI-NODE-CONFIG-2c：
基于 SelectedWorkflowDefinitionNode 和 NodeConfigDraftBuilder，
展示选中节点 config draft 只读摘要，
不生成编辑控件，不写回 JSON。
```

### 2.93 UI-NODE-CONFIG-2c 选中节点 config draft 只读摘要

阶段目标：

```text
把 SelectedWorkflowDefinitionNode、已加载 node definition schema
和当前 WorkflowDefinitionDraftJson 组合为只读配置草稿摘要，
但不生成编辑控件，也不写回 JSON。
```

已完成：

* `NodeDefinitionListItemViewModel` 暴露 `ConfigSchemaDescriptor`。
* `MainWindowViewModel` 新增 `SelectedNodeConfigDraftSummaryText` 计算属性。
* `MainWindowViewModel` 根据选中节点的 `node_type/node_version` 查找已加载节点定义 schema。
* `SelectedNodeConfigDraftSummaryText` 使用 `NodeConfigDraftBuilder` 只读生成摘要。
* `WorkflowSummaryView` 在节点卡片底部展示选中节点配置草稿摘要。
* 中英文资源补齐选中节点配置草稿摘要文本。
* 测试覆盖 schema 未加载回退、schema 加载后字段数量摘要、XAML 只读绑定。

本阶段明确未做：

* 不生成字段编辑控件。
* 不创建持久化 config draft 状态。
* 不新增 Apply 命令。
* 不写回 `WorkflowDefinitionDraftJson`。
* 不改变 Validate / Save / revision conflict 行为。

验证结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "MainWindowViewModelWorkflowTests|WorkflowSummaryViewStructureTests|NodeConfigDraftBuilderTests"
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
```

下一步建议：

```text
UI-NODE-CONFIG-2d：
先分析 Apply 写回 WorkflowDefinitionDraftJson 的最小边界，
确认如何保持 dirty、validation invalidation 和 revision conflict 语义，
再决定是否实现最小 Apply。
```

### 2.94 UI-NODE-CONFIG-2d Apply 写回边界与验收清单

阶段目标：

```text
在实现任何 Apply 写回前，
先确认写回算法、dirty / validation / revision conflict 继承语义和验收清单。
```

完成文档：

```text
docs/FlowWeaver_UI-NODE-CONFIG-2d_Apply写回边界与验收清单.md
```

当前结论：

* Apply 的唯一职责是把当前选中节点的 config 草稿写回 `WorkflowDefinitionDraftJson`。
* Apply 不调用后端、不调用 Validate、不调用 Save、不刷新 workflow detail。
* Apply 必须通过设置 `WorkflowDefinitionDraftJson = updatedJson` 触发现有 dirty 和 validation invalidation 逻辑。
* revision conflict 状态下第一版 Apply 应拒绝或保持不可用，不能清空 conflict 标记。
* 第一版 patcher 应拒绝无效 JSON、找不到节点、`node.config` 非 object 等不安全情况。
* 最小实现应先做纯 `NodeConfigDraftJsonPatcher`，不直接接按钮。

本阶段明确未做：

* 不改 Avalonia 代码。
* 不新增 Apply 命令。
* 不实现动态表单。
* 不写回 `WorkflowDefinitionDraftJson`。
* 不改后端 API。

建议下一步：

```text
UI-NODE-CONFIG-2d.1：
新增 NodeConfigDraftJsonPatcher 纯模型和测试，
只验证 JSON patch 算法，
不接 MainWindowViewModel，不加 Apply 按钮。
```

### 2.95 UI-NODE-CONFIG-2d.1 NodeConfigDraftJsonPatcher 纯模型和测试

阶段目标：

```text
先实现 workflow draft JSON 的纯 patch 算法，
验证选中节点 config 替换/新增和错误状态，
不接 MainWindowViewModel，不加 Apply 按钮。
```

已完成：

* 新增 `NodeConfigDraftApplyStatus`。
* 新增 `NodeConfigDraftApplyResult`。
* 新增 `NodeConfigDraftJsonPatcher`。
* 新增 `NodeConfigDraftJsonPatcherTests`。

patcher 当前能力：

* 替换选中节点已有 object config。
* 缺失 config 时新增 object config。
* 保留其它节点、connections 和 workflow 根字段。
* JSON 无效时返回 `JsonInvalid`。
* 缺失 `nodes[]` 时返回 `NodesMissing`。
* 找不到节点时返回 `NodeNotFound`。
* 现有 `node.config` 非 object 时返回 `NodeConfigNotObject`。
* 新 config 非 object 时返回 `ConfigUnsupported`。

本阶段明确未做：

* 不接 ViewModel。
* 不新增 Apply 命令。
* 不新增按钮或表单。
* 不修改 `WorkflowDefinitionDraftJson`。
* 不调用 Validate / Save / 后端 API。

验证结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "NodeConfigDraftJsonPatcherTests"
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
```

下一步建议：

```text
UI-NODE-CONFIG-2d.2：
先评估并最小接入 ApplySelectedNodeConfigDraftCommand，
只把当前 config draft 写回 WorkflowDefinitionDraftJson，
不做动态字段编辑控件。
```

### 2.96 UI-NODE-CONFIG-2d.2 Apply 命令接入评估

阶段目标：

```text
评估是否应立即接入 ApplySelectedNodeConfigDraftCommand，
避免在没有字段草稿输入模型时暴露语义不清的 Apply 按钮。
```

完成文档：

```text
docs/FlowWeaver_UI-NODE-CONFIG-2d.2_Apply命令接入评估.md
```

当前结论：

* 不建议现在直接接入 Apply 命令或按钮。
* 当前没有字段草稿输入模型，直接 Apply 只能原样重写当前 config，用户价值不足。
* Apply 前应先具备 editable draft、字段级校验、可编辑值到 JsonObject 的转换。
* `array`、`object`、`unsupported` 仍应走 JSON fallback。
* revision conflict 状态下 Apply 仍必须不可用或拒绝，不能清空冲突状态。

本阶段明确未做：

* 不改 Avalonia 代码。
* 不新增 Apply 命令。
* 不新增按钮或表单。
* 不写回 `WorkflowDefinitionDraftJson`。

建议下一步：

```text
UI-NODE-CONFIG-2e：
新增 NodeConfigEditableDraft 纯模型和测试，
只把 NodeConfigDraft 中可编辑字段转换为可输入草稿，
不接 XAML，不接 ViewModel Apply。
```

### 2.97 UI-NODE-CONFIG-2e NodeConfigEditableDraft 纯模型和测试

阶段目标：

```text
把只读 NodeConfigDraft 中可编辑字段转换为可输入草稿模型，
为后续字段编辑和 Apply 写回提供纯模型边界。
```

已完成：

* 新增 `NodeConfigEditableDraft`。
* 新增 `NodeConfigEditableDraftField`。
* 新增 `NodeConfigEditableDraftBuilder`。
* `NodeConfigDraftField` 补充 `EnumValues`。
* `NodeConfigDraftBuilder` 将 schema enum 候选值传入 draft field。
* 新增 `NodeConfigEditableDraftBuilderTests`。

当前能力：

* 仅从已支持的 `NodeConfigDraft` 构建可编辑草稿。
* 支持 `string`、`integer`、`number`、`boolean`、`enum` 字段。
* 字段输入值优先使用当前 config 值，缺失时使用 default。
* boolean 输入文本固定为 `true` / `false`。
* enum 字段保留完整候选值。
* `array`、`object`、`unsupported` 字段继续过滤，不进入可编辑字段集合。
* 字段级 warning 会保留到对应 editable field。
* 无可编辑字段时返回 `EDITABLE_DRAFT_NO_EDITABLE_FIELDS`。
* 不支持的 draft 只透传原 warnings，不生成字段。

本阶段明确未做：

* 不改 XAML。
* 不接 MainWindowViewModel。
* 不新增 Apply 命令。
* 不写回 `WorkflowDefinitionDraftJson`。
* 不改变 Save / Validate / revision conflict 行为。
* 不实现动态表单控件。

验证结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "NodeConfigEditableDraftBuilderTests|NodeConfigDraftBuilderTests"
通过：10，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：198，失败：0，跳过：0
```

建议下一步：

```text
UI-NODE-CONFIG-2f：
先评估并实现可编辑草稿到 JsonObject/config JSON 的纯转换模型，
只处理 string、integer、number、boolean、enum 的输入解析和错误状态，
仍不接 XAML，不接 MainWindowViewModel Apply。
```

### 2.98 UI-NODE-CONFIG-2f 可编辑草稿转 Config 纯模型

阶段目标：

```text
把 NodeConfigEditableDraft 转换为节点 config JSON object，
为后续 Apply 写回提供安全输入。
```

完成文档：

```text
docs/FlowWeaver_UI-NODE-CONFIG-2f_可编辑草稿转Config边界与验收清单.md
```

已完成：

* 新增 `NodeConfigEditableDraftConfigBuildStatus`。
* 新增 `NodeConfigEditableDraftConfigFieldError`。
* 新增 `NodeConfigEditableDraftConfigResult`。
* 新增 `NodeConfigEditableDraftConfigBuilder`。
* `NodeConfigEditableDraftField` 补充 `HasInputValue`，用于区分缺失字段和显式输入。
* `NodeConfigEditableDraftBuilder` 会根据当前 config/default 设置 `HasInputValue`。
* 新增 `NodeConfigEditableDraftConfigBuilderTests`。

当前能力：

* 支持 `string`、`integer`、`number`、`boolean`、`enum` 转 config JSON。
* 缺失的可选字段不会被静默写入 config。
* 显式空字符串可以保留。
* 必填空值、非法 integer/number/boolean/enum 会返回字段级错误。
* unsupported 类型会拒绝转换。
* 无可编辑字段会返回 `DraftUnsupported`。

本阶段明确未做：

* 不改 XAML。
* 不接 MainWindowViewModel。
* 不新增 Apply 命令。
* 不调用 `NodeConfigDraftJsonPatcher`。
* 不写回 `WorkflowDefinitionDraftJson`。
* 不改变 Validate / Save / revision conflict 行为。

验证结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "NodeConfigEditableDraftConfigBuilderTests|NodeConfigEditableDraftBuilderTests|NodeConfigDraftJsonPatcherTests"
通过：19，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：205，失败：0，跳过：0
```

建议下一步：

```text
UI-NODE-CONFIG-2g：
先分析 MainWindowViewModel 接入边界，
确认 SelectedNodeConfigEditableDraft、选中节点切换、草稿 JSON 变化、
schema 变化和后续 Apply 命令的最小状态来源。
```

### 2.99 UI-NODE-CONFIG-2g MainWindowViewModel 接入边界评估

阶段目标：

```text
在改 ViewModel 之前，
确认节点配置 editable draft 状态应如何接入 MainWindowViewModel。
```

完成文档：

```text
docs/FlowWeaver_UI-NODE-CONFIG-2g_MainWindowViewModel接入边界评估.md
```

当前结论：

* `SelectedNodeConfigDraftSummaryText` 当前是即时计算摘要，没有保存 draft 状态。
* 下一步应先接 `SelectedNodeConfigDraft` / `SelectedNodeConfigEditableDraft` 只读状态。
* 刷新触发点应复用 `WorkflowDefinitionDetail`、`SelectedWorkflowDefinitionNode`、`WorkflowDefinitionDraftJson` 和 node definitions 刷新完成后的现有通知。
* 2h 不接 XAML，不新增 Apply 命令，不写回 `WorkflowDefinitionDraftJson`。
* revision conflict 状态不能被刷新 editable draft 状态清空。

建议下一步：

```text
UI-NODE-CONFIG-2h：
在 MainWindowViewModel 内接入只读 SelectedNodeConfigDraft /
SelectedNodeConfigEditableDraft 状态和测试，
仍不接 Apply，不改 XAML。
```

### 2.100 UI-NODE-CONFIG-2h ViewModel 只读 EditableDraft 状态接入

阶段目标：

```text
将节点配置 draft / editable draft 作为 MainWindowViewModel 只读状态暴露，
为后续字段编辑和 Apply 接入提供稳定状态来源。
```

完成文档：

```text
docs/FlowWeaver_UI-NODE-CONFIG-2h_ViewModel只读EditableDraft状态接入.md
```

已完成：

* 新增 `SelectedNodeConfigDraft`。
* 新增 `SelectedNodeConfigEditableDraft`。
* 新增 `SelectedNodeConfigEditableDraftMessage`。
* 新增 `RefreshSelectedNodeConfigDraftState()`。
* `SelectedNodeConfigDraftSummaryText` 改为读取统一 message，保持原显示语义。
* 在 workflow detail、selected node、draft JSON、node definitions、语言切换等入口刷新状态。
* 补充 ViewModel 测试。

本阶段明确未做：

* 不改 XAML。
* 不新增 Apply 命令。
* 不调用 config builder / patcher。
* 不写回 `WorkflowDefinitionDraftJson`。
* 不改变 Validate / Save / revision conflict 行为。

验证结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "MainWindowViewModelWorkflowTests"
通过：39，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：206，失败：0，跳过：0
```

建议下一步：

```text
UI-NODE-CONFIG-2i：
先做最小可编辑输入状态边界评估，
确认用户修改字段值应该如何进入 ViewModel/model，
再决定是否接 ApplySelectedNodeConfigDraftCommand。
```

### 2.101 UI-NODE-CONFIG-2i 最小可编辑输入状态边界评估

阶段目标：

```text
确认 NodeConfigEditableDraft 是否可以直接作为用户输入状态，
以及 Apply 前还缺少哪一层状态。
```

完成文档：

```text
docs/FlowWeaver_UI-NODE-CONFIG-2i_最小可编辑输入状态边界评估.md
```

当前结论：

* `SelectedNodeConfigEditableDraft` 是从 workflow JSON + schema 派生的只读快照。
* 用户正在编辑但尚未 Apply 的输入值需要单独的可变状态。
* 不建议 UI 直接双向绑定 `NodeConfigEditableDraftField.InputValue`。
* 第一版刷新策略应先采用“选中节点、draft JSON、schema 变化即重建输入”的保守策略。
* Apply 仍应后置，不能跳过输入状态层。

建议下一步：

```text
UI-NODE-CONFIG-2j：
新增 NodeConfigEditableFieldInputViewModel 和输入字段集合状态，
只接 MainWindowViewModel 内部状态和测试，
不改 XAML，不接 Apply。
```

### 2.102 UI-NODE-CONFIG-2j 输入字段 ViewModel 状态接入

阶段目标：

```text
在只读 editable draft 快照之外，
新增用户可变输入字段状态。
```

完成文档：

```text
docs/FlowWeaver_UI-NODE-CONFIG-2j_输入字段ViewModel状态接入.md
```

已完成：

* 新增 `NodeConfigEditableFieldInputViewModel`。
* 新增 `SelectedNodeConfigEditableInputFields`。
* 新增 `HasSelectedNodeConfigEditableInputFields`。
* 输入字段支持 `InputValue`、`OriginalInputValue`、`HasInputValue`、`IsDirty`。
* 输入字段可转换回 `NodeConfigEditableDraftField`。
* `RefreshSelectedNodeConfigDraftState()` 会按当前 editable draft 重建输入字段集合。
* 补充输入字段和 MainWindowViewModel 测试。

本阶段明确未做：

* 不改 XAML。
* 不新增 Apply 命令。
* 不调用 config builder / patcher。
* 不写回 `WorkflowDefinitionDraftJson`。

验证结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "NodeConfigEditableFieldInputViewModelTests|MainWindowViewModelWorkflowTests"
通过：40，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：207，失败：0，跳过：0
```

建议下一步：

```text
UI-NODE-CONFIG-2k：
新增输入字段集合到 config JSON 的适配层，
复用 NodeConfigEditableDraftConfigBuilder，
仍不接 Apply。
```

### 2.103 UI-NODE-CONFIG-2k 输入字段集合转 Config 适配层

阶段目标：

```text
把 SelectedNodeConfigEditableInputFields 转换为 config JSON，
为 Apply 命令提供最后一个纯本地输入。
```

完成文档：

```text
docs/FlowWeaver_UI-NODE-CONFIG-2k_输入字段集合转Config适配层.md
```

已完成：

* 新增 `NodeConfigEditableFieldInputConfigBuilder`。
* 输入字段集合可转换为 `NodeConfigEditableDraft`。
* 复用 `NodeConfigEditableDraftConfigBuilder` 返回统一 config build result。
* 补充 `NodeConfigEditableFieldInputConfigBuilderTests`。

本阶段明确未做：

* 不改 XAML。
* 不新增 Apply 命令。
* 不调用 `NodeConfigDraftJsonPatcher`。
* 不写回 `WorkflowDefinitionDraftJson`。
* 不做字段错误回填到 UI。

验证结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "NodeConfigEditableFieldInputConfigBuilderTests|NodeConfigEditableFieldInputViewModelTests|NodeConfigEditableDraftConfigBuilderTests"
通过：11，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：210，失败：0，跳过：0
```

建议下一步：

```text
UI-NODE-CONFIG-2l：
ApplySelectedNodeConfigDraftCommand 最小接入，
只把输入字段集合生成的 config JSON 写回 WorkflowDefinitionDraftJson，
不改 XAML。
```

### 2.104 UI-NODE-CONFIG-2l ApplySelectedNodeConfigDraftCommand 最小接入

阶段目标：

```text
在 MainWindowViewModel 内接入 Apply 命令，
只把当前输入字段集合生成的 config JSON 写回 WorkflowDefinitionDraftJson。
```

完成文档：

```text
docs/FlowWeaver_UI-NODE-CONFIG-2l_Apply命令最小接入.md
```

已完成：

* 新增 `ApplySelectedNodeConfigDraftCommand`。
* 新增 `CanApplySelectedNodeConfigDraft`。
* Apply 成功时调用 input config builder 和 `NodeConfigDraftJsonPatcher`。
* Apply 成功后只设置 `WorkflowDefinitionDraftJson`，沿用现有 dirty / validation 链路。
* Apply 失败时保留原 JSON，并显示字段错误。
* revision conflict 状态下 Apply 不可用。
* 补充中英文最小本地化键。
* 补充 ViewModel 测试。

本阶段明确未做：

* 不改 XAML。
* 不新增可见按钮。
* 不做动态字段表单。
* 不调用后端 Validate / Save。
* 不清空 revision conflict。

验证结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "MainWindowViewModelWorkflowTests"
通过：42，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：213，失败：0，跳过：0
```

建议下一步：

```text
UI-NODE-CONFIG-2m：
整理节点配置字段表单和 Apply 按钮的 XAML 接入说明，
明确给 Gemini 的绑定对象、Command、控件类型和不可改边界。
```

### 2.105 UI-NODE-CONFIG-2m 节点配置表单 View 协作说明

阶段目标：

```text
在交给 Gemini 修改 XAML 前，
明确节点配置字段表单和 Apply 按钮的 View 接入边界。
```

完成文档：

```text
docs/FlowWeaver_UI-NODE-CONFIG-2m_节点配置表单View协作说明.md
```

当前结论：

* 第一小步建议只改 `WorkflowSummaryView.axaml`。
* 节点配置表单应放在 Nodes Card 底部。
* 绑定入口是 `SelectedNodeConfigEditableInputFields`。
* Apply 按钮绑定 `ApplySelectedNodeConfigDraftCommand`。
* 不改 `MainWindowViewModel.cs`、不写 code-behind、不改后端。
* 当前缺少 `IsEnum` / `IsBoolean` / `DisplayLabel` 等 View 友好辅助属性。

建议下一步：

```text
UI-NODE-CONFIG-2n：
为 NodeConfigEditableFieldInputViewModel 补充 View 友好辅助属性和测试，
再交给 Gemini 做 XAML 会更稳。
```

### 2.106 UI-NODE-CONFIG-2n 输入字段 View 辅助属性

阶段目标：

```text
为 NodeConfigEditableFieldInputViewModel 补充 XAML 友好属性，
减少后续 View 层对 converter / code-behind 的依赖。
```

完成文档：

```text
docs/FlowWeaver_UI-NODE-CONFIG-2n_输入字段View辅助属性.md
```

已完成：

* 新增 `DisplayLabel`。
* 新增 `TypeText` / `RequiredText`。
* 新增 `IsTextInput` / `IsEnumInput` / `IsBooleanInput`。
* 新增 `BooleanValues`。
* 新增 `HasWarnings` / `WarningText`。
* 补充输入字段 ViewModel 测试。

本阶段明确未做：

* 不改 XAML。
* 不新增 converter。
* 不新增 code-behind。
* 不改变 Apply / Validate / Save 语义。

验证结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "NodeConfigEditableFieldInputViewModelTests|NodeConfigEditableFieldInputConfigBuilderTests"
通过：5，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：214，失败：0，跳过：0
```

建议下一步：

```text
UI-NODE-CONFIG-2o：
WorkflowSummaryView.axaml 节点配置表单最小接入，
只改 View，绑定 SelectedNodeConfigEditableInputFields 和 ApplySelectedNodeConfigDraftCommand。
```

### 2.107 UI-NODE-CONFIG-2o WorkflowSummaryView 节点配置表单最小接入

阶段目标：

```text
将节点配置字段表单和 Apply 按钮接入 WorkflowSummaryView.axaml，
让当前 ViewModel 契约在 UI 中可见。
```

完成文档：

```text
docs/FlowWeaver_UI-NODE-CONFIG-2o_WorkflowSummaryView节点配置表单最小接入.md
```

已完成：

* Nodes Card 底部新增节点配置区域。
* 字段列表绑定 `SelectedNodeConfigEditableInputFields`。
* Apply 按钮绑定 `ApplySelectedNodeConfigDraftCommand`。
* string / integer / number 使用 `TextBox`。
* enum / boolean 使用 `ComboBox`。
* 新增 `NodeConfigSectionText` / `ApplyNodeConfigText` 和中英文资源。
* 补充 XAML 结构测试。

本阶段明确未做：

* 不改 `MainWindow.axaml`。
* 不改 `WorkflowPage.axaml` 三列结构。
* 不新增 converter / code-behind。
* 不改 Apply / Validate / Save 语义。

验证结果：

```text
dotnet build Avalonia_UI\Avalonia_UI.sln --no-restore
成功，警告：0，错误：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "WorkflowSummaryViewStructureTests|MainWindowViewModelWorkflowTests"
通过：45，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：215，失败：0，跳过：0
```

建议下一步：

```text
UI-NODE-CONFIG-2p：
节点配置表单后置复核，
重点检查布局高度、空状态、revision conflict 下 Apply 禁用、
以及真实 UI 中字段输入 + Apply + Draft JSON 的最小链路。
```

### 2.108 UI-NODE-CONFIG-2p 节点配置表单后置复核

阶段目标：

```text
复核节点配置表单最小接入后的 XAML 绑定、Apply 可用性和测试证据。
```

完成文档：

```text
docs/FlowWeaver_UI-NODE-CONFIG-2p_节点配置表单后置复核.md
```

已完成：

* schema 未加载时 Apply 不可用的 ViewModel 测试。
* schema 加载后 Apply 可用的 ViewModel 测试。
* XAML 绑定 `DisplayLabel` / `TypeText` / `RequiredText` / `WarningText` 的结构测试。
* XAML 绑定 `IsTextInput` / `IsEnumInput` / `IsBooleanInput` / `BooleanValues` 的结构测试。
* 确认 XAML 未引入 converter。

验证结果：

```text
dotnet build Avalonia_UI\Avalonia_UI.sln --no-restore
成功，警告：0，错误：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "WorkflowSummaryViewStructureTests|MainWindowViewModelWorkflowTests"
通过：46，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：216，失败：0，跳过：0
```

保留项：

* 未做真实桌面截图核验。
* 未做字段级错误高质量可视化回填。
* 未做 array / object JSON fallback 编辑器。

建议下一步：

```text
UI-NODE-CONFIG-2q：
节点配置阶段总体验收与进入 WORKFLOW-EDIT 前复核。
```

### 2.109 UI-NODE-CONFIG-2q 节点配置阶段总体验收与 WORKFLOW-EDIT 前复核

阶段目标：

```text
对 UI-NODE-CONFIG-2 主线做完成矩阵复核，
并明确它和后续 WORKFLOW-EDIT-1/2 的边界。
```

完成文档：

```text
docs/FlowWeaver_UI-NODE-CONFIG-2q_阶段总体验收与WORKFLOW-EDIT前复核.md
```

当前结论：

* 节点配置主线已形成 schema → input fields → Apply → `WorkflowDefinitionDraftJson` 的最小闭环。
* 当前能力只覆盖已有节点实例的 config 编辑。
* 完整 workflow 结构编辑仍未开始，不能把节点 config Apply 等同于 WORKFLOW-EDIT 完成。
* 建议进入 WORKFLOW-EDIT，但先只做前置边界分析。

建议下一步：

```text
WORKFLOW-EDIT-1.0：
工作流结构化编辑前置边界分析，
先列清 nodes / connections / draft JSON / revision conflict 的边界，
不直接实现节点增删或连线编辑。
```

### 2.110 WORKFLOW-EDIT-1.0 工作流结构化编辑前置边界分析

阶段目标：

```text
在节点配置主线收口后，
先明确完整 workflow definition 结构化编辑的最小边界，
避免把已有 node config Apply 误扩展成完整 Workflow 编辑器。
```

完成文档：

```text
docs/FlowWeaver_WORKFLOW-EDIT-1.0_工作流结构化编辑前置边界分析.md
```

当前结论：

* `WorkflowDefinitionDraftJson` 继续作为唯一保存源。
* 结构化编辑必须复用现有 dirty、validation invalidation、Save 和 revision conflict 语义。
* 当前 `WorkflowDefinitionDetail.Nodes` / `Connections` 是已加载 definition 的只读投影，不等同于可编辑草稿结构。
* WORKFLOW-EDIT-1 先做结构化 JSON 草稿模型和纯 patcher，不引入画布、拖拽、后端 partial patch API。
* WORKFLOW-EDIT-2 再考虑图形化体验、节点专用编辑器、复杂 config 表单、撤销/重做等能力。

建议下一步：

```text
WORKFLOW-EDIT-1.1：
建立 WorkflowDefinitionDraftStructure 只读解析模型和测试，
只解析当前 WorkflowDefinitionDraftJson 中的 nodes / connections，
不修改 ViewModel，不修改 XAML，不新增结构化写入命令。
```

### 2.111 WORKFLOW-EDIT-1.1 WorkflowDefinitionDraftStructure 只读解析模型

阶段目标：

```text
先从 WorkflowDefinitionDraftJson 中建立只读草稿结构，
把“用户正在编辑的 draft”与“已加载 workflow detail”区分开。
```

完成文件：

```text
Avalonia_UI/Models/WorkflowDefinitionDraftStructure.cs
Avalonia_UI/Models/WorkflowDefinitionDraftStructureStatus.cs
Avalonia_UI/Models/WorkflowDefinitionDraftNode.cs
Avalonia_UI/Models/WorkflowDefinitionDraftConnection.cs
Avalonia_UI/Models/WorkflowDefinitionDraftStructureBuilder.cs
Avalonia_UI.Tests/WorkflowDefinitionDraftStructureBuilderTests.cs
docs/FlowWeaver_WORKFLOW-EDIT-1.1_WorkflowDefinitionDraftStructure只读解析模型.md
```

当前结论：

* 新增模型只读取 draft JSON，不写回、不 patch、不触发保存。
* 根结构错误会让结构不可用，单个坏节点/坏连线只记录 warning 并跳过。
* 已覆盖 JSON invalid、root not object、nodes/connections missing、坏节点/坏连线跳过等测试。
* 完整 Avalonia 测试通过。

验证结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "WorkflowDefinitionDraftStructureBuilderTests"
通过：6，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：222，失败：0，跳过：0
```

建议下一步：

```text
WORKFLOW-EDIT-1.2：
接入 ViewModel 只读草稿结构状态，
从 WorkflowDefinitionDraftJson 派生 draft nodes / draft connections，
不新增写入命令，不修改 XAML。
```

### 2.112 WORKFLOW-EDIT-1.2 ViewModel 只读草稿结构状态接入

阶段目标：

```text
把 WorkflowDefinitionDraftStructure 接入 MainWindowViewModel，
使 UI 层后续可读取“当前 draft”的节点和连线摘要，
但暂不展示、不写回、不新增结构化编辑命令。
```

完成文件：

```text
Avalonia_UI/ViewModels/MainWindowViewModel.cs
Avalonia_UI.Tests/MainWindowViewModelWorkflowTests.cs
docs/FlowWeaver_WORKFLOW-EDIT-1.2_ViewModel只读草稿结构状态接入.md
```

当前结论：

* `WorkflowDefinitionDraftStructure` 现在随 `WorkflowDefinitionDraftJson` 变化自动重建。
* 新增派生状态可读取 draft node / connection 数量和 warning 状态。
* 切换 workflow 或清空 draft 时会清空 draft structure。
* 没有修改 Validate / Save / Apply / revision conflict 语义。
* 没有修改 XAML。

验证结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "MainWindowViewModelWorkflowTests"
通过：43，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：223，失败：0，跳过：0
```

建议下一步：

```text
WORKFLOW-EDIT-1.3：
节点新增纯 patcher 前置实现，
只新增模型和测试，不接 ViewModel 命令，不修改 XAML。
```

### 2.113 WORKFLOW-EDIT-1.3 节点新增纯 patcher

阶段目标：

```text
先建立新增节点的纯 JSON patch 能力，
为后续 ViewModel 命令和 UI 输入提供可测试的底层边界。
```

完成文件：

```text
Avalonia_UI/Models/WorkflowDefinitionDraftNodePatcher.cs
Avalonia_UI/Models/WorkflowDefinitionDraftNodePatchResult.cs
Avalonia_UI/Models/WorkflowDefinitionDraftNodePatchStatus.cs
Avalonia_UI.Tests/WorkflowDefinitionDraftNodePatcherTests.cs
docs/FlowWeaver_WORKFLOW-EDIT-1.3_节点新增纯Patcher.md
```

当前结论：

* `AddNode` 会 append 新节点，并保留 root 其他字段和现有 `connections`。
* 已校验根对象、nodes/connections 数组、必填身份字段、重复 node_instance_id、config object 边界。
* 本小步没有接 ViewModel 命令，也没有修改 XAML。
* 完整 Avalonia 测试通过。

验证结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "WorkflowDefinitionDraftNodePatcherTests"
通过：9，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：232，失败：0，跳过：0
```

建议下一步：

```text
WORKFLOW-EDIT-1.4：
节点删除 preflight / patcher，
先识别连接依赖，默认不做级联删除，
不接 ViewModel 命令，不修改 XAML。
```

### 2.114 WORKFLOW-EDIT-1.4 节点删除 preflight / patcher

阶段目标：

```text
建立删除节点的纯 JSON patch 能力，
并先通过 preflight 阻断仍被 connection 引用的节点。
```

完成文件：

```text
Avalonia_UI/Models/WorkflowDefinitionDraftNodePatcher.cs
Avalonia_UI/Models/WorkflowDefinitionDraftNodePatchStatus.cs
Avalonia_UI.Tests/WorkflowDefinitionDraftNodePatcherTests.cs
docs/FlowWeaver_WORKFLOW-EDIT-1.4_节点删除Preflight与Patcher.md
```

当前结论：

* `DeleteNode` 只删除无连接依赖的节点。
* 存在 incoming/outgoing connection 时返回 `NODE_HAS_CONNECTIONS`。
* 第一版明确不做默认级联删除。
* 本小步没有接 ViewModel 命令，也没有修改 XAML。
* 完整 Avalonia 测试通过。

验证结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "WorkflowDefinitionDraftNodePatcherTests"
通过：14，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：237，失败：0，跳过：0
```

建议下一步：

```text
WORKFLOW-EDIT-1.5：
connection 新增 / 删除纯 patcher，
只新增模型和测试，不接 ViewModel 命令，不修改 XAML。
```

### 2.115 WORKFLOW-EDIT-1.5 connection 新增 / 删除纯 patcher

阶段目标：

```text
建立 connection 新增和删除的纯 JSON patch 能力，
为后续 ViewModel 命令接入提供可测试底层。
```

完成文件：

```text
Avalonia_UI/Models/WorkflowDefinitionDraftConnectionPatcher.cs
Avalonia_UI/Models/WorkflowDefinitionDraftConnectionPatchResult.cs
Avalonia_UI/Models/WorkflowDefinitionDraftConnectionPatchStatus.cs
Avalonia_UI.Tests/WorkflowDefinitionDraftConnectionPatcherTests.cs
docs/FlowWeaver_WORKFLOW-EDIT-1.5_Connection新增删除纯Patcher.md
```

当前结论：

* `AddConnection` 会校验 connection_id 不重复、source / target node 存在、端口非空。
* `DeleteConnection` 会校验目标 connection 存在。
* 第一版不做端口 schema 深校验。
* 本小步没有接 ViewModel 命令，也没有修改 XAML。
* 完整 Avalonia 测试通过。

验证结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "WorkflowDefinitionDraftConnectionPatcherTests"
通过：8，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：245，失败：0，跳过：0
```

建议下一步：

```text
WORKFLOW-EDIT-1.6：
结构化编辑 ViewModel 命令接入前置分析，
先只分析命令、输入状态和错误消息边界。
```

### 2.116 WORKFLOW-EDIT-1.6 ViewModel 命令接入前置分析

阶段目标：

```text
在已有纯 patcher 之后，
先明确 ViewModel 命令接入顺序、输入状态和错误消息边界，
避免一次性接入节点增删和 connection 增删。
```

完成文档：

```text
docs/FlowWeaver_WORKFLOW-EDIT-1.6_ViewModel命令接入前置分析.md
```

当前结论：

* 结构化命令必须只写回 `WorkflowDefinitionDraftJson`。
* dirty、validation invalidation、Save 和 revision conflict 继续复用现有语义。
* 不建议一次性接入 AddNode / DeleteNode / AddConnection / DeleteConnection。
* 建议先补节点新增输入状态，再接 AddNode 命令。
* XAML 和 Gemini View 协作继续后置。

建议下一步：

```text
WORKFLOW-EDIT-1.6a：
节点新增输入状态最小接入，
只新增 ViewModel 属性和测试，
不调用 patcher，不修改 WorkflowDefinitionDraftJson，不修改 XAML。
```

### 2.117 WORKFLOW-EDIT-1.6a 节点新增输入状态最小接入

阶段目标：

```text
先在 ViewModel 中建立节点新增输入状态，
为 AddNode 命令接入提供可测试输入边界。
```

完成文件：

```text
Avalonia_UI/ViewModels/MainWindowViewModel.cs
Avalonia_UI.Tests/MainWindowViewModelWorkflowTests.cs
docs/FlowWeaver_WORKFLOW-EDIT-1.6a_节点新增输入状态最小接入.md
```

当前结论：

* 新增了 `NewDraftNodeInstanceId` / `NewDraftNodeType` / `NewDraftNodeVersion` / `NewDraftNodeDisplayName` / `NewDraftNodeConfigJson`。
* 默认 version 为 `1.0`，默认 config JSON 为 `{}`。
* 加载或切换 workflow definition 时会重置输入。
* 本小步没有调用 patcher，没有修改 draft JSON，没有修改 XAML。
* 完整 Avalonia 测试通过。

验证结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "MainWindowViewModelWorkflowTests"
通过：44，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：246，失败：0，跳过：0
```

建议下一步：

```text
WORKFLOW-EDIT-1.6b：
AddNode 命令最小接入，
成功后只写回 WorkflowDefinitionDraftJson，
不修改 XAML。
```

### 2.118 WORKFLOW-EDIT-1.6b AddNode 命令最小接入

阶段目标：

```text
将节点新增纯 patcher 接入 MainWindowViewModel 命令，
成功后只写回 WorkflowDefinitionDraftJson。
```

完成文件：

```text
Avalonia_UI/ViewModels/MainWindowViewModel.cs
Avalonia_UI.Tests/MainWindowViewModelWorkflowTests.cs
Avalonia_UI/Localization/en-US.json
Avalonia_UI/Localization/zh-Hans.json
docs/FlowWeaver_WORKFLOW-EDIT-1.6b_AddNode命令最小接入.md
```

当前结论：

* 新增 `AddWorkflowDefinitionDraftNodeCommand`。
* 命令成功后写回 draft JSON，并复用 dirty / validation invalidation / draft structure 刷新。
* 命令失败不清空用户输入。
* revision conflict、busy、未加载 definition、输入为空时命令不可用。
* 本小步没有修改 XAML。
* 完整 Avalonia 测试通过。

验证结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "MainWindowViewModelWorkflowTests"
通过：47，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：249，失败：0，跳过：0
```

建议下一步：

```text
WORKFLOW-EDIT-1.6c：
DeleteNode 命令前置状态，
先新增 draft node 选择/输入状态，不调用 delete patcher，不修改 XAML。
```

### 2.119 WORKFLOW-EDIT-1.6c DeleteNode 命令前置状态

阶段目标：

```text
新增 draft node 选择状态，
为后续 DeleteNode 命令提供明确输入，
避免混用 loaded detail node selection。
```

完成文件：

```text
Avalonia_UI/ViewModels/MainWindowViewModel.cs
Avalonia_UI.Tests/MainWindowViewModelWorkflowTests.cs
docs/FlowWeaver_WORKFLOW-EDIT-1.6c_DeleteNode命令前置状态.md
```

当前结论：

* 新增 `SelectedWorkflowDefinitionDraftNodeInstanceId`。
* 加载或切换 workflow definition 时会重置选择状态。
* draft JSON 变化后，如果所选节点不再存在，会自动清空选择状态。
* 本小步没有调用 delete patcher，没有修改 draft JSON，没有修改 XAML。
* 完整 Avalonia 测试通过。

验证结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "MainWindowViewModelWorkflowTests"
通过：48，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：250，失败：0，跳过：0
```

建议下一步：

```text
WORKFLOW-EDIT-1.6d：
DeleteNode 命令最小接入，
成功后只写回 WorkflowDefinitionDraftJson，
不做级联删除，不修改 XAML。
```

### 2.120 WORKFLOW-EDIT-1.6d DeleteNode 命令最小接入

阶段目标：

```text
将节点删除纯 patcher 接入 MainWindowViewModel 命令，
成功后只写回 WorkflowDefinitionDraftJson，
并继续阻断存在 connection 依赖的节点删除。
```

完成文件：

```text
Avalonia_UI/ViewModels/MainWindowViewModel.cs
Avalonia_UI.Tests/MainWindowViewModelWorkflowTests.cs
Avalonia_UI/Localization/en-US.json
Avalonia_UI/Localization/zh-Hans.json
docs/FlowWeaver_WORKFLOW-EDIT-1.6d_DeleteNode命令最小接入.md
```

当前结论：

* 新增 `DeleteWorkflowDefinitionDraftNodeCommand`。
* 命令成功后写回 draft JSON，并复用 dirty / validation invalidation / draft structure 刷新。
* 命令失败不清空选择状态。
* `NODE_HAS_CONNECTIONS` 只显示错误，不做级联删除。
* revision conflict、busy、未加载 definition、未选择 draft node 时命令不可用。
* 本小步没有修改 XAML。
* 完整 Avalonia 测试通过。

验证结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "MainWindowViewModelWorkflowTests"
通过：50，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：252，失败：0，跳过：0
```

建议下一步：

```text
WORKFLOW-EDIT-1.6e：
connection 命令接入前置状态，
只新增输入/选择状态，不调用 connection patcher，不修改 XAML。
```

### 2.121 WORKFLOW-EDIT-1.6e connection 命令接入前置状态

阶段目标：

```text
新增 connection 新增输入和删除选择状态，
为 AddConnection / DeleteConnection 命令提供明确输入边界。
```

完成文件：

```text
Avalonia_UI/ViewModels/MainWindowViewModel.cs
Avalonia_UI.Tests/MainWindowViewModelWorkflowTests.cs
docs/FlowWeaver_WORKFLOW-EDIT-1.6e_Connection命令前置状态.md
```

当前结论：

* 新增 connection 新增输入状态。
* 新增 `SelectedWorkflowDefinitionDraftConnectionId`。
* 加载或切换 workflow definition 时会重置 connection 输入和选择状态。
* draft JSON 变化后，如果所选 connection 不再存在，会自动清空选择状态。
* 本小步没有调用 connection patcher，没有修改 draft JSON，没有修改 XAML。
* 完整 Avalonia 测试通过。

验证结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "MainWindowViewModelWorkflowTests"
通过：51，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：253，失败：0，跳过：0
```

建议下一步：

```text
WORKFLOW-EDIT-1.6f：
AddConnection / DeleteConnection 命令最小接入，
成功后只写回 WorkflowDefinitionDraftJson，
不修改 XAML。
```

### 2.122 WORKFLOW-EDIT-1.6f AddConnection / DeleteConnection 命令最小接入

阶段目标：

```text
将 connection 新增 / 删除纯 patcher 接入 MainWindowViewModel 命令，
成功后只写回 WorkflowDefinitionDraftJson。
```

完成文件：

```text
Avalonia_UI/ViewModels/MainWindowViewModel.cs
Avalonia_UI.Tests/MainWindowViewModelWorkflowTests.cs
Avalonia_UI/Localization/en-US.json
Avalonia_UI/Localization/zh-Hans.json
docs/FlowWeaver_WORKFLOW-EDIT-1.6f_Connection命令最小接入.md
```

当前结论：

* 新增 `AddWorkflowDefinitionDraftConnectionCommand`。
* 新增 `DeleteWorkflowDefinitionDraftConnectionCommand`。
* 命令成功后写回 draft JSON，并复用 dirty / validation invalidation / draft structure 刷新。
* 命令失败不清空用户输入或选择。
* revision conflict、busy、未加载 definition、输入为空时命令不可用。
* 本小步没有修改 XAML。
* 完整 Avalonia 测试通过。

验证结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "MainWindowViewModelWorkflowTests"
通过：54，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：256，失败：0，跳过：0
```

建议下一步：

```text
WORKFLOW-EDIT-1.6g：
结构化编辑命令后置复核，
先文档化完成矩阵和下一步 View 协作边界。
```

### 2.123 WORKFLOW-EDIT-1.6g 结构化编辑命令后置复核

阶段目标：

```text
复核 WORKFLOW-EDIT-1.0 到 1.6f 的结构化编辑命令闭环，
明确是否可以进入 View 协作说明。
```

完成文档：

```text
docs/FlowWeaver_WORKFLOW-EDIT-1.6g_结构化编辑命令后置复核.md
```

当前结论：

* AddNode / DeleteNode / AddConnection / DeleteConnection 的 ViewModel 命令最小闭环已完成。
* 成功后统一写回 `WorkflowDefinitionDraftJson`。
* 已复用 dirty、validation invalidation、draft structure refresh、revision conflict 和 busy guard。
* XAML 输入区、按钮和画布都尚未实现。
* 下一步建议先写 Gemini View 协作说明，而不是继续扩展命令逻辑。

建议下一步：

```text
WORKFLOW-EDIT-1.7：
结构化编辑 View 协作说明，
只写 Gemini 可执行说明，不直接改 XAML。
```

### 2.124 WORKFLOW-EDIT-1.7 结构化编辑 View 协作说明

阶段目标：

```text
整理结构化编辑命令进入 View 前的 Gemini 协作边界，
并确认是否存在必须由 Codex 先补齐的 ViewModel/L10N 前置项。
```

完成文档：

```text
docs/FlowWeaver_WORKFLOW-EDIT-1.7_结构化编辑View协作说明.md
```

当前结论：

* ViewModel 已提供节点/连接增删命令和输入状态。
* 但新增表单区缺少本地化显示文本属性。
* 不建议 Gemini 直接写死英文或中文文本。
* 下一步建议先由 Codex 做 `WORKFLOW-EDIT-1.7a`，补结构化编辑 View 辅助文本属性。
* 1.7a 完成后，再让 Gemini 只改 `WorkflowSummaryView.axaml`。

建议下一步：

```text
WORKFLOW-EDIT-1.7a：
结构化编辑 View 辅助文本属性，
只补 Localization 和 MainWindowViewModel 文本属性，
不修改 XAML。
```

### 2.125 WORKFLOW-EDIT-1.7a 结构化编辑 View 辅助文本属性

阶段目标：

```text
补齐结构化编辑表单进入 XAML 前所需的本地化文本属性，
避免 Gemini 后续在 View 中写死英文或中文。
```

完成文件：

```text
Avalonia_UI/ViewModels/MainWindowViewModel.cs
Avalonia_UI/Localization/en-US.json
Avalonia_UI/Localization/zh-Hans.json
Avalonia_UI.Tests/MainWindowViewModelLocalizationTests.cs
docs/FlowWeaver_WORKFLOW-EDIT-1.7a_结构化编辑View辅助文本属性.md
```

当前结论：

* 已新增节点/连接结构化编辑表单所需文本属性。
* 已补英文和简体中文资源。
* 已接入语言切换通知。
* 本小步没有修改 XAML。
* 完整 Avalonia 测试通过。

验证结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "MainWindowViewModelLocalizationTests|JsonLocalizationServiceTests"
通过：28，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：256，失败：0，跳过：0
```

建议下一步：

```text
WORKFLOW-EDIT-1.7b：
结构化编辑 Gemini View 修改任务说明，
只写协作文档，不直接改 XAML。
```

### 2.126 WORKFLOW-EDIT-1.7b Gemini 结构化编辑 View 修改任务说明

阶段目标：

```text
整理给 Gemini 的纯 View 修改任务说明，
明确可用绑定、允许修改文件和禁止范围。
```

完成文档：

```text
docs/FlowWeaver_WORKFLOW-EDIT-1.7b_Gemini结构化编辑View修改任务说明.md
```

当前结论：

* Gemini 后续只应修改 `WorkflowSummaryView.axaml`。
* 第一版只做节点/连接结构化编辑表单，不做画布。
* 必须使用 1.7a 新增的本地化文本属性。
* 不允许 Gemini 修改 ViewModel、模型、本地化资源、测试或后端。
* 不允许引入 converters 或 code-behind。

建议下一步：

```text
WORKFLOW-EDIT-1.7c：
WorkflowSummaryView 结构化编辑表单纯 View 接入。
```

### 2.127 WORKFLOW-EDIT-1.7c WorkflowSummaryView 结构化编辑表单纯 View 接入

阶段目标：

```text
将结构化编辑命令以紧凑表单方式接入 WorkflowSummaryView，
只改 XAML 和结构测试。
```

完成文件：

```text
Avalonia_UI/Views/Components/Workflow/WorkflowSummaryView.axaml
Avalonia_UI.Tests/WorkflowSummaryViewStructureTests.cs
docs/FlowWeaver_WORKFLOW-EDIT-1.7c_WorkflowSummaryView结构化编辑表单接入.md
```

当前结论：

* Nodes Card 已增加节点新增/删除表单。
* Connections Card 已增加 connection 新增/删除表单。
* 表单绑定现有输入状态、文本属性和命令。
* 没有新增 converter 或 code-behind。
* 没有修改 ViewModel、模型、本地化资源或后端。
* 完整 Avalonia 测试通过。

验证结果：

```text
dotnet build Avalonia_UI\Avalonia_UI.sln --no-restore
成功，警告：0，错误：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "WorkflowSummaryViewStructureTests|MainWindowViewModelWorkflowTests|MainWindowViewModelLocalizationTests"
通过：81，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：257，失败：0，跳过：0
```

建议下一步：

```text
WORKFLOW-EDIT-1.7d：
结构化编辑 View 后置复核。
```

### 2.128 WORKFLOW-EDIT-1.7d 结构化编辑 View 后置复核

阶段目标：

```text
对结构化编辑 View 接入做后置复核，
确认是否可以进入 WORKFLOW-EDIT-1 阶段总体验收。
```

完成文档：

```text
docs/FlowWeaver_WORKFLOW-EDIT-1.7d_结构化编辑View后置复核.md
```

当前结论：

* `WorkflowSummaryView` 已完成结构化编辑最小表单接入。
* 已保持无 converter、无 code-behind、无 ViewModel/模型/后端改动。
* 完整 Avalonia 测试通过。
* 下一步建议进入 WORKFLOW-EDIT-1 阶段总体验收复核。

建议下一步：

```text
WORKFLOW-EDIT-1.8：
WORKFLOW-EDIT-1 阶段总体验收复核。
```

### 2.129 WORKFLOW-EDIT-1.8 阶段总体验收复核

阶段目标：

```text
对 WORKFLOW-EDIT-1 从 1.0 到 1.7d 做总体验收，
确认结构化编辑第一阶段已经完成，
并明确进入 WORKFLOW-EDIT-2 前的剩余缺口。
```

完成文档：

```text
docs/FlowWeaver_WORKFLOW-EDIT-1.8_阶段总体验收复核.md
```

当前结论：

* `WorkflowDefinitionDraftJson` 仍是唯一保存源。
* 只读草稿结构、节点 patcher、connection patcher、ViewModel 命令、View 表单接入已经形成最小闭环。
* 已复用 dirty、validation invalidation、busy guard、revision conflict 等既有边界。
* 第一阶段仍不包含用户友好 warning 映射、下拉选择、端口 schema 深校验、自动 ID、图形画布和桌面真实 smoke。

建议下一步：

```text
WORKFLOW-EDIT-2.0：
结构化编辑可用性缺口边界分析。
```

### 2.130 WORKFLOW-EDIT-2.0 结构化编辑可用性缺口边界分析

阶段目标：

```text
在进入 WORKFLOW-EDIT-2 代码前，
明确哪些可用性缺口可以先由 UI 侧收口，
哪些必须等待后端 schema/API 契约。
```

完成文档：

```text
docs/FlowWeaver_WORKFLOW-EDIT-2.0_结构化编辑可用性缺口边界分析.md
```

当前结论：

* WORKFLOW-EDIT-2 不应直接扩大为图形化编辑器。
* 可以先做用户友好 warning / error 映射。
* node type 选择可以基于已有节点定义只读数据逐步增强。
* source / target 选择可以基于当前 draft nodes 逐步增强。
* port 下拉和端口深校验需要等待更明确的 schema 契约。

建议下一步：

```text
WORKFLOW-EDIT-2.1：
用户友好 warning / error 映射。
```

### 2.131 WORKFLOW-EDIT-2.1 用户友好 warning / error 映射

阶段目标：

```text
将结构化编辑命令失败时展示的内部 warning code，
转换为用户可读文案。
```

完成文档：

```text
docs/FlowWeaver_WORKFLOW-EDIT-2.1_用户友好WarningError映射.md
```

当前结论：

* patcher 返回码保持不变。
* ViewModel 展示层新增 warning code 到本地化文案映射。
* AddNode、DeleteNode、AddConnection、DeleteConnection 失败分支已接入映射。
* 未知 warning code 继续回退原始 code。
* 中英文本地化资源已补齐。

验证结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "MainWindowViewModelWorkflowTests|JsonLocalizationServiceTests"
通过：61，失败：0，跳过：0

dotnet build Avalonia_UI\Avalonia_UI.sln --no-restore
成功，警告：0，错误：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：258，失败：0，跳过：0
```

建议下一步：

```text
WORKFLOW-EDIT-2.2：
node type 与 node instance id 输入体验收口。
```

### 2.132 WORKFLOW-EDIT-2.2a node type 与 node instance id 输入体验前置分析

阶段目标：

```text
明确新增节点表单如何复用现有 node catalog，
并在不破坏手动输入降级能力的前提下，
为 node type 选择和 node instance id 自动建议做前置设计。
```

完成文档：

```text
docs/FlowWeaver_WORKFLOW-EDIT-2.2a_NodeType与NodeInstanceId输入体验前置分析.md
```

当前结论：

* 2.2 应复用 `NodeDefinitions` 和 `NodeDefinitionListItemViewModel`。
* ViewModel 可先新增 `SelectedNewDraftNodeDefinition` 状态。
* 选择节点定义时填充 `NewDraftNodeType` / `NewDraftNodeVersion` / `NewDraftNodeDisplayName`。
* `NewDraftNodeInstanceId` 可以基于 `NodeType` 自动建议，并避开当前 draft nodes。
* node catalog 未加载、为空或失败时，必须保留手动输入降级能力。

建议下一步：

```text
WORKFLOW-EDIT-2.2b：
SelectedNewDraftNodeDefinition 与 node instance id 自动建议 ViewModel 状态。
```

### 2.133 WORKFLOW-EDIT-2.2b SelectedNewDraftNodeDefinition 与自动建议 ID

阶段目标：

```text
先在 ViewModel 层接通 node catalog 到新增节点输入的状态桥，
为后续 View 接入 ComboBox / 手动输入降级做准备。
```

完成文档：

```text
docs/FlowWeaver_WORKFLOW-EDIT-2.2b_SelectedNewDraftNodeDefinition与自动建议ID.md
```

当前结论：

* 已新增 `SelectedNewDraftNodeDefinition`。
* 选择节点定义会填充 `NewDraftNodeType` / `NewDraftNodeVersion` / `NewDraftNodeDisplayName`。
* 会基于 node type 自动建议不重复的 `NewDraftNodeInstanceId`。
* 用户手动填写的 `NewDraftNodeInstanceId` 不会被覆盖。
* 本小步未修改 XAML。

验证结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "MainWindowViewModelWorkflowTests"
通过：58，失败：0，跳过：0

dotnet build Avalonia_UI\Avalonia_UI.sln --no-restore
成功，警告：0，错误：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：261，失败：0，跳过：0
```

建议下一步：

```text
WORKFLOW-EDIT-2.2c：
新增节点 View 接入前置复核 / Gemini 任务说明。
```

### 2.134 WORKFLOW-EDIT-2.2c 新增节点 View 接入任务说明

阶段目标：

```text
为 WorkflowSummaryView 的新增节点表单接入 node catalog 选择入口，
明确纯 View 修改范围和测试要求。
```

完成文档：

```text
docs/FlowWeaver_WORKFLOW-EDIT-2.2c_新增节点View接入任务说明.md
```

当前结论：

* View 接入应绑定 `NodeDefinitions` 与 `SelectedNewDraftNodeDefinition`。
* ComboBox 只是辅助选择，必须保留 `NewDraftNodeType` 手动输入。
* 必须保留 `NewDraftNodeInstanceId` 手动输入。
* 不允许新增 converter、code-behind 或后端改动。
* 结构测试应覆盖 ComboBox 绑定和原手动输入仍存在。

建议下一步：

```text
WORKFLOW-EDIT-2.2d：
新增节点 View 最小接入。
```

### 2.135 WORKFLOW-EDIT-2.2d 新增节点 View 最小接入

阶段目标：

```text
在 WorkflowSummaryView 的新增节点表单中接入 node catalog ComboBox，
并保留 node type 手动输入降级能力。
```

完成文档：

```text
docs/FlowWeaver_WORKFLOW-EDIT-2.2d_新增节点View最小接入.md
```

当前结论：

* 新增节点表单已接入 `NodeDefinitions` ComboBox。
* ComboBox `SelectedItem` 绑定 `SelectedNewDraftNodeDefinition`。
* item template 展示 `DisplayNameText` 和 `TypeText`。
* `NewDraftNodeType` 手动输入仍保留。
* 未新增 converter、code-behind 或后端改动。

验证结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "WorkflowSummaryViewStructureTests|MainWindowViewModelWorkflowTests"
通过：63，失败：0，跳过：0

dotnet build Avalonia_UI\Avalonia_UI.sln --no-restore
成功，警告：0，错误：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：261，失败：0，跳过：0
```

建议下一步：

```text
WORKFLOW-EDIT-2.2e：
node type 与 node instance id 输入体验后置复核。
```

### 2.136 WORKFLOW-EDIT-2.2e node type 与 node instance id 输入体验后置复核

阶段目标：

```text
复核 WORKFLOW-EDIT-2.2 是否完成 node type 选择、
node instance id 自动建议和手动输入降级边界。
```

完成文档：

```text
docs/FlowWeaver_WORKFLOW-EDIT-2.2e_NodeType与NodeInstanceId输入体验后置复核.md
```

当前结论：

* `SelectedNewDraftNodeDefinition` 已接入 ViewModel。
* 选择 node definition 会填充 node type / version / display name。
* node instance id 会自动建议并避开重复。
* 用户手动 node instance id 不会被覆盖。
* `WorkflowSummaryView` 已接入 node catalog ComboBox。
* `NewDraftNodeType` 和 `NewDraftNodeInstanceId` 手动输入仍保留。

验证结果：

```text
dotnet build Avalonia_UI\Avalonia_UI.sln --no-restore
成功，警告：0，错误：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：261，失败：0，跳过：0
```

建议下一步：

```text
WORKFLOW-EDIT-2.3a：
connection source / target / id 输入体验前置分析。
```

### 2.137 WORKFLOW-EDIT-2.3a connection source / target / id 输入体验前置分析

阶段目标：

```text
明确 connection 新增表单如何复用当前 draft nodes，
并在不引入 port schema 深校验的前提下，
为 source / target 选择和 connection id 自动建议做前置设计。
```

完成文档：

```text
docs/FlowWeaver_WORKFLOW-EDIT-2.3a_Connection输入体验前置分析.md
```

当前结论：

* 2.3 应复用 `WorkflowDefinitionDraftStructure` 中的 draft nodes。
* ViewModel 可先新增 source / target 选择状态。
* 选择 source / target 时填充现有 connection 输入字段。
* connection id 可基于 `source_to_target` 自动建议，并避开重复。
* source / target port 继续保持手动输入，不做 schema 深校验。

建议下一步：

```text
WORKFLOW-EDIT-2.3b：
connection source / target 选择状态与 connection id 自动建议。
```

### 2.138 WORKFLOW-EDIT-2.3b connection source / target 选择状态与自动建议 ID

阶段目标：

```text
先在 ViewModel 层接通 draft nodes 到新增 connection 输入的状态桥，
为后续 View 接入 source / target ComboBox 做准备。
```

完成文档：

```text
docs/FlowWeaver_WORKFLOW-EDIT-2.3b_Connection选择状态与自动建议ID.md
```

当前结论：

* 已新增 `SelectedNewDraftConnectionSourceNode`。
* 已新增 `SelectedNewDraftConnectionTargetNode`。
* 选择 source / target node 会填充现有 endpoint 输入字段。
* source / target 均存在时会自动建议不重复的 connection id。
* 用户手动填写的 connection id 不会被覆盖。
* source / target port 仍保持手动输入。

验证结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "MainWindowViewModelWorkflowTests"
通过：61，失败：0，跳过：0

dotnet build Avalonia_UI\Avalonia_UI.sln --no-restore
成功，警告：0，错误：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：264，失败：0，跳过：0
```

建议下一步：

```text
WORKFLOW-EDIT-2.3c：
connection View 接入任务说明。
```

### 2.139 WORKFLOW-EDIT-2.3c connection View 接入任务说明

阶段目标：

```text
为 WorkflowSummaryView 的新增 connection 表单接入 source / target 选择入口，
明确纯 View 修改范围和测试要求。
```

完成文档：

```text
docs/FlowWeaver_WORKFLOW-EDIT-2.3c_ConnectionView接入任务说明.md
```

当前结论：

* View 接入应绑定 `WorkflowDefinitionDraftStructure.Nodes`。
* source ComboBox 绑定 `SelectedNewDraftConnectionSourceNode`。
* target ComboBox 绑定 `SelectedNewDraftConnectionTargetNode`。
* ComboBox 只是辅助选择，必须保留 source / target node id 手动输入。
* source / target port 继续保留手动输入，不做端口下拉。
* 不允许新增 converter、code-behind 或后端改动。

建议下一步：

```text
WORKFLOW-EDIT-2.3d：
connection View 最小接入。
```

### 2.140 WORKFLOW-EDIT-2.3d connection View 最小接入

阶段目标：

```text
在 WorkflowSummaryView 的新增 connection 表单中接入 source / target ComboBox，
并保留 source / target node id 手动输入降级能力。
```

完成文档：

```text
docs/FlowWeaver_WORKFLOW-EDIT-2.3d_ConnectionView最小接入.md
```

当前结论：

* 新增 connection 表单已接入 source ComboBox。
* 新增 connection 表单已接入 target ComboBox。
* 两个 ComboBox 均绑定 `WorkflowDefinitionDraftStructure.Nodes`。
* source / target `SelectedItem` 分别绑定对应 ViewModel 选择状态。
* source / target node id 手动输入仍保留。
* source / target port 手动输入仍保留。
* 未新增 converter、code-behind 或后端改动。

验证结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "WorkflowSummaryViewStructureTests|MainWindowViewModelWorkflowTests"
通过：66，失败：0，跳过：0

dotnet build Avalonia_UI\Avalonia_UI.sln --no-restore
成功，警告：0，错误：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：264，失败：0，跳过：0
```

建议下一步：

```text
WORKFLOW-EDIT-2.3e：
connection 输入体验后置复核。
```

### 2.141 WORKFLOW-EDIT-2.3e connection 输入体验后置复核

阶段目标：

```text
复核 WORKFLOW-EDIT-2.3 是否完成 source / target 选择、
connection id 自动建议和手动输入降级边界。
```

完成文档：

```text
docs/FlowWeaver_WORKFLOW-EDIT-2.3e_Connection输入体验后置复核.md
```

当前结论：

* `SelectedNewDraftConnectionSourceNode` 已接入 ViewModel。
* `SelectedNewDraftConnectionTargetNode` 已接入 ViewModel。
* 选择 source / target 会填充 endpoint 输入字段。
* connection id 会自动建议并避开重复。
* 用户手动 connection id 不会被覆盖。
* `WorkflowSummaryView` 已接入 source / target ComboBox。
* source / target node id 和 port 手动输入仍保留。

验证结果：

```text
dotnet build Avalonia_UI\Avalonia_UI.sln --no-restore
成功，警告：0，错误：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：264，失败：0，跳过：0
```

建议下一步：

```text
WORKFLOW-EDIT-2.4：
桌面真实 smoke 与结构化编辑后置复核。
```

### 2.142 WORKFLOW-EDIT-2.4a 桌面 smoke 前置清单

阶段目标：

```text
明确 WORKFLOW-EDIT-2 进入真实路径 smoke 时，
哪些验证可以自动执行，
哪些仍需要后续人工 Desktop 点击复核。
```

完成文档：

```text
docs/FlowWeaver_WORKFLOW-EDIT-2.4a_桌面Smoke前置清单.md
```

当前结论：

* 自动 smoke 优先使用发布 Desktop assembly/API client + 独立 EngineHost 的正式路径。
* 不直接用 `dotnet run` 启动完整 GUI，以免挂住执行流或影响用户桌面。
* 最贴近本阶段的自动用例是 `DesktopPublishWorkflowRunEventSmokeTests`。
* 人工 GUI smoke 仍保留为后续复核项。

建议下一步：

```text
WORKFLOW-EDIT-2.4b：
发布 Desktop workflow run event 自动 smoke。
```

### 2.143 WORKFLOW-EDIT-2.4b 发布 Desktop workflow run event 自动 smoke

阶段目标：

```text
执行发布 Desktop assembly/API client + portable EngineHost 的正式路径自动 smoke，
确认发布 Desktop client 与 EngineHost 的 API/WebSocket run lifecycle 链路仍可用。
```

完成文档：

```text
docs/FlowWeaver_WORKFLOW-EDIT-2.4b_发布DesktopWorkflowRunEvent自动Smoke.md
```

验证结果：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "DesktopPublishWorkflowRunEventSmokeTests"
通过：1，失败：0，跳过：0
```

当前结论：

* Desktop 发布产物可生成。
* portable EngineHost 可独立启动。
* 发布 Desktop API client 可连接 EngineHost。
* 发布 Desktop WebSocket client 可收到 `ENGINE_READY`。
* workflow run lifecycle 可收到 `WORKFLOW_STARTED` / `WORKFLOW_FINISHED`。
* 本步骤仍不覆盖人工 GUI 点击。

建议下一步：

```text
WORKFLOW-EDIT-2.4c：
结构化编辑人工 Desktop smoke 清单与后置复核。
```

### 2.144 WORKFLOW-EDIT-2.4c 人工 Desktop smoke 清单与后置复核

阶段目标：

```text
明确自动发布 smoke 已覆盖的正式路径，
并列出尚未执行的人工 Desktop GUI 点击 smoke 清单。
```

完成文档：

```text
docs/FlowWeaver_WORKFLOW-EDIT-2.4c_人工DesktopSmoke清单与后置复核.md
```

当前结论：

* `DesktopPublishWorkflowRunEventSmokeTests` 已通过。
* 自动发布路径证明 Desktop API/WebSocket client 与 EngineHost run lifecycle 可用。
* 自动 smoke 不等同于人工 GUI 点击。
* 人工 Desktop 点击 smoke 尚未执行。
* WORKFLOW-EDIT-2 暂不能宣称完整完成。

建议下一步：

```text
WORKFLOW-EDIT-2.4d：
Headless GUI 自动 smoke，补齐 View 运行时加载与关键绑定验收。
```

---

### 2.145 WORKFLOW-EDIT-2.4d Headless GUI 自动 smoke

阶段目标：

```text
在不启动真实 Desktop 窗口、不接入 EngineHost 的前提下，
确认 WorkflowSummaryView 可以在 Avalonia Headless runtime 中加载，
并且结构化编辑关键 ComboBox 能获得 ViewModel 绑定数据。
```

完成文档：

```text
docs/FlowWeaver_WORKFLOW-EDIT-2.4d_HeadlessGUI自动Smoke.md
```

当前结论：

* 新增 `WorkflowSummaryViewHeadlessSmokeTests`。
* 新增测试侧 `Avalonia.Headless 11.3.12` 依赖。
* Headless smoke 覆盖节点类型下拉和 connection source / target 下拉的运行时绑定。
* `dotnet build Avalonia_UI\Avalonia_UI.sln --no-restore` 通过，0 警告，0 错误。
* `dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "WorkflowSummaryViewHeadlessSmokeTests"` 通过。
* `dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore` 通过：265 个测试。
* 本步骤仍不等同于人工 Desktop 点击 smoke。

建议下一步：

```text
WORKFLOW-EDIT-2.5：
结构化编辑阶段小结与后续边界分析。
```

---

### 2.146 WORKFLOW-EDIT-2.5 结构化编辑阶段小结与后续边界分析

阶段目标：

```text
对 WORKFLOW-EDIT-2 做阶段小结，
明确当前结构化编辑已完成的自动验收边界、
仍未覆盖的人工 Desktop smoke、
以及后续是否应继续扩展到 port/schema/画布能力。
```

完成文档：

```text
docs/FlowWeaver_WORKFLOW-EDIT-2.5_结构化编辑阶段小结与后续边界分析.md
```

当前结论：

* WORKFLOW-EDIT-2 已完成 warning/error 可读化、node 输入体验、connection 输入体验、发布路径 smoke、Headless GUI smoke。
* 当前支持表单式新增/删除 node 和 connection，仍以 `WorkflowDefinitionDraftJson` 作为保存接口唯一输入。
* source / target port 仍为手动输入。
* port 下拉、端口类型兼容、自动连接推荐、画布、拖拽连线继续不属于当前收口范围。
* 人工 Desktop 点击 smoke 尚未被 Headless smoke 完全替代，更适合作为发布前或用户试用前验收清单。

建议下一步：

```text
WORKFLOW-EDIT-2.6：
结构化编辑目标完成审计与人工 Desktop smoke 决策。
```

---

## 一、总体目标

将桌面端调整为：

```text
固定 AppShell
+
组件注册中心
+
页面与区域管理
+
Schema 动态表单
+
专用编辑器注册
+
可选外部 DLL 模块
```

最终达到：

* `MainWindow.axaml`只负责窗口外壳和固定区域。
* 新增普通页面时，不再修改MainWindow。
* 后端新增普通配置字段时，前端可根据Schema自动显示。
* 新增复杂编辑器时，通过组件注册或模块安装实现。
* 样式、主题和轻量效果可以独立更新。
* 外部组件更新默认重启Desktop生效，不强行追求运行中卸载。
* 未识别组件能够回退到通用表单或JSON编辑器。

---

# 二、最终结构

```text
MainWindow / AppShell
├─ HeaderRegion
├─ NavigationRegion
├─ MainRegion
├─ InspectorRegion
├─ StatusRegion
└─ DialogRegion

UiComponentManager
├─ PageRegistry
├─ NodeEditorRegistry
├─ DataViewerRegistry
├─ SettingsSectionRegistry
├─ DialogRegistry
└─ StyleResourceRegistry

UiModuleManager
├─ 内置模块
├─ 外部DLL模块
├─ 模块版本检查
├─ 能力检查
├─ 注册与注销
└─ 模块生命周期
```

MainWindow只认识：

```text
导航项集合
当前页面
当前属性面板
当前状态组件
当前对话框
```

MainWindow不直接认识：

```text
WorkflowPage
RunMonitorPage
OfficeMappingEditor
ExcelPreviewView
新的插件页面
```

---

# 三、阶段一：固定Shell与区域契约

## 目标

先冻结MainWindow职责，避免后续新增功能继续修改主窗口结构。

## 需要实现

定义固定区域：

```text
NavigationRegion
MainRegion
InspectorRegion
StatusRegion
DialogRegion
SettingsRegion
DataViewerRegion
NodeEditorRegion
```

建立区域名称常量：

```csharp
public static class UiRegions
{
    public const string Navigation = "NavigationRegion";
    public const string Main = "MainRegion";
    public const string Inspector = "InspectorRegion";
    public const string Status = "StatusRegion";
    public const string Dialog = "DialogRegion";
    public const string Settings = "SettingsRegion";
    public const string DataViewer = "DataViewerRegion";
    public const string NodeEditor = "NodeEditorRegion";
}
```

MainWindow建议只保留：

```xml
<Grid>
    <ContentControl Content="{Binding HeaderContent}" />

    <ItemsControl ItemsSource="{Binding NavigationItems}" />

    <ContentControl Content="{Binding CurrentPage}" />

    <ContentControl Content="{Binding CurrentInspector}" />

    <ItemsControl ItemsSource="{Binding StatusComponents}" />

    <ContentControl Content="{Binding CurrentDialog}" />
</Grid>
```

## 阶段限制

本阶段不做：

* 外部DLL加载。
* 运行时卸载。
* 节点Schema表单。
* 新页面开发。
* 自由节点画布。

## 验收

* MainWindow不包含业务页面详细布局。
* Shell区域名称稳定。
* 页面切换不依赖修改MainWindow。
* 现有五个页面行为不回归。

---

# 四、阶段二：建立组件注册中心

## 目标

让页面、面板和编辑器通过统一描述信息注册，而不是写死在主窗口。

## 组件类型

```csharp
public enum UiComponentKind
{
    Page,
    Inspector,
    StatusWidget,
    Dialog,
    SettingsSection,
    NodeEditor,
    DataViewer
}
```

## 组件描述

```csharp
public sealed record UiComponentDescriptor(
    string Id,
    string ModuleId,
    UiComponentKind Kind,
    string TitleKey,
    string Region,
    int Order,
    Func<IServiceProvider, object> ViewModelFactory,
    IReadOnlyCollection<string> RequiredCapabilities);
```

## 注册中心接口

```csharp
public interface IUiComponentRegistry
{
    void Register(UiComponentDescriptor descriptor);

    bool Unregister(string componentId);

    IReadOnlyList<UiComponentDescriptor> GetByRegion(
        string region);

    UiComponentDescriptor? Find(string componentId);

    object Create(
        string componentId,
        IServiceProvider services);
}
```

## 实施原则

* 组件ID全局唯一。
* 组件标题使用本地化Key。
* 页面排序由`Order`控制。
* 能力不足时不创建组件。
* 注册失败不能导致Desktop整体启动失败。
* 重复ID必须拒绝并写日志。

---

# 五、阶段三：迁移现有五个页面

## 目标

验证组件注册体系能够承载现有页面。

## 内置模块建议

```text
FlowWeaver.Ui.Workflow
FlowWeaver.Ui.RunMonitor
FlowWeaver.Ui.Data
FlowWeaver.Ui.Logs
FlowWeaver.Ui.Settings
```

每个模块注册自己的页面：

```csharp
registry.Register(new UiComponentDescriptor(
    Id: "page.workflow",
    ModuleId: "flowweaver.ui.workflow",
    Kind: UiComponentKind.Page,
    TitleKey: "navigation.workflow",
    Region: UiRegions.Main,
    Order: 100,
    ViewModelFactory: services =>
        services.GetRequiredService<WorkflowWorkspaceViewModel>(),
    RequiredCapabilities: []));
```

## 迁移完成后

导航栏由：

```text
NavigationItems
```

自动生成。

MainWindow不再写：

```xml
<TabItem>
    <pages:WorkflowPage />
</TabItem>
```

而是根据注册信息生成导航和页面。

## 验收

* 工作流、运行、数据、日志和设置页全部正常。
* 页面选中状态保留。
* 页面切换不会反复创建不必要实例。
* 页面ViewModel能够正确释放。
* 现有ActionState和Command不改变。

---

# 六、阶段四：NodeEditor注册体系

## 目标

让不同节点可以拥有专用Avalonia编辑器，但主工作流页面不需要知道具体节点类型。

## 接口建议

```csharp
public interface INodeEditorProvider
{
    string ProviderId { get; }

    bool CanEdit(NodeDefinitionDto definition);

    object CreateEditorViewModel(
        NodeEditorContext context,
        IServiceProvider services);
}
```

## 查找顺序

```text
打开节点
→ 查找专用NodeEditorProvider
→ 找到：显示专用组件
→ 未找到：使用Schema通用表单
→ Schema无法渲染：回退JSON编辑器
```

## 三级降级

```text
专用编辑器
→ Schema动态表单
→ 原始JSON
```

因此：

* 普通节点不需要专用前端代码。
* 复杂节点可以单独开发组件。
* 前端旧版本遇到新节点时仍能查看或编辑JSON。
* 单个专用编辑器故障不会阻断整个工作流编辑器。

---

# 七、阶段五：JSON Schema动态配置表单

## 目标

后端增加普通设置时，前端无需重新编译即可显示。

## 后端提供

```text
node_type
config_schema_version
configuration_schema
ui_schema
capabilities
minimum_client_capabilities
```

## 控件映射

| Schema类型       | Avalonia控件            |
| -------------- | --------------------- |
| string         | TextBox               |
| integer        | NumericUpDown         |
| number         | NumericUpDown         |
| boolean        | CheckBox或ToggleSwitch |
| enum           | ComboBox              |
| object         | 分组面板并递归渲染             |
| array          | 动态列表编辑器               |
| file-path      | 文件选择组件                |
| directory-path | 目录选择组件                |
| table-selector | 表选择器                  |
| field-selector | 字段选择器                 |
| regex          | 正则编辑器                 |
| secret         | PasswordBox或脱敏输入      |

## 前端实际处理

```text
读取Schema
→ 检查Schema版本
→ 检查客户端支持的Widget
→ 递归构建字段ViewModel
→ DataTemplate显示控件
→ 本地基础校验
→ 提交后端Validate
```

## 后端设置增加时

例如后端增加：

```json
{
  "skip_empty_rows": {
    "type": "boolean",
    "default": true
  }
}
```

实际操作：

1. 后端更新Schema。
2. 前端重新读取NodeDefinition。
3. 通用渲染器识别`boolean`。
4. 自动显示CheckBox。
5. 不需要修改MainWindow。
6. 不需要发布新的Desktop。
7. 通常不需要重启，只需刷新节点定义或重新打开编辑器。

这是便携性最高的一类扩展。

---

# 八、阶段六：样式与效果资源管理

## 目标

把颜色、间距、动画、控件样式从页面中分离。

## 建议资源结构

```text
Avalonia_UI/Styles/
├─ Colors.axaml
├─ Typography.axaml
├─ Spacing.axaml
├─ Buttons.axaml
├─ Lists.axaml
├─ Cards.axaml
├─ StatusBadges.axaml
├─ Dialogs.axaml
└─ Transitions.axaml
```

## 可独立调整的效果

* 颜色。
* 字号。
* 圆角。
* 阴影。
* 按钮状态。
* 列表Hover。
* 状态Badge。
* 页面淡入。
* 面板展开收起。
* 错误提示动画。
* Loading表现。

## 后续增加视觉效果的实际操作

### 修改已有视觉效果

例如修改按钮Hover：

1. 修改`Buttons.axaml`。
2. 不修改页面。
3. 不修改ViewModel。
4. 重新构建Desktop。
5. 发布新的Desktop文件。

### 增加新的效果Class

例如：

```xml
<Button Classes="Primary PulseOnSuccess" />
```

实际需要：

1. 在样式资源中新增`PulseOnSuccess`。
2. 页面为目标控件添加Class。
3. 重新构建Desktop。

### 运行时更换主题

可以使用：

```text
DynamicResource
MergedDictionaries
ThemeVariant
```

实际需要：

1. 主题资源已经被前端支持。
2. 切换已注册ResourceDictionary。
3. 通常不需要重启。

### 新增全新的复杂动画控件

例如动态流程图、特殊图表：

1. 编写新的Avalonia控件。
2. 注册为组件。
3. 重新构建内部模块，或发布外部DLL模块。
4. 安装模块后重启Desktop。

仅靠资源文件不能增加新的C#交互逻辑。

---

# 九、阶段七：外部UI模块契约

## 目标

复杂专用界面可以作为独立模块安装，而不重新修改Shell。

## 契约程序集

建立：

```text
FlowWeaver.Ui.Contracts.dll
```

只包含：

* 组件接口。
* 模块接口。
* Descriptor。
* Context。
* 必要DTO。
* 能力标识。
* 版本结构。

不得包含：

* MainWindow。
* 具体页面。
* 具体API Client实现。
* 数据库访问。
* EngineHost业务实现。

## 模块接口

```csharp
public interface IFlowWeaverUiModule : IDisposable
{
    UiModuleManifest Manifest { get; }

    void Register(
        IUiComponentRegistry components,
        IServiceCollection services);

    Task InitializeAsync(
        CancellationToken cancellationToken);

    Task ShutdownAsync(
        CancellationToken cancellationToken);
}
```

## 模块清单

```json
{
  "module_id": "flowweaver.ui.office",
  "version": "1.0.0",
  "contract_version": "1.0",
  "minimum_host_version": "0.8.0",
  "entry_assembly": "FlowWeaver.Ui.Office.dll",
  "entry_type": "FlowWeaver.Ui.Office.OfficeUiModule",
  "capabilities": [
    "node_editor.office_mapping.v1"
  ]
}
```

---

# 十、阶段八：外部模块加载

## 推荐技术

```text
AssemblyLoadContext
+
AssemblyDependencyResolver
+
module.json
+
FlowWeaver.Ui.Contracts
```

## 模块目录

```text
FlowWeaverPortable/
  Desktop/
  ui-modules/
    Office/
      module.json
      FlowWeaver.Ui.Office.dll
      依赖DLL
    ExcelAdvanced/
      module.json
      FlowWeaver.Ui.ExcelAdvanced.dll
```

## 启动流程

```text
Desktop启动
→ 扫描ui-modules
→ 读取module.json
→ 检查宿主版本
→ 检查契约版本
→ 检查签名或白名单
→ 加载程序集
→ 创建模块实例
→ 注册组件
→ 生成导航和编辑器入口
```

## 第一版更新策略

推荐：

```text
模块可动态发现
模块安装后重启生效
不承诺运行中卸载
```

不建议第一版实现真正热替换。

---

# 十一、后续增加页面的实际操作

## 情况一：新增内置普通页面

例如新增“节点目录”页面。

需要操作：

1. 新建`NodeCatalogPage.axaml`。
2. 新建`NodeCatalogViewModel.cs`。
3. 在内置模块中注册`page.node-catalog`。
4. 添加本地化Key。
5. 添加测试。
6. 重新构建Desktop。
7. Codex复核。
8. 发布新Desktop。

不需要：

* 修改MainWindow。
* 修改主导航XAML。
* 修改Shell结构。

便携性：

```text
结构便携性：高
发布便携性：需要重新发布Desktop
运行时动态性：低
```

## 情况二：通过外部模块增加页面

例如企业专用“质量分析”页面。

需要操作：

1. 创建独立模块项目。
2. 引用`FlowWeaver.Ui.Contracts`。
3. 实现页面和ViewModel。
4. 实现`IFlowWeaverUiModule`。
5. 编写`module.json`。
6. 构建DLL。
7. 复制到`ui-modules/QualityAnalysis/`。
8. 重启Desktop。

不需要：

* 修改MainWindow。
* 修改主程序业务代码。
* 重新发布完整EngineHost。

便携性：

```text
结构便携性：很高
安装便携性：复制目录即可
更新便携性：替换模块目录后重启
运行中热替换：第一版不支持
```

## 情况三：新增节点专用编辑器

例如Office可视化映射编辑器。

需要操作：

1. 实现`INodeEditorProvider`。
2. 声明支持的`node_type`。
3. 实现专用View和ViewModel。
4. 注册到`NodeEditorRegistry`。
5. 作为内置模块或外部DLL发布。
6. 重启Desktop。

工作流页面不需要修改。

---

# 十二、后续增加配置字段的实际操作

## 普通字段

例如增加：

```text
最大行数
跳过空行
错误时停止
编码格式
```

实际操作：

1. Codex修改后端配置Schema。
2. 更新Schema版本。
3. 更新后端校验。
4. 前端刷新NodeDefinition。
5. Gemini通用渲染器自动显示。

通常不需要：

* 修改Avalonia页面。
* 修改MainWindow。
* 发布新Desktop。
* 安装新DLL。

## 新控件类型

例如新增：

```text
表达式编辑器
字段映射矩阵
可视化文件预览
```

实际操作：

1. 定义新的Widget能力，如`widget.field_mapping.v1`。
2. 前端实现对应组件。
3. 注册Widget。
4. 发布新Desktop或新UI模块。
5. 后端Schema引用该Widget。
6. 旧客户端回退到普通字段或JSON。

---

# 十三、后续增加视觉效果的便携性

| 变化类型            | 是否改MainWindow |  是否重编译 | 是否重启 | 便携性   |
| --------------- | ------------: | -----: | ---: | ----- |
| 修改颜色、字号、圆角      |             否 |    通常是 |    是 | 高     |
| 切换已内置主题         |             否 |      否 |  通常否 | 很高    |
| 修改Button/List样式 |             否 |      是 |    是 | 高     |
| 新增页面过渡效果        |             否 |      是 |    是 | 高     |
| 新增状态Badge样式     |             否 |      是 |    是 | 高     |
| 后端改变字段标题和顺序     |             否 |      否 | 否或刷新 | 很高    |
| 后端新增普通配置字段      |             否 |      否 | 否或刷新 | 很高    |
| 新增专用复杂控件        |             否 | 是或模块更新 |    是 | 中高    |
| 新增外部页面模块        |             否 |  只编译模块 |    是 | 高     |
| 真正运行时替换DLL      |             否 |      是 |  理论否 | 低，风险高 |

---

# 十四、模块安装和更新流程

## 安装

```text
获得模块包
→ 校验模块ID、版本和签名
→ 解压到ui-modules
→ 重启Desktop
→ 自动注册页面和组件
```

## 更新

推荐使用staging：

```text
ui-modules/
  Office/
    current/
  .staging/
    Office-1.2.0/
```

流程：

```text
下载或复制新版本
→ 校验
→ 写入staging
→ 关闭Desktop
→ 原子替换current
→ 启动Desktop
→ 加载新模块
→ 失败则回滚旧版本
```

## 卸载

```text
关闭Desktop
→ 删除模块目录
→ 启动Desktop
→ 导航和组件自动消失
```

如果现有Workflow引用该模块对应的节点：

* Workflow仍保留原始定义。
* UI显示“缺少对应编辑器”。
* 回退JSON。
* 后端是否可以运行由节点后端实现决定。

---

# 十五、版本与兼容策略

模块至少检查：

```text
module_version
contract_version
minimum_host_version
maximum_host_version（可选）
required_capabilities
```

建议兼容规则：

```text
契约主版本不同：
拒绝加载

契约次版本较新：
检查能力后决定

缺少可选能力：
降级显示

缺少必需能力：
禁用模块并给出原因
```

旧客户端处理新组件：

```text
能够识别：
正常显示

不能识别Widget：
回退通用控件

不能识别节点编辑器：
回退Schema表单

Schema也不支持：
回退JSON

模块契约不兼容：
拒绝加载
```

---

# 十六、安全边界

外部DLL不是沙箱。

模块在Desktop进程中运行，理论上可以访问：

* 文件。
* 网络。
* 内存。
* Token。
* 用户数据。
* UI对象。

因此第一版应要求：

* 仅加载受信任模块。
* 模块目录白名单。
* 模块SHA-256。
* 可选代码签名。
* 模块许可证metadata。
* 禁止从后端直接指定任意程序集路径。
* 禁止加载网络路径DLL。
* 禁止任意远程XAML。
* 不允许插件自行读取Token。
* API调用通过受控服务接口。

---

# 十七、测试与验收

每个模块至少测试：

* 清单解析。
* 契约版本。
* 重复组件ID。
* 缺少程序集。
* 入口类型错误。
* 初始化异常。
* 页面创建异常。
* 模块关闭。
* 模块更新回滚。
* 本地化Key缺失。
* Schema回退。
* JSON回退。
* Token不泄露。

UI验收：

* 新页面无需改MainWindow。
* 删除模块后Shell仍能启动。
* 单个模块异常不拖垮Desktop。
* 页面切换不丢失核心状态。
* 模块不兼容时提示清晰。
* 外部模块不影响现有五个页面。

---

# 十八、推荐实施顺序

## 当前分层

执行时必须分层推进：

| 层级 | 阶段 | 当前处理 |
| --- | --- | --- |
| 近期 | COMPONENT-0 到 COMPONENT-2 | 可以作为下一轮小步分析和最小实现范围 |
| 中期 | COMPONENT-3 到 COMPONENT-5 | 等内置页面迁移稳定后再进入 |
| 远期 | COMPONENT-6 到 COMPONENT-10 | 只作为插件化和 Distribution 方向参考 |

近期阶段不得顺手实现外部模块加载、安装更新、签名或热更新。

```text
COMPONENT-0
冻结Shell区域和组件契约

COMPONENT-1
整理 MainWindow 当前职责清单与 AppShell 目标结构

COMPONENT-2
建立内置页面清单最小实现方案，必要时再迁移硬编码 TabItem

COMPONENT-3
建立NodeEditorRegistry

COMPONENT-4
实现JSON Schema通用表单

COMPONENT-5
拆分样式和动画ResourceDictionary

COMPONENT-6
建立FlowWeaver.Ui.Contracts

COMPONENT-7
实现AssemblyLoadContext模块扫描

COMPONENT-8
用Office映射编辑器做外部模块试点

COMPONENT-9
实现模块安装、更新、回滚和发布归档

COMPONENT-10
最后评估运行时卸载和真正热更新
```

其中`COMPONENT-10`不是第一版必需项。

其中 `COMPONENT-6` 到 `COMPONENT-10` 也不是当前 UI-COMPONENT-0 的后续直接任务；需要另起插件化/Distribution 阶段分析后再决定是否执行。

---

# 十九、最终效果

采用这套结构后，后续扩展分为三种成本等级。

## 低成本扩展

```text
新增配置字段
修改默认值
修改枚举
调整字段顺序
调整提示文字
切换已支持主题
```

只改后端Schema或资源数据，通常无需发布新前端。

## 中成本扩展

```text
新增内部页面
新增普通数据查看器
新增已有类型的状态组件
新增通用视觉效果
```

需要编译Desktop，但不修改MainWindow。

## 独立模块扩展

```text
Office映射编辑器
企业专用页面
复杂数据预览
新型节点专用编辑器
```

只编译和发布模块，复制到`ui-modules`并重启Desktop，主程序Shell不变。

最终目标是：

```text
MainWindow长期稳定
普通配置由Schema驱动
复杂功能由组件模块扩展
样式效果由资源层管理
前端无法识别时安全降级
模块更新默认重启生效
```
