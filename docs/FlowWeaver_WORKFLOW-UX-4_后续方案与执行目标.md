# FlowWeaver WORKFLOW-UX-4+：工作流编辑体验后续方案与执行目标

## 当前基线

基线日期：2026-07-05

当前已经完成：

- 新增节点面板已从右侧节点管理区移回中间列。
- 新增节点面板位于节点配置上方。
- 右侧工作流节点区继续承担节点列表、选择、复制、删除、批量删除、上移、下移和高级 JSON 入口。
- 本阶段尚未继续简化新增节点字段，也尚未把节点身份信息编辑迁入节点配置区。

## 执行原则

- 一个小阶段完成后，运行对应测试并使用中文提交信息提交。
- 默认不扩大后端协议，不提前实现后续阶段。
- UI 改动优先保持 Avalonia + .NET 10 + C# + MVVM 现有结构。
- 新发现的问题先记录到本文档的“后续方向判断”，再决定是否进入实现。
- 如果某阶段需要改后端、改保存语义或改变运行语义，先暂停做边界分析。

## 建议执行顺序

### WORKFLOW-UX-4.1：新增节点面板简化

目标功能：

- 新增节点面板只保留节点下拉、刷新、新增、关闭。
- 不再在新增面板暴露节点实例 ID、版本、显示名、配置 JSON 等细节输入。
- 新增节点仍复用现有自动生成 ID、版本、默认 config 的逻辑。

未完成说明：

- 当前新增面板仍显示较多字段。
- 这些字段后续应移动到节点配置区或高级 JSON 入口。

验收：

- 新增节点面板只呈现必要选择控件。
- 选择节点类型后仍可新增节点。
- 新增成功后选中新节点。
- 结构测试证明新增面板不再承载身份和 config 输入框。

### WORKFLOW-UX-4.2：节点配置区扩展

目标功能：

- 将选中节点的可编辑信息统一放到节点配置区。
- 覆盖节点显示名、config schema 表单、必要的只读身份信息。
- 节点实例 ID 第一版建议先只读展示，避免重命名导致连接引用同步问题。

未完成说明：

- 当前节点配置区主要编辑 config schema 字段。
- 节点身份字段和显示名还没有完整的普通表单入口。

验收：

- 选中新节点后，节点配置区能显示对应信息。
- config 字段编辑仍通过现有 patcher 修改 draft JSON。
- 节点实例 ID 不在本阶段直接重命名。

### WORKFLOW-UX-4.3：节点操作体验收口

目标功能：

- 复核复制、删除、批量删除、上移、下移的按钮状态、提示文案和错误边界。
- 让用户明确知道上移/下移当前只改变列表顺序，不改变依赖连接。

未完成说明：

- 当前操作可用，但部分提示仍偏工程化。
- 上移/下移还不等同于 DataFlowKit 式线性执行顺序调整。

验收：

- 无选择、revision 冲突、草稿忙碌等状态下按钮禁用符合预期。
- 删除节点会同步移除相关连接并显示摘要。
- 上移/下移文案不暗示执行依赖已改变。

### WORKFLOW-UX-5：线性工作流易用模式

目标功能：

- 面向 DataFlowKit 式顺序处理，评估并实现简单线性链路的自动维护。
- 插入节点、删除节点、上移/下移节点时，在安全条件下自动维护线性连接。

未完成说明：

- 当前连接在删除节点时会同步移除。
- 当前上移/下移不会自动改写 connections。
- 多入多出 DAG、复杂拓扑不应混入第一版线性模式。

验收：

- 明确线性模式适用条件。
- 非线性或复杂 DAG 场景不自动重排。
- 线性连接自动调整必须有测试覆盖。

建议拆分：

- `WORKFLOW-UX-5.0`：线性链路语义和拒绝边界分析，只写文档。
- `WORKFLOW-UX-5.1`：只读识别层，判断当前草稿是否满足单入口、单出口、单链路线性条件。
- `WORKFLOW-UX-5.2`：线性删除桥接，删除中间节点时在安全条件下连接前驱和后继。
- `WORKFLOW-UX-5.3`：线性上移/下移重排连接，只支持相邻节点交换。
- `WORKFLOW-UX-5.4`：线性模式 UI 提示与拒绝原因。
- `WORKFLOW-UX-5.5`：阶段验收复核。

### DATA-PREVIEW：真实数据预览体验增强

目标功能：

- 更稳定地展示选中节点输出、预览运行结果和完整运行最终输出。
- 补充空数据、失败保留上次结果、当前预览来源说明。

未完成说明：

- 当前已有数据预览基础。
- 用户仍需要更清楚地知道当前表格来自哪个 run、哪个 node、是否为上次结果。

验收：

- 表格常驻，不因刷新失败清空上次有效结果。
- 显示当前预览来源。
- 预览选中节点与完整运行结果有明确区分。

建议拆分：

- `DATA-PREVIEW-0`：现状复核与缺口确认，只写文档。
- `DATA-PREVIEW-1`：预览来源常驻说明，显示当前表格来自哪个 run、node、table。
- `DATA-PREVIEW-2`：预览选中节点与完整运行结果的状态文案复核。
- `DATA-PREVIEW-3`：空表、失败保留和成功全量替换验收复核。

### RUN-SAVE-UX：运行与保存体验收口

目标功能：

- 保存前校验提示、运行前未保存草稿提示、运行到选中节点和完整运行明确区分。
- 避免用户误以为后端运行的是当前未保存草稿。

未完成说明：

- 后端运行以已保存 revision 为准。
- UI 需要更明确地提示 dirty draft 与运行 revision 的关系。

验收：

- 草稿未保存时运行按钮有明确提示或保护。
- 预览运行和完整运行的状态文案区分清楚。
- 保存失败、revision 冲突和运行失败信息可读。

建议拆分：

- `RUN-SAVE-UX-0`：运行与保存当前边界复核，只写文档。
- `RUN-SAVE-UX-1`：dirty draft 运行保护，未保存草稿时禁用完整运行和预览运行。
- `RUN-SAVE-UX-2`：运行保护可见提示，说明后端运行的是已保存 revision。
- `RUN-SAVE-UX-3`：保存、revision 冲突、运行失败阶段验收复核。

### RELEASE-UX：发布与使用体验

目标功能：

- 完善便携包、启动器、用户手册、clean-room smoke。
- 保持 Python runtime、Avalonia desktop、manifest、SHA-256、许可证信息一致。

未完成说明：

- 发布 runtime、许可证、zip manifest、中文路径/空格路径验收仍可继续完善。
- 用户手册需要继续明确关闭 Desktop 对运行中工作流的影响。

验收：

- clean-room smoke 覆盖仓库外路径、空格路径、中文路径。
- manifest 与版本信息一致。
- 用户手册覆盖启动、连接、运行、退出、故障排查。

## 后续方向判断

工作阶段如发现新问题，先追加到本节，再决定是否进入实现：

- 节点实例 ID 编辑不能直接作为普通输入暴露；如果后续支持重命名，需要同步处理 connections 引用、选中状态、批量选择状态和保存前校验。
- 线性识别层需要把“单节点但存在自环连接”视为非法拓扑，不能因为节点数为 1 就直接通过。
- 线性删除桥接第一版只接入单节点删除；批量删除仍保持“删除节点并移除相关连接”，如需批量桥接需要单独定义连续区间和非连续选择的语义。
- 线性上移/下移第一版只支持中间相邻节点交换；移动源节点、尾节点或端口无法推导时，应回退为只调整节点列表顺序。

## 阶段执行记录

### WORKFLOW-UX-4.1：新增节点面板简化

状态：已完成。

完成内容：

- 新增节点面板保留节点类型下拉、刷新、新增、关闭。
- 移除新增节点面板中的节点实例 ID、节点版本、显示名、配置 JSON 输入。
- 保持现有 ViewModel 自动生成节点实例 ID、版本和默认 config 的逻辑不变。
- 新增节点区域仍位于节点配置上方。

测试结果：

- `dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj -p:UseAppHost=false --filter "FullyQualifiedName~WorkflowSummaryViewStructureTests|FullyQualifiedName~WorkflowSummaryViewHeadlessSmokeTests|FullyQualifiedName~MainWindowViewModelWorkflowTests"`：92 passed。
- `dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj -p:UseAppHost=false`：326 passed。

### WORKFLOW-UX-4.2a：节点配置区只读身份信息

状态：已完成。

完成内容：

- 在节点配置区顶部展示当前选中节点的节点实例 ID、节点类型、节点版本和显示名。
- 节点实例 ID 第一版保持只读，不引入重命名。
- 保持现有 config schema 表单和应用配置命令不变。

测试结果：

- `dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj -p:UseAppHost=false --filter "FullyQualifiedName~WorkflowSummaryViewStructureTests|FullyQualifiedName~MainWindowViewModelWorkflowTests"`：91 passed。
- `dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj -p:UseAppHost=false`：326 passed。

### WORKFLOW-UX-4.2b：节点显示名称编辑

状态：已完成。

完成内容：

- 在节点配置区提供显示名称输入和“应用名称”按钮。
- 新增 `WorkflowDefinitionDraftNodePatcher.UpdateDisplayName(...)`，只更新或清空选中节点的 `display_name`。
- ViewModel 接入显示名称草稿状态和应用命令。
- 节点实例 ID、节点类型、节点版本仍保持只读。

测试结果：

- `dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj -p:UseAppHost=false --filter "FullyQualifiedName~WorkflowDefinitionDraftNodePatcherTests|FullyQualifiedName~MainWindowViewModelWorkflowTests|FullyQualifiedName~WorkflowSummaryViewStructureTests|FullyQualifiedName~MainWindowViewModelLocalizationTests"`：144 passed。
- `dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj -p:UseAppHost=false`：330 passed。

### WORKFLOW-UX-4.3a：节点操作禁用原因与移动语义说明

状态：已完成。

完成内容：

- 为复制、删除、删除已选、列表上移、列表下移补充禁用原因文本。
- 右侧节点操作按钮使用现有 `Panel + ToolTip.Tip` 模式展示禁用原因。
- 节点操作区补充说明：上移/下移只调整草稿节点列表顺序，不改变连接和执行依赖。
- 保持节点操作后端语义不变，不引入线性连接自动重排。

测试结果：

- `dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj -p:UseAppHost=false --filter "FullyQualifiedName~MainWindowViewModelWorkflowTests|FullyQualifiedName~WorkflowSummaryViewStructureTests|FullyQualifiedName~MainWindowViewModelLocalizationTests"`：115 passed。
- `dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj -p:UseAppHost=false`：331 passed。

### WORKFLOW-UX-5.0：线性链路语义和拒绝边界分析

状态：已完成。

边界结论：

- 线性模式只处理单入口、单出口、每个中间节点最多一个前驱且最多一个后继的简单链路。
- 自动重排只允许在所有相关端口可确定、连接唯一、且不会丢失旁路连接的情况下发生。
- 多入、多出、分支、汇合、旁路连接、缺失端口、重复连接 ID、未知节点引用都必须拒绝自动重排。
- 当前 `AddNode` 已有“单下游连接 + 单输入端口 + 单输出端口”的最小自动插入能力，可作为线性模式的既有基础。
- 当前 `DeleteNode` / `DeleteNodes` 只同步移除相关连接，不会自动桥接前驱和后继。
- 当前 `MoveNode` 只调整 `nodes` 数组顺序，明确不改变 `connections`。

建议下一步：

- 先实现只读识别层 `WORKFLOW-UX-5.1`，只返回“是否线性、节点顺序、拒绝原因”，不改写草稿。
- 识别层通过测试后，再决定是否进入删除桥接和相邻上移/下移重排。
- UI 在识别层完成前继续保持 4.3a 的提示：上移/下移只调整列表顺序，不改变连接和执行依赖。

测试结果：

- 文档分析小步，未改代码，未运行测试。

### WORKFLOW-UX-5.1：线性链路只读识别层

状态：已完成。

完成内容：

- 新增 `WorkflowDefinitionLinearChainAnalyzer`，只读判断草稿是否为单入口、单出口、单链路的线性结构。
- 新增 `WorkflowDefinitionLinearChainAnalysis`，返回是否线性、线性节点顺序和拒绝原因。
- 覆盖简单线性链、单节点无连接、分支、汇合、断链、未知节点引用、重复连接 ID、自环和无效草稿结构。
- 本小步不改写 draft JSON，不接入 UI，不改变删除、上移、下移的现有语义。

测试结果：

- `dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj -p:UseAppHost=false --filter "FullyQualifiedName~WorkflowDefinitionLinearChainAnalyzerTests"`：9 passed。
- `dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj -p:UseAppHost=false`：340 passed。

### WORKFLOW-UX-5.2：线性删除桥接

状态：已完成。

完成内容：

- 新增 `DeleteNodeWithLinearBridge(...)`，保留原 `DeleteNode(...)` 默认删除语义不变。
- 单节点删除命令改用线性桥接方法：在线性链路、中间节点有唯一前驱和唯一后继、端口可确定时，删除目标节点并新增前驱到后继的桥接连接。
- 非线性草稿、旁路连接、端口缺失、源节点或尾节点删除仍回退为移除相关连接，不自动重排。
- 批量删除暂不桥接，避免连续区间和非连续选择语义提前扩大。
- 补充删除桥接的中英文提示文案和连接明细。

测试结果：

- `dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj -p:UseAppHost=false --filter "FullyQualifiedName~WorkflowDefinitionDraftNodePatcherTests|FullyQualifiedName~MainWindowViewModelWorkflowTests|FullyQualifiedName~WorkflowDefinitionLinearChainAnalyzerTests|FullyQualifiedName~JsonLocalizationServiceTests"`：127 passed。
- `dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj -p:UseAppHost=false`：343 passed。

### WORKFLOW-UX-5.3：线性上移/下移相邻重排

状态：已完成。

完成内容：

- 新增 `MoveNodeWithLinearRewire(...)`，保留原 `MoveNode(...)` 默认移动语义不变。
- 上移/下移命令改用线性重排方法：旧草稿为线性链路、移动为相邻交换、且新顺序所有相邻端口均可推导时，重建线性 connections。
- 移动源节点、尾节点、端口缺失或非线性草稿时，回退为只调整节点列表顺序，connections 不改变。
- 更新移动成功文案和连接重排明细；同步修正节点操作区的移动语义说明。

测试结果：

- `dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj -p:UseAppHost=false --filter "FullyQualifiedName~WorkflowDefinitionDraftNodePatcherTests|FullyQualifiedName~MainWindowViewModelWorkflowTests|FullyQualifiedName~MainWindowViewModelLocalizationTests|FullyQualifiedName~WorkflowDefinitionLinearChainAnalyzerTests|FullyQualifiedName~JsonLocalizationServiceTests"`：152 passed。
- `dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj -p:UseAppHost=false`：346 passed。

### WORKFLOW-UX-5.4：线性模式 UI 提示与拒绝原因

状态：已完成。

完成内容：

- 新增 `WorkflowLinearChainStatusText`，在节点操作区显示当前草稿的线性链路识别状态。
- 已加载线性草稿时显示可自动维护连接的节点数量提示。
- 非线性草稿显示本地化拒绝原因，例如分支、汇合、断链、环路、非单入口单出口等。
- 该状态只读展示，不改变按钮可用性、保存语义或运行语义。

测试结果：

- `dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj -p:UseAppHost=false --filter "FullyQualifiedName~MainWindowViewModelWorkflowTests|FullyQualifiedName~MainWindowViewModelLocalizationTests|FullyQualifiedName~JsonLocalizationServiceTests|FullyQualifiedName~WorkflowSummaryViewStructureTests|FullyQualifiedName~WorkflowDefinitionLinearChainAnalyzerTests"`：133 passed。
- `dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj -p:UseAppHost=false`：347 passed。

### WORKFLOW-UX-5.5：线性工作流易用模式阶段验收复核

状态：已完成。

验收结论：

- 已固化线性链路边界：单入口、单出口、单链路；分支、汇合、断链、环路、旁路和未知引用均不进入自动维护。
- 已实现只读识别层，可返回线性节点顺序和拒绝原因。
- 已实现单节点删除桥接：仅在线性链路中删除中间节点时，自动连接前驱和后继。
- 已实现相邻中间节点移动重排：仅在线性链路、相邻交换、端口可推导时重建 connections。
- 已补 UI 只读状态提示，让用户能看到当前草稿是否支持线性自动维护。
- 原有非线性操作保持保守：复杂 DAG、源/尾节点移动、端口不可推导、批量删除都不会自动改写连接。

当前明确保留：

- 批量删除桥接未实现；连续区间和非连续选择语义需要单独设计。
- 节点实例 ID 重命名未实现；如支持，需要同步更新 connections 引用。
- 复杂 DAG 的图形化连接编辑、拖拽编排和多端口 schema 表单不在本阶段范围内。
- 运行到选中节点、数据预览来源说明和保存/运行 dirty draft 保护进入后续 DATA-PREVIEW 与 RUN-SAVE-UX 阶段。

测试结果：

- `dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj -p:UseAppHost=false`：347 passed。

### DATA-PREVIEW-0：现状复核与缺口确认

状态：已完成。

复核结论：

- 当前已经具备数据预览基础表格，`WorkflowDataPreviewView` 独立显示在工作流页面下方。
- 当前已有“预览选中节点”和“运行”入口，预览选中节点会启动到目标节点的预览运行，完整运行后会尝试选择最新可读输出节点并刷新数据预览。
- 当前已有失败保留上次有效表格的测试覆盖：刷新失败、缺少输出表和预览启动失败不会清空上一份有效数据。
- 当前缺口是“当前表格来自哪个 run、哪个 node、哪个 table”还没有常驻来源行，只能从状态消息间接判断。

建议下一步：

- 进入 `DATA-PREVIEW-1`，新增只读来源文本，不改变后端接口、不改变预览和运行语义。

测试结果：

- 现状复核小步，未改代码；本轮进入 DATA-PREVIEW 前已执行 `dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj -p:UseAppHost=false`：347 passed。

### DATA-PREVIEW-1：预览来源常驻说明

状态：已完成。

完成内容：

- 新增数据预览来源派生文本，展示上一次成功加载的 run、node 和 logical table。
- 成功加载预览数据时更新来源；刷新失败、缺少输出表或选择变化时不清空上一份来源，与表格保留策略一致。
- 数据预览窗口新增来源行；未成功加载过预览时显示“尚未加载数据预览”。
- 补充中英文文案和结构测试。

测试结果：

- `dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj -p:UseAppHost=false --filter "FullyQualifiedName~MainWindowViewModelDataTests|FullyQualifiedName~MainWindowViewModelLocalizationTests|FullyQualifiedName~JsonLocalizationServiceTests|FullyQualifiedName~WorkflowSummaryViewStructureTests"`：52 passed。
- `dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj -p:UseAppHost=false`：347 passed。

### DATA-PREVIEW-2：预览运行与完整运行来源区分

状态：已完成。

完成内容：

- `WorkflowRunListItemViewModel` 保留后端 `run_mode` 和 `target_node_instance_id`。
- 数据预览来源行区分完整运行和预览运行：完整运行显示 `full run`，预览到节点显示 `preview run ... to node ...`。
- 缺省或空 run mode 继续按完整运行处理，兼容已有手动刷新和旧响应。
- 补充中英文来源格式和完整运行、预览运行断言。

测试结果：

- `dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj -p:UseAppHost=false --filter "FullyQualifiedName~MainWindowViewModelDataTests|FullyQualifiedName~MainWindowViewModelWorkflowTests|FullyQualifiedName~JsonLocalizationServiceTests|FullyQualifiedName~MainWindowViewModelLocalizationTests|FullyQualifiedName~WorkflowSummaryViewStructureTests"`：134 passed。
- `dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj -p:UseAppHost=false`：347 passed。

### DATA-PREVIEW-3：空表、失败保留和成功替换验收复核

状态：已完成。

验收结论：

- 空表场景保留列头并显示 0 行，不误报错误。
- 缺少输出表、刷新失败和预览启动失败不会清空上一份有效表格。
- 后续成功刷新会全量替换列、行和来源信息。
- 预览选中节点与完整运行都会在运行完成后尝试刷新数据预览。
- 当前不新增分页、排序、筛选和大表虚拟化，这些进入后续数据体验阶段再设计。

测试结果：

- `dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj -p:UseAppHost=false --filter "FullyQualifiedName~MainWindowViewModelDataTests|FullyQualifiedName~MainWindowViewModelWorkflowTests"`：92 passed。
- `dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj -p:UseAppHost=false`：347 passed。

### RUN-SAVE-UX-0：运行与保存当前边界复核

状态：已完成。

复核结论：

- 保存命令当前已依赖 `IsWorkflowDefinitionDraftDirty`、`WorkflowDefinitionDetail`、保存忙碌状态和 revision conflict 状态。
- 保存失败、revision conflict 和保存后刷新定义已有基础测试覆盖。
- 完整运行和预览运行当前仍未把 dirty draft 作为禁用条件，存在用户误以为“运行的是未保存草稿”的风险。
- 数据预览来源已能区分完整运行和预览运行，但还需要运行前保护和可见提示说明后端运行的是已保存 revision。

建议下一步：

- 进入 `RUN-SAVE-UX-1`，先做最小保护：dirty draft 或 revision conflict 时禁用完整运行和预览运行，不改变后端接口。

测试结果：

- 现状复核小步，未改代码；进入本阶段前已执行 `dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj -p:UseAppHost=false`：347 passed。

### RUN-SAVE-UX-1：dirty draft 运行保护

状态：已完成。

完成内容：

- 完整运行命令在工作流草稿 dirty 或 revision conflict 时禁用。
- 预览选中节点命令在工作流草稿 dirty 或 revision conflict 时禁用。
- dirty/conflict 状态变化时同步刷新运行和预览命令可用性。
- 不改变保存接口、不改变后端运行接口、不自动保存草稿。

测试结果：

- `dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj -p:UseAppHost=false --filter "FullyQualifiedName~MainWindowViewModelWorkflowTests"`：83 passed。
- `dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj -p:UseAppHost=false`：348 passed。
