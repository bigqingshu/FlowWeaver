# FlowWeaver RUNTIME-OPTIONS-1：配置字执行计划

> 文档状态：执行计划
> 前置依据：`FlowWeaver_RUNTIME-OPTIONS-0_配置字与运行反馈开关边界方案.md`
> 当前边界：只限制、降低、过滤已有日志、事件、进度、诊断上下文、限流、metrics、payload 和脱敏；不进入节点业务 `config`；节点已有反馈输出必须通过统一通道让配置字真实生效
> 不适用范围：权限审计、数据产物保存、节点业务参数、插件私有配置、完整动态 schema 编辑器

## 1. 执行目标

配置字作为工作流运行反馈控制层，目标是在任何工作流运行状态下降低无效反馈量，同时保留必要的诊断能力。

第一版完成后应具备：

* 工作流定义可保存 `runtime_options`。
* UI 可通过独立窗口编辑工作流整体配置字和节点覆盖。
* 运行前可合并 `system defaults + workflow + node override`。
* 主程序可按配置控制 runtime events、progress、log level 和诊断 payload。
* 节点已有的 progress、metrics、诊断输出可真实受到配置字限制。
* 旧工作流不带 `runtime_options` 时行为不破坏。

第一版明确不做：

* 不把配置字塞进节点业务 `config`。
* 不要求所有节点读取配置字。
* 不改节点业务 schema。
* 不引入新的权限、审计或数据保存模型。
* 不用配置字新增节点能力、改变核心计算、关闭当前表输出或控制副作用写入。
* 不用配置字自动清理业务输出表；当前运行数据清理先由用户手动处理。
* 不用配置字生成内存表预览快照；快照会创建新的 runtime sqlite 数据产物，第一版由节点业务配置或诊断运行入口控制。

## 2. 当前改动规模评估

| 维度 | 评估 | 说明 |
| --- | --- | --- |
| 后端模型 | 小到中 | 增加可选 `runtime_options` 模型和默认值 |
| UI 编辑 | 中 | 需要独立窗口、摘要入口、草稿写回 |
| 运行时接入 | 中 | 增加配置解析、合并、事件/进度过滤 |
| 节点协议 | 第一版不动 | 先不改 `NodeTaskModel`，避免扩大协议面 |
| 数据库迁移 | 预计不需要 | 工作流定义本身已作为 JSON 保存；如不改表结构，无需迁移 |
| 性能影响 | 低 | 小对象合并和条件判断；可减少事件/进度写入 |

## 3. 总体原则

1. 兼容优先：旧工作流不带配置字时，默认行为应等价于当前行为。
2. 低耦合优先：配置字独立于节点业务 `config`。
3. 后端为准：运行时配置模型、默认值和校验规则由后端定义，UI 只负责编辑和展示。
4. 分阶段生效：先支持保存和编辑，再接运行时行为。
5. 只做减法：配置字只限制、降低、过滤已有记录与反馈能力，不增加业务能力。
6. 真实生效：主程序和节点已有反馈通道都必须按配置字执行，不能只保存不生效。
7. 不生成数据产物：配置字不触发内存表预览快照、业务输出表、外部写入等数据产物行为。
8. 少承诺：第一版固定字段即可，不做动态扩展系统。

## 4. 阶段计划

### RUNTIME-OPTIONS-1A：后端模型与兼容解析

目标：工作流 JSON 正式承载 `runtime_options`，但不改变运行行为。

涉及文件预计：

```text
src/flowweaver/workflow/definition.py
tests/unit/test_workflow_process_dag.py
tests/integration/test_api.py
```

任务：

* 新增 `RuntimeOptionsModel`。
* 新增 `TelemetryRuntimeOptionsModel`。
* 新增 `DiagnosticsRuntimeOptionsModel`。
* `WorkflowDefinitionModel` 增加可选 `runtime_options`。
* 增加默认值和基础校验。
* 确认旧工作流缺失 `runtime_options` 可正常加载。

验收：

* 旧 workflow JSON 可通过 `WorkflowDefinitionModel.model_validate()`。
* 新 workflow JSON 可保存、读取、API 返回。
* 不改变 DAG 构建结果。
* 不改变现有工作流运行行为。

风险控制：

* 默认值应选择 current-compatible，而不是立刻降低反馈。
* 校验失败应给出清晰错误，不吞掉非法配置。

### RUNTIME-OPTIONS-1B：UI 解析模型与草稿 patcher

目标：Avalonia 能识别、读取和写回 `runtime_options`，但先不做完整窗口。

涉及文件预计：

```text
Avalonia_UI/Models/RuntimeOptionsDraft*.cs
Avalonia_UI/Models/WorkflowDefinitionDraftRuntimeOptionsPatcher.cs
Avalonia_UI.Tests/RuntimeOptionsDraftTests.cs
Avalonia_UI.Tests/WorkflowDefinitionDraftRuntimeOptionsPatcherTests.cs
```

任务：

* 新增 UI 侧 runtime options draft 模型。
* 新增从 `WorkflowDefinitionDraftJson` 读取配置字的 parser。
* 新增写回 `runtime_options.workflow` 的 patcher。
* 新增写回 `runtime_options.node_overrides` 的 patcher。
* 缺失配置字时返回默认 draft。

验收：

* 可从空配置生成默认配置字 draft。
* 可修改 workflow 配置字并写回 JSON。
* 可修改节点覆盖并只保存差异。
* 不破坏节点新增、删除、连接 patcher。

风险控制：

* patcher 只改 `runtime_options`，不重排 nodes/connections。
* 不把配置字写进任何节点 `config`。

### RUNTIME-OPTIONS-1C：UI 摘要入口与独立窗口

目标：工作流界面显示配置字摘要入口，并打开独立窗口编辑。

涉及文件预计：

```text
Avalonia_UI/ViewModels/MainWindowViewModel.cs
Avalonia_UI/Views/Components/Workflow/*
Avalonia_UI/Localization/zh-Hans.json
Avalonia_UI/Localization/en-US.json
Avalonia_UI.Tests/MainWindowViewModelWorkflowTests.cs
Avalonia_UI.Tests/MainWindowViewModelLocalizationTests.cs
```

任务：

* 在节点配置区下方增加“运行配置字”摘要入口。
* 摘要显示 profile、event level、progress 状态、节点覆盖数量。
* 独立窗口上方编辑工作流整体配置字。
* 独立窗口下方选择节点并编辑覆盖项。
* 支持恢复节点为工作流默认。
* 写回 workflow draft，并进入 dirty 状态。

验收：

* 不选择节点也能编辑工作流整体配置字。
* 选择节点后可编辑覆盖项。
* 节点覆盖只保存差异。
* 保存并重新加载后配置字保持一致。
* UI 不显示不存在的高级能力。

风险控制：

* 不把配置字字段铺满主界面，只显示摘要和入口。
* 独立窗口字段固定，避免第一版 UI 发散。

### RUNTIME-OPTIONS-1D：运行时 resolver

目标：运行开始时生成节点最终配置字，但先不改变事件行为。

涉及文件预计：

```text
src/flowweaver/workflow/runtime_options.py
src/flowweaver/workflow_process/main.py
tests/unit/test_runtime_options.py
tests/integration/test_workflow_process_main.py
```

任务：

* 新增 `resolve_runtime_options_for_node()`。
* 合并顺序固定为：system defaults -> workflow -> node override。
* 运行开始时解析工作流配置字。
* 调度节点时可取到该节点的 resolved runtime options。
* 第一版 resolver 不写入 `NodeTaskModel`。

验收：

* 无覆盖节点继承 workflow 配置字。
* 有覆盖节点只覆盖指定字段。
* resolver 不改变 node `config`。
* 运行行为仍与当前一致。

风险控制：

* resolver 结果作为 workflow process 内部上下文使用。
* 暂不新增任务表字段，避免任务协议扩大。

### RUNTIME-OPTIONS-1E：事件、进度与诊断控制

目标：配置字开始影响 runtime feedback。

涉及文件预计：

```text
src/flowweaver/workflow_process/main.py
src/flowweaver/workflow_process/node_tasks.py
src/flowweaver/engine/runtime_event_sink.py
src/flowweaver/engine/runtime_store.py
tests/integration/test_workflow_process_main.py
```

任务：

* `event_level=basic` 时只保留关键事件。
* `event_level=progress` 或 `verbose` 时保留进度事件。
* `progress_enabled=false` 时不记录或不推送节点进度细节。
* `event_rate_limit_per_second` 限制高频事件。
* `payload_byte_limit` 限制诊断 payload 大小。
* `include_metrics=false` 时过滤 metrics。
* `redact_columns` 和 `mask_policy` 用于事件/诊断 payload 脱敏。
* 节点已有 progress、metrics、diagnostics 输出必须走统一通道，不绕过配置字。

验收：

* 默认配置下与当前行为兼容。
* 后台快速配置下 runtime events 数量减少。
* diagnostic 配置下错误上下文更完整。
* payload 超限时被截断或拒绝，并保留明确提示。

风险控制：

* 关键生命周期事件不能被过滤掉。
* 过滤只作用于事件/进度/诊断，不影响节点状态更新。
* 所有过滤逻辑应集中，不散落到各节点实现中。
* 节点不得用配置字改变输出表、外部写入、文件改名或插件调用行为。
* 节点不得用配置字生成内存表预览快照。

### RUNTIME-OPTIONS-1F：运行详情只读展示

目标：运行详情页展示本次生效配置摘要，帮助排查“为什么这次反馈少/多”。

涉及文件预计：

```text
Avalonia_UI/ViewModels/MainWindowViewModel.cs
Avalonia_UI/Views/Pages/*
Avalonia_UI/Localization/*.json
Avalonia_UI.Tests/MainWindowViewModelWorkflowTests.cs
```

任务：

* 运行详情展示 profile、event level、progress 状态、diagnostics 状态。
* 只读展示，不在运行详情页编辑。
* 如果第一版后端未持久化 resolved snapshot，则展示 workflow revision 中配置字摘要。

验收：

* 用户能看到运行采用的配置字摘要。
* 不影响运行启动和取消。

风险控制：

* 不在运行记录里塞完整大 JSON。
* 不制造第二套编辑入口。

## 5. 延后项

以下能力明确延后：

| 项目 | 延后原因 |
| --- | --- |
| `NodeTaskModel.runtime_options` | 会扩大任务协议和持久化面，第一版主程序内部使用即可 |
| 运行请求临时覆盖 `run_override` | 需要 API 请求模型和 UI 运行弹窗配合 |
| 动态配置字 schema | 第一版固定字段更稳定 |
| 插件私有运行时配置 | 需要命名空间规则和插件协议 |
| 诊断保留清理任务 | 先只记录 `ttl_seconds` 建议；业务输出表清理当前由用户手动处理 |

## 6. 验证清单

后端验证：

```text
.\python312\python.exe -m pytest tests/unit/test_workflow_process_dag.py -q
.\python312\python.exe -m pytest tests/integration/test_workflow_process_main.py -q
.\python312\python.exe -m pytest tests/integration/test_api.py -q
```

UI 验证：

```text
dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj
```

手工验证：

| 场景 | 期望 |
| --- | --- |
| 打开旧工作流 | 未配置 `runtime_options` 也能正常加载 |
| 新建配置字 | 工作流草稿变 dirty |
| 节点覆盖 | 只保存与 workflow 默认不同的字段 |
| 后台快速配置运行 | 事件/进度反馈减少，节点状态仍正确 |
| diagnostic 配置运行 | 错误上下文和 metrics 按配置保留 |
| 保存再打开 | 配置字保持一致 |
| 节点已有反馈 | 节点 progress、metrics、diagnostics 不绕过配置字 |
| 业务输出数据 | runtime sqlite 输出表仍可由 UI 查询，配置字不自动删除 |

## 7. 回滚策略

| 阶段 | 回滚方式 |
| --- | --- |
| 后端模型 | 保留字段但默认忽略，旧工作流不受影响 |
| UI 编辑 | 隐藏入口，保留 JSON 字段不消费 |
| resolver | 不调用 resolver，运行行为回到当前 |
| 事件控制 | 使用 current-compatible 默认配置 |
| 诊断控制 | 关闭 metrics 和 verbose payload |

## 8. 最小可交付版本

最小可交付版本建议只包含：

1. `RuntimeOptionsModel`。
2. 工作流 JSON 可保存 `runtime_options`。
3. UI 独立窗口可编辑工作流整体配置字。
4. 节点覆盖可保存差异。
5. 不改变运行行为。

这个版本主要验证数据模型、UI 入口和保存链路。等用户确认 UI 位置和交互后，再接运行时 resolver 和反馈控制。
