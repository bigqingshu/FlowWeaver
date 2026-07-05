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
