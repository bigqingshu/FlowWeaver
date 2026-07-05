# FlowWeaver：交给 Gemini 的 UI 界面设计、MainWindow 拆分与组件接口规划任务说明

> 文档用途：本文件用于交给 Gemini，作为 FlowWeaver Avalonia 桌面端界面设计、`MainWindow.axaml` 拆分、页面组件规划和 XAML 重构的统一任务说明。  
> 当前状态：UI 本地化与语言切换工作已经由 Codex 单独进行，Gemini 不负责翻译或本地化实现。  
> 技术栈：Avalonia UI + .NET 10 + C# + MVVM + HTTP/WebSocket。  
> 核心目标：允许 Gemini 设计并实现界面结构，但必须分阶段、可回滚、保持现有业务功能和绑定契约。  
> 后续分工：Gemini 负责界面结构、XAML、组件和样式；Codex 负责绑定复核、业务接线、构建测试、本地化复核和功能回归。

---

## 1. 你的角色

你是 FlowWeaver 桌面端 UI/UX 架构与 Avalonia XAML 重构顾问。

你的任务包括：

1. 分析当前桌面端的信息结构。
2. 重新规划页面导航和功能分区。
3. 设计主要页面的线框结构。
4. 将当前过大的 `MainWindow.axaml` 逐步拆分。
5. 把 `MainWindow` 收口为应用 Shell。
6. 设计并实现可复用的 Avalonia `UserControl`。
7. 设计组件的输入、输出、状态和绑定接口。
8. 提供可供 Codex 复核和继续实现的工程化 XAML 结构。
9. 保持现有业务逻辑、API、DTO、Command 和运行语义不变。

你当前不负责：

- 本地化实现。
- 翻译。
- 本地化 Key 设计。
- EngineHost。
- API 路由。
- Workflow Definition Schema。
- RuntimeEvent 协议。
- AuditEvent 协议。
- TableRef 或 SharedPublication 协议。
- 发布和打包。
- 自动更新。
- 安装器。
- 大规模重写业务 ViewModel。
- 一次性推翻全部 UI。

---

## 2. 项目当前能力

FlowWeaver 当前已经具备：

- EngineHost 启动和连接检查。
- Token 鉴权。
- RuntimeEvent WebSocket 事件流。
- 工作流列表。
- 内置模板创建工作流。
- 工作流启动和取消。
- Run、NodeRun 状态查看。
- 工作流定义详情。
- Revision 历史。
- 工作流定义 JSON 草稿编辑。
- 后端 Validate。
- 保存新 Revision。
- Revision 冲突保护。
- RuntimeEvent 和 AuditEvent 日志查看。
- TableRef 和 SharedPublication 摘要查看。
- 便携启动与发布归档能力。

当前项目已经可以内部试用。

本次任务不是扩展底层能力，而是把现有能力整理为更清晰、更稳定、更可维护的桌面界面。

---

## 3. 需要优先阅读的文件

开始前，请阅读：

```text
Avalonia_UI/Views/MainWindow.axaml
Avalonia_UI/Views/MainWindow.axaml.cs
Avalonia_UI/ViewModels/MainWindowViewModel.cs
Avalonia_UI/ViewModels/
Avalonia_UI/Models/
Avalonia_UI/Api/
Avalonia_UI/Services/
Avalonia_UI/Localization/
Avalonia_UI/App.axaml
Avalonia_UI/App.axaml.cs
Avalonia_UI/Avalonia_UI.csproj
```

其中本地化相关文件必须作为绑定边界阅读：

```text
Avalonia_UI/Localization/en-US.json
Avalonia_UI/Localization/zh-Hans.json
Avalonia_UI/Localization/DisplayTextFormatter.cs
Avalonia_UI/Localization/ILocalizationService.cs
Avalonia_UI/Localization/JsonLocalizationService.cs
Avalonia_UI/Models/SupportedLanguage.cs
Avalonia_UI/ViewModels/LanguageMenuItemViewModel.cs
```

还应参考：

```text
README.md
docs/FlowWeaver_便携版用户手册.md
docs/FlowWeaver_阶段M*
docs/FlowWeaver_阶段N*
docs/FlowWeaver_阶段O*
docs/FlowWeaver_阶段P*
```

阅读目标：

- 理解现有功能。
- 理解现有绑定。
- 理解所有 Command。
- 理解 ItemsSource 与 SelectedItem。
- 理解 Busy、Error、Empty 状态。
- 理解窗口关闭和 EngineHost 生命周期风险。
- 理解哪些能力已经存在。
- 理解哪些能力当前明确不支持。
- 理解现有语言菜单、语言设置持久化和本地化资源加载边界。
- 理解哪些显示文本已经由 ViewModel 或 `DisplayTextFormatter` 派生，不应在 XAML 中重新拼接。

---

## 4. 当前 UI 主要问题

当前 `MainWindow.axaml` 已经承载：

- 应用标题。
- 语言菜单。
- 连接配置。
- Token。
- 连接检查。
- RuntimeEvent Stream。
- 工作流列表。
- 创建工作流。
- 启动工作流。
- Run 列表。
- NodeRun 列表。
- 工作流定义。
- Revision。
- 节点列表。
- 连接列表。
- JSON 草稿。
- Validate。
- Save。
- RuntimeEvent 日志。
- AuditEvent。
- TableRef。
- SharedPublication。

主要问题：

1. `MainWindow.axaml` 文件过大。
2. 主窗口同时承担 Shell、导航、页面和组件职责。
3. 功能层次不够清楚。
4. 用户操作路径较分散。
5. 连接设置长期占据主区域。
6. 工作流编辑和运行监控被拆得较散。
7. 页面缺少统一的 Loading、Empty、Error 接口。
8. 后续继续增加功能时，主窗口会持续膨胀。
9. 当前界面更偏开发调试工具，而不是成熟桌面生产力工具。

---

## 5. 关于 MainWindow.axaml 的处理原则

### 5.1 允许重构和拆分

允许 Gemini：

- 修改 `MainWindow.axaml`。
- 将 `MainWindow` 改造成应用 Shell。
- 新增页面级 `UserControl`。
- 新增组件级 `UserControl`。
- 新增 `ResourceDictionary`。
- 新增样式资源。
- 移动原有 XAML 区域到新文件。
- 调整页面布局和导航。

### 5.2 禁止一次性无映射重写

禁止：

```text
直接删除旧 MainWindow 内容
→ 编写全新界面
→ 不提供功能映射
→ 不确认现有绑定是否保留
```

必须采用：

```text
功能盘点
→ 绑定映射
→ 无损拆分
→ Shell 化
→ 逐页改版
→ Codex 复核
```

### 5.3 MainWindow 最终职责

最终 `MainWindow.axaml` 只应保留：

- Window 属性。
- 应用级 Shell。
- 主导航。
- 全局连接状态摘要。
- 当前页面容器。
- 全局错误提示。
- 全局确认弹窗入口。
- 窗口关闭相关界面入口。

最终目标结构：

```text
MainWindow
  ├─ AppHeader
  ├─ Navigation
  ├─ ConnectionStatus
  ├─ ContentHost
  │    ├─ WorkflowPage
  │    ├─ RunMonitorPage
  │    ├─ DataPage
  │    ├─ LogsAuditPage
  │    └─ SettingsPage
  └─ GlobalOverlay / DialogHost
```

---

## 6. 第一阶段必须先做功能映射

在改 XAML 之前，必须先输出旧界面功能矩阵。

每项至少包含：

| 旧区域 | 旧绑定 Property | 旧 Command | ItemsSource | SelectedItem | Busy | Error | Empty | 显示文本来源 | 是否协议原值 | 新页面 | 新组件 | 是否保留 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|

示例：

| 旧功能 | 旧绑定 | 新页面 | 新组件 | 是否保留 |
|---|---|---|---|---|
| 检查连接 | `CheckConnectionCommand` | 设置 | `ConnectionPanelView` | 是 |
| 启动工作流 | `StartSelectedWorkflowCommand` | 工作流 | `WorkflowActionBar` | 是 |
| 取消运行 | `CancelSelectedRunCommand` | 运行监控 | `RunActionBar` | 是 |
| 保存 Revision | `SaveWorkflowDefinitionDraftCommand` | 工作流 | `DefinitionEditorView` | 是 |
| RuntimeEvent | `RuntimeEvents` | 运行监控/日志 | `RuntimeEventListView` | 是 |

不得遗漏：

- Command。
- SelectedItem。
- ItemsSource。
- IsBusy。
- ErrorMessage。
- EmptyMessage。
- 可见性条件。
- 生命周期行为。
- Token 脱敏。
- Revision 冲突。
- Event Stream 状态。
- 用户可读文本来源。
- 协议原值是否应保持原样。
- 本地化绑定是否被保留。

当前已经由 ViewModel 或 `DisplayTextFormatter` 处理的用户可读派生文本，不要在 XAML 中重新硬编码或用 `StringFormat` 重新拼接：

```text
NodeCountText
ConnectionCountText
EnabledText
AttemptText
MemberCountText
```

以下内容属于协议、技术或标识值，默认保持原样展示，不要翻译：

```text
RUNNING
SUCCEEDED
FAILED
CANCELLED
PUBLISHED
RuntimeEvent event_type
AuditEvent decision
workflow_run_id
node_run_id
table_ref_id
publication_id
v{number}
#{sequence_number}
timestamp
JSON field name
```

---

## 7. 推荐拆分顺序

### G.0：现状复核

只分析：

- 当前页面结构。
- 当前操作路径。
- 当前 ViewModel 职责。
- 当前绑定。
- 当前 Command。
- 当前页面状态。
- 当前组件缺口。

不改代码。

### G.1：无损拆分 View

先拆 View，不拆业务 ViewModel。

要求：

- 布局尽量保持原样。
- 所有 Property 保持不变。
- 所有 Command 保持不变。
- 所有 ItemsSource 保持不变。
- 所有 SelectedItem 保持不变。
- 所有功能保持不变。

第一层建议结构：

```text
Avalonia_UI/Views/
  MainWindow.axaml

  Pages/
    WorkflowPage.axaml
    RunMonitorPage.axaml
    DataPage.axaml
    LogsAuditPage.axaml
    SettingsPage.axaml
```

各页面第一阶段可以继续使用：

```xml
x:DataType="vm:MainWindowViewModel"
```

不要在第一步同时拆 ViewModel。

### G.2：MainWindow Shell 化

加入：

- 应用头部。
- 主导航。
- 连接状态摘要。
- 内容区。
- 设置入口。
- 全局错误条。
- DialogHost 或 Overlay。

此阶段仍尽量保持原有功能和绑定。

### G.3：拆分页面内部组件

建议组件：

```text
WorkflowListView
WorkflowSummaryView
WorkflowRevisionView
NodeListView
ConnectionListView
DefinitionEditorView
WorkflowActionBar

RunListView
RunSummaryView
NodeRunListView
RuntimeEventPanelView
RunActionBar

TableRefListView
SharedPublicationListView
SharedPublicationVersionView

RuntimeEventListView
AuditEventListView
LogFilterBar

ConnectionPanelView
ConnectionStatusView

ErrorBannerView
EmptyStateView
LoadingStateView
ConfirmDialogView
```

### G.4：逐页重设计

按顺序：

```text
工作流
运行监控
数据
日志与审计
设置
```

一次只重设计一个页面。

### G.5：Codex 分阶段复核

每完成一个阶段，由 Codex 复核：

- `dotnet build`。
- 编译绑定。
- Command 完整性。
- SelectedItem。
- ItemsSource。
- Busy。
- Error。
- Empty。
- 中文显示。
- Token 脱敏。
- Revision 冲突。
- RuntimeEvent。
- 生命周期。
- 自动化测试。
- 功能回归。

### G.6：最后再决定是否拆 ViewModel

只有当 View 和组件结构稳定后，才评估是否将：

```text
MainWindowViewModel
```

拆为：

```text
ConnectionViewModel
WorkflowWorkspaceViewModel
WorkflowDefinitionViewModel
RunMonitorViewModel
DataBrowserViewModel
LogsAuditViewModel
SettingsViewModel
```

View 拆分和 ViewModel 拆分不要同时进行。

---

## 8. 推荐新版信息架构

主导航建议：

```text
工作流
运行监控
数据
日志与审计
设置
```

### 8.1 工作流

主要用于：

- 查看工作流。
- 创建工作流。
- 查看定义。
- 查看 Revision。
- 查看节点。
- 查看连接。
- 编辑 JSON。
- Validate。
- Save Revision。
- Run。

推荐结构：

```text
左侧：
- 搜索
- 工作流列表
- 创建入口
- 模板入口

中间：
- 工作流概览
- 节点
- 连接
- Revision

右侧：
- 当前属性
- JSON 草稿
- Validate 结果

底部固定操作：
- 校验
- 保存
- 运行
```

核心操作路径：

```text
选择工作流
→ 查看定义
→ 修改草稿
→ 校验
→ 保存 Revision
→ 运行
```

### 8.2 运行监控

主要用于：

- 当前 Run。
- 历史 Run。
- NodeRun。
- 运行状态。
- 进度。
- 当前阶段。
- Attempt。
- 取消运行。
- 失败详情。
- WebSocket 状态。
- REST 恢复结果。

推荐结构：

```text
左侧：
- Run 列表
- 状态筛选
- 时间筛选

中间：
- Run 详情
- NodeRun 列表
- 进度和状态

右侧：
- 实时事件
- 错误详情
- 技术信息
```

### 8.3 数据

主要用于：

- TableRef。
- SharedPublication。
- SharedPublication Version。
- 来源 Run。
- 创建时间。
- 数据摘要。

当前只做摘要与引用查看。

不设计完整数据库表格编辑器。

### 8.4 日志与审计

主要用于：

- RuntimeEvent。
- AuditEvent。
- WorkflowRun ID 筛选。
- NodeRun ID 筛选。
- Event Type 筛选。
- Sequence 筛选。
- 日志级别。
- 复制技术详情。

### 8.5 设置

主要用于：

- Base URL。
- Token。
- 检查连接。
- Event Stream 状态。
- 日志目录。
- Runtime 目录。
- 启动参数说明。

连接设置应从主页面大块区域中移出，改为设置页、侧边栏或弹出面板。

主界面只保留连接摘要：

```text
● EngineHost 已连接
127.0.0.1:8000
事件流已连接
```

---

## 9. UI 组件接口设计要求

每个组件必须明确：

- 组件职责。
- 输入属性。
- 输出 Command。
- SelectedItem。
- ItemsSource。
- IsBusy。
- ErrorMessage。
- EmptyMessage。
- IsReadOnly。
- IsVisible。
- 是否允许独立复用。
- 是否需要技术详情展开。
- 是否需要复制功能。

示例：

### WorkflowListView

```text
组件职责：
显示工作流列表，支持选择、刷新、搜索和创建入口。

输入：
Items
SelectedItem
IsBusy
SearchText
StatusFilter
EmptyMessage
ErrorMessage

输出：
SelectionChangedCommand
RefreshCommand
CreateCommand

状态：
Loading
Empty
Error
Normal
```

### RunListView

```text
组件职责：
显示运行记录，支持选择、刷新、取消和状态筛选。

输入：
Items
SelectedItem
IsBusy
CanCancel
StatusFilter
ErrorMessage

输出：
SelectionChangedCommand
RefreshCommand
CancelCommand

状态：
Loading
Empty
Error
Running
Completed
```

---

## 10. 必须保留的架构原则

### 10.1 MVVM

必须保持：

- View 不直接请求 HTTP。
- View 不直接访问数据库。
- View 不直接修改 Workflow Definition。
- 业务逻辑不放入 code-behind。
- Command 由 ViewModel 提供。
- 状态由 ViewModel 管理。

### 10.2 编译绑定

继续使用：

```xml
x:DataType="..."
```

不要改成大量无类型字符串绑定。

### 10.3 现有业务契约

不得随意修改：

- API Client 方法。
- DTO。
- Workflow Definition Schema。
- Revision 语义。
- RuntimeEvent。
- AuditEvent。
- TableRef。
- SharedPublication。
- 现有 Command 行为。
- Token 处理方式。

### 10.4 本地化与显示文本契约

Gemini 不负责新增或修改本地化资源，但拆分 View 和重排 XAML 时必须保留现有本地化契约：

- 不得新增硬编码中文或英文用户可见文本。
- 不得把已经由 ViewModel 暴露的本地化文本改回 XAML 字符串。
- 不得在 XAML 中重新拼接 `node(s)`、`connection(s)`、`enabled/disabled`、`attempt {n}`、`member(s)` 等派生文本。
- 不得修改 `Avalonia_UI/Localization/*.json`。
- 不得修改 `DisplayTextFormatter`、`ILocalizationService`、`JsonLocalizationService` 的职责。
- 移动语言菜单时必须保留 `ChangeLanguageCommand`、语言项、当前语言显示和设置持久化行为。
- 新增用户可见文案时，只列出文案清单和建议位置，由 Codex 补本地化 Key 与资源。
- 协议值、ID、版本号、序列号、时间戳和 JSON 字段名保持原样，不做翻译。

### 10.5 不做自由画布

当前阶段不要设计为必须依赖：

- 拖拽节点画布。
- 鼠标连线。
- MiniMap。
- 无限画布。
- 复杂缩放。
- 节点端口路由。

可以为未来画布保留入口，但当前第一版仍使用：

- 节点列表。
- 连接列表。
- 配置面板。
- JSON 编辑器。

---

## 11. 视觉方向

推荐风格：

- 桌面生产力工具。
- 稳定、克制。
- 信息密度适中。
- 状态清晰。
- 操作路径明确。
- 不过度拟物。
- 不大面积渐变。
- 不游戏化。
- 不堆叠大量卡片。

视觉重点：

- 工作流状态。
- 运行状态。
- 当前选择。
- 错误。
- 警告。
- 未保存修改。
- Validate 结果。
- Revision 冲突。
- Event Stream 状态。

---

## 12. DPI 与桌面适配

需要考虑：

```text
1920×1080
2560×1440
3840×2160
```

缩放：

```text
100%
125%
150%
200%
```

要求：

- 不过度依赖固定宽度。
- 长 ID 可截断并支持复制。
- 长错误信息可展开。
- JSON 编辑器独立滚动。
- 左右面板支持伸缩。
- 最小窗口下核心操作仍可见。
- 工具栏可折叠或进入更多菜单。
- 关键操作不能因窗口缩小完全消失。

---

## 13. 必须考虑的状态

每个页面都要设计：

```text
未连接
正在连接
连接成功
鉴权失败
连接中断
正在加载
空数据
加载成功
加载失败
操作成功
操作失败
数据过期
Revision 冲突
WebSocket 断开
REST 恢复
```

### 工作流页面

- 无工作流。
- 未选择工作流。
- 正在创建。
- 创建失败。
- 草稿已修改。
- 草稿未校验。
- Validate 失败。
- Validate 通过。
- 保存成功。
- Revision 冲突。
- 当前工作流正在运行。

### 运行页面

- 无运行记录。
- RUNNING。
- SUCCEEDED。
- FAILED。
- CANCELLED。
- 正在取消。
- Event Stream 断开。
- REST 恢复最终状态。

### 数据页面

- 无 TableRef。
- 无 SharedPublication。
- Version 列表为空。
- 数据摘要失败。
- 只读状态。
- 来源 Run 已失效。

---

## 14. 操作安全设计

### 14.1 保存工作流

应展示：

```text
当前 Revision
当前 Definition Hash
草稿是否修改
最后一次 Validate 结果
保存后将创建新 Revision
```

### 14.2 取消运行

需要确认：

```text
确认取消当前运行？
已完成节点不会回滚。
```

### 14.3 关闭 Desktop

存在运行中工作流时，应警告：

```text
关闭 Desktop 可能同时停止本次 EngineHost，
并中断正在运行的工作流。
```

### 14.4 Token

设计必须支持：

- 默认掩码。
- 临时显示。
- 粘贴。
- 不在普通提示中显示真实值。
- 不出现在截图示例中。
- 不进入日志。

---

## 15. Gemini 与 Codex 的分工

### Gemini 负责

- 信息架构。
- 页面线框。
- `MainWindow.axaml` 拆分。
- MainWindow Shell。
- 页面级 UserControl。
- 组件级 UserControl。
- XAML 布局。
- ResourceDictionary。
- Style。
- 控件层级。
- 响应式和 DPI。
- 组件输入输出接口。
- 保持现有绑定契约。
- 保持现有本地化绑定契约。
- 新增用户可见文案时输出清单，等待 Codex 统一补本地化资源。

### Codex 负责

- 本地化实现。
- 本地化资源。
- Command 复核。
- Property 复核。
- ItemsSource 复核。
- SelectedItem 复核。
- ViewModel 接线。
- 业务逻辑。
- API 调用。
- 编译错误修复。
- 自动化测试。
- 功能回归。
- 生命周期复核。
- Token 安全复核。
- Revision 冲突复核。
- CI 和提交。

推荐协作方式：

```text
Gemini 完成一个小步
→ 输出功能映射和改动文件
→ Codex 复核并修正
→ 通过后再进入下一小步
```

不建议：

```text
Gemini 一次性重写全部 UI
→ Codex 最后集中修复
```

---

## 16. 明确禁止事项

未经单独批准，不得：

1. 负责中文化。
2. 修改本地化文件。
3. 重写 EngineHost。
4. 修改 API 路由。
5. 修改 Workflow Schema。
6. 修改 Revision 语义。
7. 修改 RuntimeEvent 协议。
8. 修改 AuditEvent 协议。
9. 修改 TableRef 或 SharedPublication 协议。
10. 将业务逻辑移入 code-behind。
11. 在 View 中直接发送 HTTP。
12. 删除现有 JSON 编辑入口。
13. 直接实现自由节点画布。
14. 删除现有诊断能力。
15. 用静态假数据替代真实绑定。
16. 创建无法运行的展示按钮。
17. 无映射地一次性重写全部 UI。
18. 随意修改依赖版本。
19. 同时拆 View 和 ViewModel。
20. 与 Codex 当前本地化工作发生冲突。
21. 新增硬编码中文或英文用户可见文本。
22. 在 XAML 中重新拼接已由 ViewModel 派生的列表显示文本。
23. 翻译协议状态、事件类型、审计决策、ID、版本号、序列号、时间戳或 JSON 字段名。

---

## 17. 每个阶段必须提供的内容

每一步开始前：

1. 目标。
2. 改动范围。
3. 不改内容。
4. 文件清单。
5. 功能映射。
6. 绑定影响。
7. Command 影响。
8. SelectedItem 影响。
9. 状态影响。
10. 回滚方式。

实现后：

1. 实际修改文件。
2. 迁移了哪些旧区域。
3. 保留了哪些绑定。
4. 新增了哪些组件。
5. 是否新增 code-behind。
6. 是否改变 Command。
7. 是否改变 ViewModel。
8. 是否存在未迁移功能。
9. 构建结果。
10. 需要 Codex 重点复核的内容。

---

## 18. 第一轮回复格式

第一轮只分析，不直接大规模改代码。

请按以下格式回复：

```text
1. 对当前项目和 UI 的理解
2. MainWindow 当前职责清单
3. 现有功能与绑定映射
4. 新版 Shell 结构
5. 页面拆分方案
6. 组件拆分方案
7. 组件输入输出接口
8. 第一阶段无损拆分计划
9. Codex 复核点
10. 风险和明确不做事项
```

第一轮不要直接删除或整体覆盖：

```text
MainWindow.axaml
MainWindowViewModel.cs
```

可以提出具体拆分补丁计划，但先等待评审。

---

## 19. 最终目标

Gemini 最终需要产出一套可以由 Codex 稳定复核和继续实现的 Avalonia UI 结构。

最终应做到：

```text
MainWindow 成为 Shell
页面职责清楚
导航逻辑清楚
组件边界清楚
绑定接口清楚
状态接口清楚
现有功能全部保留
业务逻辑不回归
Codex 可以逐步复核
```

最终用户操作路径应自然：

```text
启动应用
→ 查看连接状态
→ 选择或创建工作流
→ 查看和修改定义
→ 校验
→ 保存 Revision
→ 启动运行
→ 查看节点状态
→ 查看数据
→ 查看日志与审计
→ 处理失败或冲突
```

Gemini 可以参与 `MainWindow.axaml` 的重构和拆分，但必须采用“功能映射、无损拆分、Shell 化、逐页改版、Codex 复核”的渐进方式。
