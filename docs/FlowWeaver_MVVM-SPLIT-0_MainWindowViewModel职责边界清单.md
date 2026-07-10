# FlowWeaver MVVM-SPLIT-0：MainWindowViewModel 职责边界清单

## 阶段定位

本阶段只做 `MainWindowViewModel` 的职责边界确认，不改 Avalonia 代码、不迁移 XAML 绑定、不引入新的子 ViewModel。

当前目标是先把 `MainWindowViewModel` 中已经形成的页面职责、共享状态和高耦合点列清楚，为后续小步拆分提供依据。

## 当前结论

`MainWindowViewModel` 当前承担了三类职责：

1. 应用级组合根：创建 API client、设置存储、本地化服务、主题语言状态和全局命令刷新。
2. 页面级 ViewModel：工作流、运行监控、数据、日志、设置、通知、Shell 导航等页面状态都挂在同一个根 VM 上。
3. 编辑器级业务状态：工作流定义草稿、节点目录、节点配置、运行配置、数据预览工作台等复杂交互逻辑也集中在同一个根 VM 上。

这使得它适合先做“内部减脂”，不适合立刻整体拆成多个独立 DataContext。

## 文件职责现状

| 文件 | 当前主要职责 | 拆分压力 | 建议优先级 |
| --- | --- | --- | --- |
| `MainWindowViewModel.cs` | 构造依赖、主题语言初始化、全局命令状态刷新 | 中 | 中 |
| `MainWindowViewModel.Connection.cs` | EngineHost 连接、token、WebSocket 事件流、连接配置持久化 | 中 | 中 |
| `MainWindowViewModel.Workflow.cs` | 工作流列表、创建、导入、导出、删除、运行、预览运行入口 | 中 | 中 |
| `MainWindowViewModel.WorkflowDraft.cs` | 工作流详情、草稿 JSON、节点目录、节点操作、连接、节点配置、校验保存 | 高 | 高 |
| `MainWindowViewModel.RuntimeOptions.cs` | workflow/node 运行配置编辑、JSON 高级入口、运行配置摘要 | 高 | 高 |
| `MainWindowViewModel.DataPreview.cs` | 表引用、节点预览、数据预览工作台、分页、复制解析、保存入口 | 高 | 高 |
| `MainWindowViewModel.Runs.cs` | run 列表、node run 列表、取消 run、运行监控状态 | 低 | 低 |
| `MainWindowViewModel.Logs.cs` | RuntimeEvent 查询、筛选、分页限制 | 低 | 低 |
| `MainWindowViewModel.SharedPublications.cs` | 共享发布与版本只读查询 | 低 | 低 |
| `MainWindowViewModel.Notifications.cs` | 通知浮层、最近事件 | 低 | 低 |
| `MainWindowViewModel.Localization.cs` | 文案刷新、语言切换、本地化派生文本刷新 | 中 | 中 |
| `MainWindowViewModel.Shell.cs` | Shell 导航项、当前页面 key、页面选择状态 | 低 | 低 |

## 建议职责边界

### Root / Composition

保留在根 `MainWindowViewModel`：

- 构造函数和依赖注入入口。
- `CanUseEngineActions` 等跨页面共享条件。
- Shell 当前页面状态。
- 应用级主题、语言、连接状态。
- 全局命令状态刷新协调。

后续可以收口的方向：

- 将 `NotifyEngineActionStateChanged` 拆成各领域自己的 `Notify...ActionStateChanged`，根 VM 只负责调用协调。

### Connection

保留为独立 partial，暂不急拆子 VM：

- BaseUrl、Token、连接状态。
- health check。
- WebSocket 连接、断开和重连消息。
- 连接配置读取与保存。

可抽出的纯逻辑：

- BaseUrl/token 配置校验。
- WebSocket URL 脱敏显示。

### Workflow List / Management

建议边界：

- 工作流列表加载。
- 创建模板工作流。
- 导入、导出、删除工作流。
- 运行整个工作流。
- 预览选中节点入口。

暂不和 workflow draft 编辑器合并。列表管理属于 workflow shell，草稿编辑属于 workflow editor。

### Workflow Draft Editor

这是第一优先级拆分区。

建议先按 partial 文件级拆分，不改外部绑定名：

- `WorkflowDraft.Document`：加载详情、revision、草稿 JSON、dirty、校验、保存。
- `WorkflowDraft.Catalog`：节点定义加载、缓存、节点定义显示文本、schema 解析缓存。
- `WorkflowDraft.Nodes`：新增、复制、删除、批量删除、上移、下移、选中节点。
- `WorkflowDraft.NodeConfig`：选中节点配置草稿、配置字段、应用配置。
- `WorkflowDraft.Connections`：连接自动维护、连接高级显示、连接结构同步。
- `WorkflowDraft.Parse`：草稿结构解析、线性链分析、runtime options 读取缓存调用。

后续再考虑抽内部状态对象：

- `WorkflowEditorState`
- `WorkflowNodeCatalogState`
- `WorkflowNodeSelectionState`
- `WorkflowDraftConnectionState`

不建议当前立刻做：

- 不建议直接让 `WorkflowEditorView` 绑定新的 `WorkflowEditorViewModel`。
- 不建议一次性迁移所有 workflow XAML 的 DataContext。

### Runtime Options Editor

建议边界：

- workflow 级运行配置草稿。
- node override 运行配置草稿。
- JSON 高级编辑草稿。
- 摘要文本和校验错误。

可先抽纯模型/状态：

- `RuntimeOptionsEditorState`
- `RuntimeOptionsDraftStateMapper`
- `RuntimeOptionsJsonDraftSynchronizer`

暂不改 `RuntimeOptionsEditorWindow` 的 DataContext。

### Data Preview / Workbench

建议拆成两个语义区：

1. 工作流节点数据预览：由工作流页触发，展示选中节点的输出表。
2. 数据预览工作台：左侧选择处理状态，右侧选择表，查看、搜索、复制、解析、保存。

可先抽纯模型/状态：

- `DataPreviewStateSelection`
- `DataPreviewTableSelection`
- `DataPreviewWorkbenchState`
- `DataPreviewTableGridBuilder`

暂不改页面绑定。

### Run Monitor / Logs / Shared Publications

当前压力相对较低，建议暂缓拆分。

后续可以在 View 层继续组件化，但 VM 层只需保持边界清晰：

- Runs：run/node run 监控和取消。
- Logs：RuntimeEvent 只读查询与筛选。
- Shared Publications：共享发布只读查询。

## 主要耦合点

| 耦合点 | 当前影响 | 建议处理方式 |
| --- | --- | --- |
| `CanUseEngineActions` | 多页面命令统一依赖连接状态 | 保留根状态，拆分领域级刷新方法 |
| `SelectedWorkflow` | 工作流列表、详情、运行、预览、数据预览都依赖它 | 保留根可见属性，内部拆 workflow/editor 状态 |
| `SelectedWorkflowDefinitionNode` | 节点配置、运行配置、数据预览、节点操作共用 | 后续抽 `WorkflowNodeSelectionState` |
| `WorkflowDefinitionDraftJson` | 草稿解析、保存、节点列表、连接、运行配置都依赖 | 优先抽 parse cache 和 document state |
| `NodeDefinitions` | 新增节点、配置 schema、节点显示文本都依赖 | 抽 `WorkflowNodeCatalogState` 或 catalog cache |
| `NotifyEngineActionStateChanged` | 根 VM 知道太多命令 | 分阶段改成领域级 notify 方法 |
| 本地化刷新 | 多模块派生文本都需要刷新 | 保留统一入口，拆各领域 `Refresh...Text` 方法 |

## 后续拆分顺序建议

### MVVM-SPLIT-1：纯逻辑抽取

优先抽不影响 XAML 绑定的模型/服务：

- 草稿解析缓存。
- 节点目录查找与 schema 解析缓存。
- runtime options 草稿映射。
- 数据预览表格构建。

验收标准：

- XAML 绑定名不变。
- 现有 UI 测试继续通过。
- MainWindowViewModel 行为无变化。

### MVVM-SPLIT-2：WorkflowDraft partial 文件级拆分

只移动代码，不改类名、不改属性名、不改命令名。

验收标准：

- `WorkflowDraft.cs` 不再承载所有 workflow editor 逻辑。
- 节点、连接、配置、目录、保存各自有明确文件。
- 测试覆盖保持不变或只做路径级补充。

### MVVM-SPLIT-3：内部 State 对象

引入内部状态对象，但继续由根 VM 暴露旧绑定属性。

验收标准：

- XAML 仍无需迁移。
- 状态对象有独立单元测试。
- 根 VM 逻辑明显减少。

### MVVM-SPLIT-4：页面子 ViewModel 迁移评估

只有当前三步稳定后，再评估是否迁移 XAML DataContext。

候选子 VM：

- `WorkflowListViewModel`
- `WorkflowEditorViewModel`
- `WorkflowNodeListViewModel`
- `DataPreviewWorkbenchViewModel`
- `RunMonitorViewModel`
- `SettingsViewModel`

验收标准：

- 单页迁移、单页验收。
- 不跨页面批量迁移。
- 保留根 VM 作为应用级 composition root。

## 明确暂不做

- 不在本阶段新增子 ViewModel。
- 不改任何 `.axaml` 的 `x:DataType`。
- 不改命令名、属性名和绑定路径。
- 不调整后端 API。
- 不和当前节点、数据预览、运行配置功能改造混在一个提交里。

## 本阶段验收口径

- 已形成 `MainWindowViewModel` 当前职责清单。
- 已明确高优先级拆分区域：`WorkflowDraft`、`DataPreview`、`RuntimeOptions`。
- 已明确最稳拆分顺序：纯逻辑抽取、partial 文件级拆分、内部 state、最后评估子 VM。
- 未进行代码实现，避免影响当前 UI 行为。

## 实施验收更新（2026-07-10）

### MVVM-SPLIT-1：纯逻辑抽取

已完成并具有独立测试：

- `WorkflowDefinitionDraftParseCache`：统一缓存草稿结构、线性链分析和 runtime options 读取结果。
- `NodeDefinitionCatalogCacheState`：统一节点目录命中、schema catalog key 和 lookup key 边界。
- `RuntimeOptionsDraftStateMapper`：统一 workflow/node runtime options 草稿字段映射。
- `DataPreviewTableGridBuilder`：统一表格构建、搜索、TSV 和复制解析逻辑。

### MVVM-SPLIT-2：WorkflowDraft partial 文件级拆分

已完成当前阶段收口：

- `WorkflowDraft` 已按 Document、Catalog、Nodes、NodeConfig、Connections、Parse、Persistence 和 Validation 等职责拆分。
- `DataPreview` 已按 NodePreview、Selection、TableRefs、Workbench 和 Presentation 等职责拆分。
- `RuntimeOptions` 已按 Json、State、Structured、Validation 和 Presentation 等职责拆分。
- XAML 绑定名、命令名、公开属性名和页面 `x:DataType` 均未迁移。

### MVVM-SPLIT-3：内部 State 对象

已完成当前最小内部状态边界：

- `WorkflowNodeSelectionState`：保存并恢复节点列表刷新前后的选择。
- `WorkflowDefinitionDraftDocumentState`：保存草稿原始基线并统一 dirty 判断。
- `DataPreviewSelectionState`：保存并恢复数据预览 state/table 两级选择。
- `DataPreviewWorkbenchGridState`：统一工作台列、原始/可编辑行、dirty、还原和分页状态。

上述 state 均不改变根 VM 的公开绑定属性，并具有独立单元测试；根 VM 继续作为 compatibility facade。

### MVVM-SPLIT-4：页面子 ViewModel 迁移评估

评估结论：本轮不迁移页面 DataContext。

当前所有内置页面仍以 `MainWindowViewModel` 为 `x:DataType`。最小候选为 `LogsPage`，但其现有逻辑仍共同依赖：

- EngineHost API client 和连接设置构建。
- 应用级取消令牌与连接可用状态。
- 本地化格式化和 API 错误格式化。
- 根 VM 的全局命令状态刷新入口。

直接迁移会要求同时新增共享 EngineHost session/context、页面级本地化适配和 XAML DataContext 转发，超过本轮“先内部减脂、最后只评估子 VM”的边界。

后续若单独进入 MVVM-SPLIT-4 实施，建议先建立只读的应用会话上下文，再以 `LogsPageViewModel` 为首个单页迁移候选；不得跨页面批量迁移。

### 当前验收结果

- 仅修改 Avalonia 前端及本职责文档，未修改后端 API 或运行时实现。
- 未修改任何 `.axaml` 的 `x:DataType`、命令名、属性名和绑定路径。
- `MainWindowViewModel` 已完成纯逻辑抽取、领域 partial 拆分和首批内部 state 接入。
- Avalonia 完整测试：`464 passed, 0 failed`。
- 现有三条 `MSTEST0037` 为既有结构测试建议，不影响阶段验收。
