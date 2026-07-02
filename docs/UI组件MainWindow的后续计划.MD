# FlowWeaver Avalonia 组件管理与可扩展界面实施方案

> 文档状态：UI-COMPONENT-2b.4c.1 选中状态同步前置方案已补充
> 当前执行点：建议先用固定 TabControl 的 SelectedIndex 桥接 SelectedShellPageKey，暂不进入动态页面承载
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
