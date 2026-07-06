# FlowWeaver UI 交互状态矩阵、ActionState 与前后端接口实施清单

> 审核状态（2026-07-05）：部分已实现 / 前端派生路线落地
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：后端事实契约、IEngineHostApiClient 调用边界、命令 CanExecute、禁用原因、旧请求丢弃和本地化状态文案已在前端主线落地。
> 未实现：没有实现后端返回按钮定义，也没有抽出独立 ActionState 后端协议。
> 原因：这符合文档原则：后端只提供事实，前端根据事实和本地状态派生按钮可用性。

> 本清单用于 G.7 之后的桌面端交互增强和前后端协作。Codex 负责 Python EngineHost、API/DTO/状态语义、接口契约、本地化资源和最终复核；Gemini 负责 Avalonia 前端页面、组件、XAML、客户端 ActionState 与必要的 C# ViewModel 接线。后端只提供事实，不返回按钮定义；前端根据已冻结的接口契约计算按钮可见性、可用性和禁用原因。

## 1. 当前基线

- UI 技术栈保持 `Avalonia_UI/` 下的 Avalonia + .NET 10.0 + C# + MVVM。
- 后端通信继续使用 HTTP + WebSocket。
- 当前按钮大多已经绑定到 `MainWindowViewModel` 的 `RelayCommand` 和 `CanExecute`。
- 当前 UI 已具备本地状态驱动：
  - `SelectedWorkflow` 控制 run、detail、draft 保存入口。
  - `SelectedRun` 控制 cancel、node runs、table refs 入口。
  - `IsWorkflowBusy`、`IsRunBusy`、`IsNodeRunBusy`、`IsDataBusy`、`IsLogBusy` 控制加载进度和命令可用性。
  - 错误区通过 `Has*Error` 控制显示。
- 后端 DTO 已暴露足够的事实字段：
  - `NodeDefinitionDto.ui_visibility`
  - `WorkflowDefinitionDto.status`
  - `WorkflowRunDto.status`、`completion_reason`
  - `NodeRunDto.status`、`progress`、`current_stage`、`last_heartbeat`
  - `TableRefDto.lifecycle_status`、`capabilities`
  - `SharedPublicationDto.status`、`members`
  - `AuditEventDto.decision`


## 2. 职责分工与协作流程

### 2.1 Codex 负责范围

Codex 负责以下内容：

- Python EngineHost 后端实现。
- HTTP API 与 WebSocket 协议。
- DTO 字段、空值语义、状态枚举和错误码。
- workflow、run、node run、TableRef、SharedPublication 的真实业务语义。
- 哪些状态允许取消、运行、保存、读取等接口事实。
- 后端接口契约文档的编写和维护。
- `en-US.json`、`zh-Hans.json` 及中文化一致性。
- 后端测试、接口测试和必要的 C# 客户端契约测试。
- Gemini 完成前端修改后的最终代码复核。
- 最终 build、test、diff、功能回归和提交验收。

Codex 不应让后端直接返回按钮定义。后端只返回：

- 当前事实状态。
- 权限与能力。
- 可识别的错误码。
- 资源版本、Revision、Hash。
- 必要的时间戳和序号。

### 2.2 Gemini 负责范围

Gemini 负责以下前端内容：

- Avalonia 页面和组件。
- XAML 布局、样式、状态色标和轻量动画。
- `IsEnabled`、`IsVisible`、ToolTip、状态说明的绑定。
- 客户端 ActionState 派生属性。
- 与 ActionState 有关的 C# ViewModel 接线。
- `PropertyChanged`、`NotifyCanExecuteChanged` 和选中项状态订阅。
- 页面级异步请求取消、旧结果丢弃和 UI 上下文一致性。
- 禁用原因、空状态、错误状态和确认交互。
- 按 Codex 提供的接口契约消费 DTO，不自行猜测后端语义。

Gemini不得：

- 修改 Python 后端。
- 自行增加或重命名 API 字段。
- 自行定义后端状态含义。
- 因界面需要而改变 workflow、run、revision 或权限语义。
- 绕过 Command 的 `CanExecute`。
- 把业务判断写入 View code-behind。

### 2.3 完成后的复核流程

每个小步采用以下流程：

```text
Codex 冻结或补充后端接口契约
→ Gemini 按契约实现前端
→ Gemini 提交修改文件、绑定清单和测试结果
→ Codex 复核前端与后端语义是否一致
→ Codex 运行 build/test/功能回归
→ 通过后进入下一小步
```

即使 Gemini 已完成前端代码，也必须由 Codex 复核：

- 是否使用了真实字段。
- 是否遗漏 Command 最终保护。
- 是否存在状态不同步。
- 是否存在异步旧结果覆盖。
- 是否泄露 Token。
- 是否破坏中文化。
- 是否与现有 API 和生命周期冲突。

## 3. 前后端事实接口契约

### 3.1 契约原则

后端接口契约必须由 Codex 编写和维护，建议单独形成：

```text
docs/FlowWeaver_UI_BackendFactsContract.md
```

每个供 UI 使用的接口至少写清楚：

| 项目 | 必须说明 |
| --- | --- |
| API | 方法、路径、鉴权方式 |
| 请求 | 参数、空值、默认值、范围 |
| 响应 | DTO 字段、类型、空值、时间格式 |
| 状态 | 已知枚举、终态、过渡态、未知状态策略 |
| 权限 | capabilities、decision 或其他权限事实 |
| 错误 | HTTP 状态码、稳定错误码、可重试性 |
| 并发 | Revision、Hash、Sequence、覆盖保护 |
| 时序 | WebSocket 与 REST 的关系、结果新旧判断 |
| 安全 | Token、日志和技术详情脱敏要求 |

Gemini只能依赖已写入契约的事实。契约未说明的字段或状态，前端一律按未知状态保守处理。

### 3.2 当前 UI 依赖的事实字段

| 领域 | 接口事实 | UI 用途 |
| --- | --- | --- |
| Connection | HTTP health 可达结果、鉴权业务请求结果 | 控制依赖 EngineHost 的业务动作 |
| WorkflowDefinition | `status`、revision、hash | 运行、加载、编辑、保存和冲突提示 |
| WorkflowRun | `status`、`completion_reason` | 取消、查看、终态和异常终态 |
| NodeRun | `status`、`progress`、`current_stage`、`last_heartbeat` | 进度、阶段、心跳和异常提示 |
| TableRef | `lifecycle_status`、`capabilities` | 是否只读、是否允许未来读取 |
| SharedPublication | `status`、`members` | 版本查询和发布完成状态 |
| AuditEvent | `decision` | 审计结果展示 |
| NodeDefinition | `ui_visibility`、ports、`retry_safe` | 未来节点目录过滤，不直接生成按钮协议 |

`GET /api/v1/health` 当前不鉴权，只能证明 EngineHost HTTP 可达，不能证明 Token 有效。依赖 Bearer Token 的业务动作必须区分 Token 缺失、Token 待验证、鉴权成功和鉴权失败，具体规则以 `docs/FlowWeaver_UI_BackendFactsContract.md` 为准。

### 3.3 当前已存在的客户端接口矩阵

Gemini必须优先通过现有 `IEngineHostApiClient` 调用接口，不得在View或组件中自行创建 `HttpClient`、拼接API URL或写入Bearer Token。

| 客户端方法 | HTTP | 路径 | 主要参数 | 鉴权 |
| --- | --- | --- | --- | --- |
| `GetHealthAsync` | GET | `api/v1/health` | 无 | 否 |
| `ListNodeDefinitionsAsync` | GET | `api/v1/node-definitions` | 无 | Bearer |
| `ListWorkflowsAsync` | GET | `api/v1/workflows` | 无 | Bearer |
| `CreateWorkflowAsync` | POST | `api/v1/workflows` | `name`、`definition` | Bearer |
| `ValidateWorkflowDraftAsync` | POST | `api/v1/workflows/validate` | `definition` | Bearer |
| `GetWorkflowAsync` | GET | `api/v1/workflows/{workflowId}` | `workflowId` | Bearer |
| `UpdateWorkflowAsync` | PUT | `api/v1/workflows/{workflowId}` | `name`、`definition`、`baseRevisionId` | Bearer |
| `ListWorkflowRevisionsAsync` | GET | `api/v1/workflows/{workflowId}/revisions` | `workflowId` | Bearer |
| `GetWorkflowRevisionAsync` | GET | `api/v1/workflows/{workflowId}/revisions/{revisionId}` | `workflowId`、`revisionId` | Bearer |
| `StartWorkflowRunAsync` | POST | `api/v1/workflows/{workflowId}/runs` | `workflowId` | Bearer |
| `ListRunsAsync` | GET | `api/v1/runs` | `workflow_id`、可重复`status` | Bearer |
| `ListNodeRunsAsync` | GET | `api/v1/runs/{workflowRunId}/nodes` | `workflowRunId` | Bearer |
| `CancelRunAsync` | POST | `api/v1/runs/{workflowRunId}/cancel` | `workflowRunId` | Bearer |
| `ListTableRefsAsync` | GET | `api/v1/runs/{workflowRunId}/table-refs` | `workflowRunId` | Bearer |
| `ListEventsAsync` | GET | `api/v1/events` | `after_sequence_number`、`workflow_run_id`、`node_run_id`、`event_type`、`limit` | Bearer |
| `ListAuditEventsAsync` | GET | `api/v1/audit-events` | `workflow_run_id`、`node_run_id`、`event_type` | Bearer |
| `ListSharedPublicationsAsync` | GET | `api/v1/shared-publications` | `share_name`、`limit` | Bearer |
| `ListSharedPublicationVersionsAsync` | GET | `api/v1/shared-publications/{shareName}/versions` | `shareName`、`limit` | Bearer |

所有方法均支持 `CancellationToken`。Gemini在页面上下文切换时应使用现有客户端的取消能力，不得绕过客户端另写请求。

当前客户端本地可产生的稳定错误码包括：

| 错误码 | 含义 | retryable |
| --- | --- | --- |
| `TOKEN_REQUIRED` | 需要Token但当前为空 | 否 |
| `INVALID_BASE_URL` | BaseUrl无效 | 否 |
| `INVALID_RESPONSE` | 返回内容不符合API Envelope或JSON无效 | 默认否 |
| `REQUEST_TIMEOUT` | 请求超时 | 是 |
| `REQUEST_FAILED` | HTTP连接失败 | 是 |

后端领域错误码、Revision冲突码、权限拒绝码和取消失败码由Codex继续补充到 `FlowWeaver_UI_BackendFactsContract.md`。Gemini不得根据错误Message文本反推业务状态，必须优先使用稳定错误码。

### 3.4 前端接口使用规则

- View和UserControl不得直接依赖具体 `EngineHostApiClient`，由ViewModel通过 `IEngineHostApiClient` 使用。
- View不得拼接 `api/v1/...` 路径。
- View不得读取或写入Authorization Header。
- Token只能通过 `EngineHostConnectionSettings` 进入API Client。
- ActionState只依据DTO事实、连接事实和本地Busy/Selected状态。
- API失败后，前端保留原始错误码用于技术详情，面向用户的主提示使用本地化映射。
- `retryable=true`只表示可重试，不代表前端必须自动重试；自动重试策略需Codex单独批准。
- 所有上下文相关请求必须传递CancellationToken，并在返回后再次核对当前选择项ID。
- WebSocket事件和REST查询出现冲突时，Codex必须在接口契约中写明以Sequence、更新时间或最终REST状态中的哪一个为准。


### 3.5 ActionState 与后端的边界

禁止新增类似以下后端字段：

```text
show_cancel_button
enable_save_button
cancel_button_text
```

正确边界是：

```text
后端：status=RUNNING
前端：根据接口契约判断“取消运行”可用
```

若后端业务语义发生变化，Codex先修改接口契约和测试，再由 Gemini调整前端判断。

### 3.6 全局连接事实

Codex需要明确连接状态的事实来源，至少区分：

- 未检查。
- 正在检查。
- HTTP可访问。
- HTTP可访问且鉴权成功。
- HTTP可访问但鉴权失败。
- EngineHost不可访问。
- Event Stream未启动。
- Event Stream已连接。
- Event Stream断开。

业务HTTP动作只由HTTP连接和鉴权状态门控。WebSocket断开不得自动禁用仍可正常工作的HTTP动作。

当前最小实现不得把 health 成功直接等同于鉴权成功。`CanUseEngineActions` 只门控需要 EngineHost 鉴权业务接口的动作；语言切换、主题切换、BaseUrl编辑、Token编辑和连接检查本身不受该状态禁用。
若尚未实现独立鉴权探测，Token非空且未出现已知鉴权失败时，可以允许用户发起业务请求，但 UI 不得显示为“鉴权成功”；请求返回 `UNAUTHORIZED` 后再进入鉴权失败状态。

### 3.7 状态值与用户显示

DTO中的协议状态原值必须保留，例如：

```text
WAITING_PERMISSION
RUNNING
FAILED
PUBLISHED
```

UI允许做双层展示：

```text
主要显示：等待权限
技术详情：WAITING_PERMISSION
```

不得修改DTO中的协议原值，也不得把本地化文字回传给后端。


## 4. 不做事项

- 不改 Python EngineHost API 路径、字段名、权限语义和 workflow 执行行为。
- 不让后端直接返回 UI 按钮定义。后端只提供事实，UI 根据事实计算交互状态。
- 不新增完整节点配置表单。当前 `NodeDefinition` 还没有配置 Schema，节点配置仍以 JSON 草稿为主。
- 不把按钮逻辑写进 View code-behind。
- 不丢失协议字段，例如 `RUNNING`、`FAILED`、`PUBLISHED`、`table_ref_id`。主要界面可以显示本地化状态，技术详情必须保留协议原值。
- 不一次性重做全部视觉层。只在现有组件中补 `IsEnabled`、`IsVisible`、提示文案和必要的小型状态标识。

## 5. 建议的 ActionState 边界

建议先在 `MainWindowViewModel` 中增加派生属性，而不是立即抽象复杂框架。

最小可接受形式：

- `bool CanShowXxxAction`
- `bool CanUseXxxAction`
- `string XxxActionDisabledReasonText`

如果重复开始增多，再提取轻量模型：

```csharp
public sealed class UiActionState
{
    public bool IsVisible { get; init; } = true;
    public bool IsEnabled { get; init; }
    public string? DisabledReason { get; init; }
}
```

使用规则：

- 每个动作只能有一个核心可执行判断函数，ActionState 与 RelayCommand `CanExecute` 必须复用该函数。
- 不得在 `CanUseXxxAction` 和 `CanExecute` 中分别复制两套条件。
- 每个动作必须有确定的禁用原因优先级。
- `CanExecute` 仍保留为最终保护。

- `ActionState` 用于 UI 表达：按钮是否显示、是否可用、禁用原因。
- 禁用优先于隐藏。只有功能对当前对象完全无意义时才隐藏。
- 禁用原因必须可本地化，新增到 `en-US.json` 和 `zh-Hans.json`。
- XAML 优先绑定 `IsEnabled`，需要提示时绑定 `ToolTip.Tip`。
- 禁用按钮自身可能无法触发 ToolTip；实现时优先由外层 `Border`、`Panel` 或相邻状态文本承载禁用原因，并进行真实 Avalonia 交互验证。
- 状态字符串不得散落在多个文件中。至少使用状态常量和集中判断函数，例如 `IsTerminalRunStatus`、`IsCancelableRunStatus`。
- `null`、空字符串和未知未来状态必须保守禁用危险动作。
- 为避免 `MainWindowViewModel.cs` 继续膨胀，可以使用 partial 文件分区，但暂不建立复杂 ActionState 框架：

```text
MainWindowViewModel.ActionState.Connection.cs
MainWindowViewModel.ActionState.Workflow.cs
MainWindowViewModel.ActionState.Run.cs
MainWindowViewModel.ActionState.Data.cs
MainWindowViewModel.ActionState.Logs.cs
```



### 5.1 ActionState 单一判断源

推荐形式：

```csharp
private bool CanCancelSelectedRunCore()
{
    return CanUseEngineActions
        && SelectedRun is not null
        && IsCancelableRunStatus(SelectedRun.Status)
        && !IsRunBusy;
}

public bool CanUseCancelSelectedRunAction => CanCancelSelectedRunCore();

[RelayCommand(CanExecute = nameof(CanCancelSelectedRunCore))]
private async Task CancelSelectedRunAsync()
{
    // 调用既有 API
}
```

禁用原因单独计算，但必须遵循固定优先级：

```text
1. 当前正在执行同类操作
2. EngineHost未连接或鉴权失败
3. 未选择对象
4. 对象状态未知
5. 对象当前状态不允许操作
6. 其他权限或能力不足
```

### 5.2 PropertyChanged 与 Command 通知

任何依赖字段变化后，必须同时更新：

- `CanUseXxxAction`
- `CanShowXxxAction`
- `XxxActionDisabledReasonText`
- 对应 RelayCommand 的 `NotifyCanExecuteChanged()`

例如取消Run至少依赖：

```text
SelectedRun
SelectedRun.Status
IsRunBusy
ConnectionStatus
```

必须覆盖以下场景：

```text
SelectedRun对象没有替换
但SelectedRun.Status从RUNNING变成SUCCEEDED
```

如果Item ViewModel会原地修改状态，Gemini需要订阅和解绑 `SelectedRun.PropertyChanged`。如果刷新会替换整个对象，Codex需要在接口或实现说明中写清楚对象更新策略。

### 5.3 全局连接门控

建议增加统一派生状态：

```text
CanUseEngineActions
EngineActionDisabledReasonText
```

以下动作通常需要 HTTP连接和可用 Token；若已有鉴权失败事实则必须禁用：

- 刷新工作流。
- 创建和运行工作流。
- 加载、校验和保存定义。
- 刷新Run、NodeRun。
- 刷新日志、审计、TableRef和SharedPublication。

Event Stream断开只影响实时状态提示，不应自动禁用可正常使用的HTTP操作。

`CheckConnection` 本身不由 `CanUseEngineActions` 门控；它负责产生连接事实。若当前只完成 health 检查，则 UI 文案应表达为“EngineHost 可访问”，不得表达为“鉴权成功”。鉴权成功只能来自 Bearer 业务接口成功或未来明确新增的鉴权探测。

### 5.4 异步请求与上下文一致性

选择项变化时，旧请求不得覆盖新上下文。

典型风险：

```text
选择Run A并请求NodeRuns
→ 立即选择Run B并请求NodeRuns
→ A最后返回
→ A的结果覆盖B页面
```

所有上下文相关请求必须至少采用一种保护：

1. 使用独立 `CancellationTokenSource` 取消旧请求；
2. 请求返回后重新核对 workflow/run/share ID；
3. 使用请求序号，只接受最新请求；
4. 切换上下文时清空或标记旧数据。

最低保护示例：

```csharp
var requestedRunId = SelectedRun?.WorkflowRunId;
var result = await LoadNodeRunsAsync(requestedRunId, cancellationToken);

if (SelectedRun?.WorkflowRunId != requestedRunId)
{
    return;
}
```

适用范围：

- Workflow Definition。
- NodeRuns。
- TableRefs。
- RuntimeEvent查询。
- AuditEvent查询。
- SharedPublication Versions。

Busy状态必须与具体请求生命周期一致，不得因为旧请求结束而错误清除新请求的Busy状态。


## 6. 状态分类

### WorkflowDefinition

| 状态 | UI 解释 | 建议动作 |
| --- | --- | --- |
| `ACTIVE` | 可用工作流 | 可加载详情、可运行、可编辑 draft |
| `DELETED` | 已删除或不可用 | 禁用运行、禁用编辑保存 |
| 空值或未知 | 后端返回异常或未来状态 | 保守禁用危险动作，只允许刷新和查看原始信息 |

### WorkflowRun

| 状态 | UI 解释 | 建议动作 |
| --- | --- | --- |
| `PENDING` | 已创建但尚未进入执行 | 可查看、可刷新；取消是否可用按后端现有 cancel 接口保守允许 |
| `RUNNING` | 正在运行 | 可取消、可查节点、可查事件、可查数据摘要 |
| `SUCCEEDED` | 已成功 | 禁用取消；可查节点、事件、数据、共享发布、审计 |
| `FAILED` | 已失败 | 禁用取消；可查节点、事件、数据摘要、审计 |
| `CANCELLED` | 已取消 | 禁用取消；可查节点、事件、审计 |
| `ABORTED` | 进程失联或异常中止 | 禁用取消；突出显示为异常终态 |
| 空值或未知 | 未来状态 | 禁用取消，保留刷新和详情 |

### NodeRun

| 状态 | UI 解释 | 建议动作 |
| --- | --- | --- |
| `PENDING`、`WAITING_DEPENDENCY`、`WAITING_PERMISSION` | 等待调度或条件 | 只读展示 |
| `READY`、`QUEUED` | 可执行或已排队 | 只读展示 |
| `RUNNING`、`LONG_RUNNING` | 正在执行 | 显示 progress/current_stage/heartbeat |
| `CANCEL_REQUESTED` | 已请求取消 | 显示取消中，避免重复取消 |
| `SUCCEEDED` | 成功 | 可作为数据查看入口的上下文 |
| `FAILED`、`TIMED_OUT` | 失败 | 显示错误状态，建议联动日志筛选 |
| `CANCELLED`、`SKIPPED` | 已取消或跳过 | 只读展示 |

### TableRef

| 字段 | UI 解释 | 建议动作 |
| --- | --- | --- |
| `lifecycle_status=STAGING` | 临时输出，可能尚未发布 | 只读摘要；不要提供读取大表或跨 workflow 使用入口 |
| `lifecycle_status=PUBLISHED` | 已发布表引用 | 可展示 schema/summary/rows 入口，但当前若 API 未实现则先禁用并说明 |
| `capabilities` 包含 `READ` 或等价读取能力 | 可读取 | 可启用未来查看入口 |
| `capabilities` 缺失读取能力 | 不可读取 | 禁用查看入口，说明缺少读取能力 |

### SharedPublication

| 状态 | UI 解释 | 建议动作 |
| --- | --- | --- |
| `STAGING` | 尚未发布完成 | 禁用版本读取，提示发布未完成 |
| `PUBLISHED` | 已发布 | 可查询版本，可展示 members |
| 空值或未知 | 未来状态 | 保守只读 |

## 7. 页面级实施清单

### 7.1 Settings / Connection

数据来源：

- `BaseUrl`
- `Token`
- `ConnectionStatus`
- `IsChecking`
- `IsRuntimeEventStreamRunning`
- `HasRuntimeEventStreamError`

交互规则：

- `CheckConnection`：
  - 显示：始终显示。
  - 启用：`BaseUrl`非空且`!IsChecking`；该动作不依赖`CanUseEngineActions`，因为它本身用于建立连接事实。
  - 禁用原因：正在检查连接。
- `StartRuntimeEventStream`：
  - 显示：始终显示。
  - 启用：`!IsRuntimeEventStreamRunning`，并建议要求 `BaseUrl` 非空。
  - 禁用原因：事件流已连接，或服务地址为空。
- `StopRuntimeEventStream`：
  - 显示：始终显示。
  - 启用：`IsRuntimeEventStreamRunning`。
  - 禁用原因：事件流未连接。

建议 Gemini 改动：

- 给开始/停止事件流按钮绑定 `IsEnabled`。
- 禁用原因优先通过外层容器 ToolTip 或相邻简短状态文本展示；不得只依赖禁用 Button 自身接收指针事件。
- 不保存 token。
- WebSocket URL 仍不得在 UI 或日志中明文展示 token。

### 7.2 Workflow List

数据来源：

- `Workflows`
- `SelectedWorkflow`
- `SelectedWorkflow.Status`
- `NewWorkflowName`
- `IsWorkflowBusy`

交互规则：

- `RefreshWorkflows`：
  - 显示：始终显示。
  - 启用：`CanUseEngineActions && !IsWorkflowBusy`。
- `CreateTemplateWorkflow`：
  - 显示：始终显示，当前仍是最小模板创建入口。
  - 启用：`CanUseEngineActions && !IsWorkflowBusy && NewWorkflowName` 非空。
  - 禁用原因：名称为空或工作流操作忙碌。
- `StartSelectedWorkflow`：
  - 显示：有选中 workflow 时显示或启用；无选中时可禁用。
  - 启用：`CanUseEngineActions && SelectedWorkflow != null && IsActiveWorkflowStatus(SelectedWorkflow.Status) && !IsWorkflowBusy`。
  - 禁用原因：未选择工作流、工作流非 ACTIVE、正在刷新或启动。

建议 Gemini 改动：

- 不要用后端 `status` 直接控制按钮消失；优先禁用并给出原因。
- 列表项可以增加状态色标并显示本地化状态名称；DTO原始协议值必须保留在技术详情或ToolTip中。
- `Create` 暂不变成节点选择器。

### 7.3 Workflow Definition / Draft

数据来源：

- `SelectedWorkflow`
- `WorkflowDefinitionDetail`
- `WorkflowDefinitionDetail.Status`
- `WorkflowDefinitionDraftJson`
- `HasWorkflowDefinitionDraft`
- `IsLoadingWorkflowDefinition`
- `IsWorkflowDefinitionDraftBusy`

交互规则：

- `LoadSelectedWorkflowDefinition`：
  - 显示：始终显示。
  - 启用：`CanUseEngineActions && SelectedWorkflow != null && !IsLoadingWorkflowDefinition`。
  - 禁用原因：未选择工作流或正在加载。
- `ValidateWorkflowDefinitionDraft`：
  - 显示：draft 编辑区显示时显示。
  - 启用：`CanUseEngineActions && HasWorkflowDefinitionDraft && !IsWorkflowDefinitionDraftBusy`。
  - 禁用原因：草稿为空或正在校验/保存。
- `SaveWorkflowDefinitionDraft`：
  - 显示：draft 编辑区显示时显示。
  - 最低启用条件：`CanUseEngineActions && WorkflowDefinitionDetail != null && HasWorkflowDefinitionDraft && IsWorkflowDefinitionDraftDirty && !IsWorkflowDefinitionDraftBusy && !HasWorkflowDefinitionRevisionConflict`。
  - 严格模式建议再要求：`HasSuccessfulDraftValidation && ValidatedDraftHash == CurrentDraftHash`。
  - 禁用原因：正在校验/保存、服务未连接、未加载定义、Revision冲突、草稿为空、草稿未修改、校验失败、草稿在校验后又被修改。
  - Validate成功后用户再次修改草稿，必须立即使原Validate结果失效。

建议 Gemini 改动：

- 保存按钮不要只依赖 XAML 视觉状态，必须保留 command `CanExecute`。
- 发生 revision 冲突后，只显示错误和禁用原因，不自动覆盖。
- 当前仍不做图形化 workflow 编辑器。

- 建议由 Gemini 在前端实现或接入以下状态，Codex负责复核其与revision接口一致：

```text
IsWorkflowDefinitionDraftDirty
HasSuccessfulDraftValidation
HasWorkflowDefinitionRevisionConflict
ValidatedDraftHash
CurrentDraftHash
```


### 7.4 Run Monitor

数据来源：

- `Runs`
- `SelectedRun`
- `SelectedRun.Status`
- `IsRunBusy`
- `NodeRuns`
- `IsNodeRunBusy`

交互规则：

- `RefreshRuns`：
  - 显示：始终显示。
  - 启用：`CanUseEngineActions && !IsRunBusy`。
  - 说明：选中 workflow 时按 workflow 过滤；未选中时展示全部或当前后端默认返回。
- `CancelSelectedRun`：
  - 显示：有选中 run 时显示或启用；无选中时禁用。
  - 启用：`CanUseEngineActions && SelectedRun != null && IsCancelableRunStatus(SelectedRun.Status) && !IsRunBusy`。
  - UI-ACTION-1 最小可取消状态：`RUNNING`。
  - `PENDING` 暂不纳入 UI-ACTION-1 的可取消集合；只有在 Codex 补充后端测试并确认 process 创建窗口期语义后，才能扩展。
  - 禁用原因：未选择 run、run 未运行、run 已终态、正在刷新/取消。
  - 终态包括：`SUCCEEDED`、`FAILED`、`CANCELLED`、`ABORTED`。
- `RefreshNodeRuns`：
  - 显示：始终显示。
  - 启用：`CanUseEngineActions && SelectedRun != null && !IsNodeRunBusy`。
  - 禁用原因：未选择 run 或节点状态正在刷新。

建议 Gemini 改动：

- 这是第一优先落地点。
- `Cancel` 对终态 run 禁用，并通过外层容器 ToolTip 或相邻状态文本给出原因。
- 第一小步只实现取消按钮 ActionState 和确认流程，不扩展运行详情页、不改变后端取消协议。
- `RunDetailPanelView` 可以显示当前选中 run 的状态说明，但不要新增复杂详情页。
- `NodeRun` 行可以根据状态显示轻量色标或文字强调。

### 7.5 Logs / Audit

数据来源：

- 日志筛选文本
- `RuntimeEventLogEntries`
- `AuditEvents`
- `IsLogBusy`
- `HasRuntimeEventLogError`
- `HasAuditEventLogError`

交互规则：

- `RefreshRuntimeEventLog`：
  - 显示：始终显示。
  - 启用：`CanUseEngineActions && !IsLoadingRuntimeEventLog`。
  - 禁用原因：运行事件正在刷新。
- `RefreshAuditEvents`：
  - 显示：始终显示。
  - 启用：`CanUseEngineActions && !IsLoadingAuditEventLog`。
  - 禁用原因：审计事件正在刷新。

建议 Gemini 改动：

- 不新增后端筛选字段。
- 可增加“从选中 run 填入筛选”的按钮，但这属于后续小步，当前清单先不实现。
- 如果 limit 或 sequence 输入非法，沿用 ViewModel 现有拒绝消息。

### 7.6 Data

数据来源：

- `SelectedRun`
- `TableRefs`
- `TableRef.LifecycleStatus`
- `TableRef.Capabilities`
- `SharedPublications`
- `SelectedSharedPublication`
- `SharedPublication.Status`
- `SharedPublicationVersionShareNameFilter`
- `IsDataBusy`

交互规则：

- `RefreshTableRefs`：
  - 显示：始终显示。
  - 启用：`CanUseEngineActions && SelectedRun != null && !IsLoadingTableRefs`。
  - 禁用原因：未选择 run 或正在刷新 TableRef。
- `RefreshSharedPublications`：
  - 显示：始终显示。
  - 启用：`CanUseEngineActions && !IsLoadingSharedPublications`。
- `RefreshSharedPublicationVersions`：
  - 显示：始终显示。
  - 启用：`CanUseEngineActions && !IsLoadingSharedPublicationVersions`，且 `SharedPublicationVersionShareNameFilter` 非空或 `SelectedSharedPublication != null`。
  - 禁用原因：未选择共享发布且未输入 share name，或正在刷新版本。

未来按钮预留，但当前不实现：

- `View Schema`
- `View Summary`
- `View Rows`
- `Use As Input`

这些按钮需要后端表内容接口和读取权限 UI 进一步确认。当前最多可以在行内显示“可读取/不可读取”的派生文本，不打开新页面。


### 7.7 取消运行与关闭应用确认

#### 取消运行

`CancelSelectedRunCommand`保持最终 `CanExecute` 保护。点击可用的取消按钮后，前端必须先进入确认流程：

```text
用户点击取消
→ 显示确认
→ 用户确认
→ 执行现有CancelSelectedRunCommand
```

确认文案至少说明：

```text
确认取消当前运行？
已完成节点不会回滚。
```

确认状态和业务Command不能写进普通View code-behind。

#### 关闭Desktop

关闭确认属于 Desktop 生命周期边界，不并入 UI-ACTION-1。该能力需另起小步确认 portable launcher 与 Desktop 关闭时是否共同终止 EngineHost。

建议增加前端派生状态：

```text
HasActiveWorkflowRuns
RequiresCloseConfirmation
CanCloseWithoutInterruptingRun
```

当存在 `PENDING` 或 `RUNNING` 的Run时：

- 关闭窗口前显示确认。
- 明确说明关闭Desktop可能同时停止本次EngineHost。
- 用户取消时保持窗口和当前运行。
- 用户确认后执行既有关闭流程。

Codex负责核对 portable launcher 和 Desktop 生命周期语义，Gemini只实现前端确认交互。


## 8. NodeDefinition 可见性清单

数据来源：

- `GET /api/v1/node-definitions`
- `NodeDefinitionDto.ui_visibility`
- `NodeDefinitionDto.display_name`
- `NodeDefinitionDto.input_ports`
- `NodeDefinitionDto.output_ports`
- `NodeDefinitionDto.retry_safe`

交互规则：

- `ui_visibility` 为普通可见值时，允许显示在未来的节点选择入口。
- `ui_visibility` 表示测试、隐藏、内部或未知时，默认不在普通用户入口显示。
- 由于当前没有配置 Schema，不生成动态配置表单。
- Fault/Delay 等测试节点不应默认暴露在普通创建入口。

职责与阶段：

- Codex先在接口契约中写清楚 `ui_visibility` 的全部已知值、未知值策略和测试节点规则。
- Gemini只准备前端过滤与只读展示方案，不立即接入创建 UI。
- 本项从 ActionState 主线分离为 `UI-NODE-CATALOG` 专项。
- 若要展示可用节点，先做只读列表，不做拖拽画布。

## 9. 本地化清单

新增禁用原因建议 key：

- `action.disabled.busy`
- `action.disabled.no_workflow_selected`
- `action.disabled.workflow_not_active`
- `action.disabled.workflow_name_required`
- `action.disabled.definition_not_loaded`
- `action.disabled.draft_empty`
- `action.disabled.no_run_selected`
- `action.disabled.run_terminal`
- `action.disabled.event_stream_running`
- `action.disabled.event_stream_not_running`
- `action.disabled.base_url_required`
- `action.disabled.share_name_required`
- `action.disabled.missing_read_capability`

要求：

- 本地化文件由 Codex 负责更新，Gemini只提交所需Key清单并绑定Key。
- 同步更新 `Avalonia_UI/Localization/en-US.json` 和 `zh-Hans.json`。
- 不修改DTO中的协议状态原值。
- UI可以显示本地化状态名称，技术详情或ToolTip保留协议原值。
- 禁用原因必须本地化。
- Gemini新增前端文案前，先提交Key、使用位置和占位符清单，由Codex复核后落库。

## 10. 建议实施顺序

### UI-ACTION-0：准入与接口冻结

进入本阶段前必须满足：

- MainWindow Shell和页面组件拆分已稳定。
- Codex中文化主干已合入。
- 当前Binding映射已冻结。
- `dotnet build`、`dotnet test` 基线通过。
- Codex已经提交或更新 `docs/FlowWeaver_UI_BackendFactsContract.md`。
- Run、Workflow、NodeRun、TableRef、SharedPublication 的状态和空值语义已按小步确认。

本阶段不改功能代码。

### UI-ACTION-0a：RunMonitor事实冻结

这是进入 UI-ACTION-1 前的最小前置小步，只冻结 RunMonitor 取消按钮需要的事实，不要求一次性完成全领域契约。

Codex：

- 在 `docs/FlowWeaver_UI_BackendFactsContract.md` 写明 `WorkflowRun.status` 枚举、终态集合和 UI-ACTION-1 可取消集合。
- 明确 `CancelRunAsync` 的成功响应和已知失败错误码。
- 明确 health 成功不等于鉴权成功，`CanUseEngineActions` 需要鉴权事实。
- 标注 `PENDING` 取消为后续待验收扩展，不交给 Gemini 先实现。

Gemini：

- 暂不修改代码。
- 后续 UI-ACTION-1 只能依赖本小步写明的事实，不根据错误 Message 文本推断状态。

### UI-ACTION-1：RunMonitor最小ActionState

Codex：

- 确认 `docs/FlowWeaver_UI_BackendFactsContract.md` 中 RunMonitor 事实仍与后端一致。
- 复核 `CancelSelectedRunCommand`、禁用原因、确认流程和旧请求覆盖保护。
- 必要时补充或调整前端 ViewModel 测试。

Gemini：

- 增加 `CanUseCancelSelectedRunAction` 和 `CancelSelectedRunDisabledReasonText`。
- ActionState与Command复用同一核心判断函数。
- 当前只读列表项刷新会替换对象时，不强制新增 `SelectedRun.PropertyChanged` 订阅；若 Gemini 改为原地更新状态，必须补订阅与解绑。
- 实现禁用原因可见和取消确认。
- 处理Run切换时旧NodeRuns请求不得覆盖新Run。

完成后由Codex复核。

### UI-ACTION-2：Workflow List / Definition ActionState

Codex：

- 确认Workflow状态、Revision冲突、Validate和Save接口语义。
- 明确保存是否强制Validate通过。
- 明确Revision/Hash冲突错误码。

Gemini：

- 接入运行、详情、创建、校验和保存状态。
- 实现Dirty、Validate结果、Draft Hash和Revision冲突状态。
- Validate后继续修改必须使校验结果失效。
- 处理Workflow切换时旧Definition请求不得覆盖新Workflow。

完成后由Codex复核。

### UI-ACTION-3：Data ActionState

Codex：

- 确认TableRef lifecycle和capabilities全部语义。
- 确认SharedPublication状态及版本查询要求。

Gemini：

- TableRef刷新、SharedPublication和Versions刷新接入状态和禁用原因。
- 处理Run或Share切换时旧请求覆盖。
- 预留未来查看入口的派生状态，但不显示未实现按钮。

完成后由Codex复核。

### UI-ACTION-4：Settings / Connection ActionState

Codex：

- 明确HTTP健康、鉴权失败、不可访问和Event Stream断开的状态区别。
- 明确Token脱敏和错误码。

Gemini：

- 接入 `CanUseEngineActions`。
- 事件流启动/停止按钮接入状态原因。
- BaseUrl为空时禁用启动事件流。
- Event Stream断开不得禁用可用HTTP操作。

完成后由Codex复核。

### UI-ACTION-5：Logs / Audit ActionState

Codex：

- 明确查询参数边界、limit/sequence非法输入错误。
- 明确事件顺序和Sequence语义。

Gemini：

- 接入刷新状态和禁用原因。
- 处理筛选变化和旧查询结果覆盖。
- 保留原始协议和技术详情。

完成后由Codex复核。

### UI-NODE-CATALOG-0：NodeDefinition接口确认

该阶段独立于ActionState：

- Codex确认 `ui_visibility` 全部实际值和默认规则。
- Gemini只做过滤与只读展示方案。
- 不生成配置表单。
- 不接入拖拽画布。

## 11. 修改文件与职责建议

### 11.1 Codex优先负责

后端与接口：

- `src/flowweaver/api/`
- 后端DTO和状态定义所在模块。
- cancel、validate、save、table ref、publication相关接口测试。
- `docs/FlowWeaver_UI_BackendFactsContract.md`

本地化与复核：

- `Avalonia_UI/Localization/en-US.json`
- `Avalonia_UI/Localization/zh-Hans.json`
- `Avalonia_UI.Tests/MainWindowViewModelLocalizationTests.cs`
- 后端契约测试和最终集成测试。

Codex不得为了方便UI而返回按钮定义，只能补充稳定事实、状态、权限和错误码。

### 11.2 Gemini优先负责

前端逻辑与组件：

- `Avalonia_UI/ViewModels/MainWindowViewModel.ActionState.Connection.cs`
- `Avalonia_UI/ViewModels/MainWindowViewModel.ActionState.Workflow.cs`
- `Avalonia_UI/ViewModels/MainWindowViewModel.ActionState.Run.cs`
- `Avalonia_UI/ViewModels/MainWindowViewModel.ActionState.Data.cs`
- `Avalonia_UI/ViewModels/MainWindowViewModel.ActionState.Logs.cs`
- `Avalonia_UI/Views/Components/RunMonitor/RunListView.axaml`
- `Avalonia_UI/Views/Components/RunMonitor/NodeRunListView.axaml`
- `Avalonia_UI/Views/Components/Workflow/WorkflowListView.axaml`
- `Avalonia_UI/Views/Components/Workflow/WorkflowSummaryView.axaml`
- `Avalonia_UI/Views/Components/Workflow/WorkflowEditorView.axaml`
- `Avalonia_UI/Views/Components/Data/TableRefListView.axaml`
- `Avalonia_UI/Views/Components/Data/SharedPublicationListView.axaml`
- `Avalonia_UI/Views/Components/Settings/StreamConfigView.axaml`

前端测试建议：

- `Avalonia_UI.Tests/MainWindowViewModelActionStateTests.cs`
- 页面状态和XAML绑定测试。
- 异步旧结果覆盖测试。
- 禁用原因可见性手工验收清单。

Gemini需要提交新增本地化Key清单，但不直接改Codex正在维护的中文化资源，除非Codex明确授权。

### 11.3 双方都不得修改

本专项默认不修改：

- portable launcher。
- 发布归档脚本。
- workflow执行核心语义。
- 未经契约确认的权限系统。
- 未经批准的Schema。
- 自由节点画布。

## 12. 验收命令

每个小步完成后至少运行：

```powershell
dotnet build Avalonia_UI\Avalonia_UI.csproj
dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj
```

提交前补充检查：

```powershell
git diff --check
```

如涉及 XAML 结构变化，补充 XML 解析检查：

```powershell
Get-ChildItem -Recurse Avalonia_UI\Views -Filter *.axaml | ForEach-Object {
  $path=$_.FullName
  try { [xml](Get-Content $path -Raw) | Out-Null; "XML_OK $path" }
  catch { "XML_FAIL $path $($_.Exception.Message)" }
}
```


### 12.1 必测用例

#### 状态通知

- `SelectedRun`从null变为RUNNING。
- `SelectedRun`对象不更换，Status从RUNNING变SUCCEEDED。
- `IsRunBusy`从false变true再变false。
- 每次变化都更新ActionState、禁用原因和Command `CanExecute`。

#### 未知状态

必须覆盖：

```text
null
空字符串
UNKNOWN
未来新增状态
```

危险动作必须保守禁用。

#### 禁用原因优先级

同时满足多个禁用条件时，必须返回规定的最高优先级原因。

#### 全局连接

- 未连接时依赖HTTP的业务动作禁用。
- 鉴权失败时禁用并显示鉴权原因。
- Event Stream断开但HTTP正常时，HTTP业务动作仍可用。

#### 草稿

- 草稿未修改。
- 未Validate。
- Validate失败。
- Validate成功后继续修改。
- Revision冲突。
- 冲突后保存被阻止。
- 当前草稿Hash与已Validate Hash不一致。

#### 异步竞态

- Run A请求晚于Run B返回，A不得覆盖B。
- Workflow A定义晚于Workflow B返回，A不得覆盖B。
- Share A版本晚于Share B返回，A不得覆盖B。
- 旧请求结束不得错误清除新请求的Busy状态。

#### XAML交互

- 禁用原因在真实Avalonia界面中可见。
- 不只检查属性存在。
- 确认弹窗不会绕过Command。
- Token不出现在UI技术详情、日志和WebSocket URL显示中。


## 13. 通过标准

- 所有新增按钮状态均由 ViewModel 派生属性或 `CanExecute` 驱动，且ActionState和Command复用同一核心判断函数。
- XAML 不包含业务判断表达式。
- View code-behind 仍只保留 `InitializeComponent()`。
- 用户能看出按钮为什么不可用，禁用Button无法触发ToolTip时仍有其他可见入口。
- 不支持的能力不伪装成已实现。
- 后端状态未知时保守禁用危险动作。
- SelectedItem内部状态变化时，ActionState和Command立即同步。
- 上下文切换时，旧异步请求不会覆盖新页面数据。
- 依赖EngineHost的动作受HTTP连接和鉴权状态门控，Event Stream断开不误伤HTTP动作。
- 草稿保存受Dirty、Validate、Draft Hash和Revision冲突保护。
- 取消运行和关闭Desktop具有确认流程。
- 后端接口契约由Codex维护，Gemini不自行推断协议语义。
- Gemini完成前端后，必须由Codex完成最终复核。
- build/test 全部通过。
