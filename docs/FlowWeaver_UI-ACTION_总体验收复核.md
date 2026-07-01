# FlowWeaver UI-ACTION 总体验收复核

> 文档状态：UI-ACTION 阶段总体验收复核完成
> 当前日期：2026-07-01
> 适用范围：Avalonia UI 的 RunMonitor、Workflow、Data、Settings / Connection、Logs / Audit ActionState 收口
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、`FlowWeaver_UI_交互状态矩阵与ActionState实施清单.md` 和 `FlowWeaver_UI_BackendFactsContract.md`

## 1. 复核结论

UI-ACTION 阶段可以视为完成当前最小验收闭环。

本次复核确认：

- 依赖 EngineHost 鉴权业务接口的动作已接入 `CanUseEngineActions`。
- Event Stream 连接状态不会误伤仍可用的 HTTP 业务动作。
- Run、Workflow、Data 和 Logs 相关旧请求覆盖风险已用 request version 边界处理。
- 日志和审计过滤器变化会废弃旧请求，同时释放 loading 状态，避免刷新按钮永久锁定。
- Workflow 启动动作已补齐 `SelectedWorkflow.Status == "ACTIVE"` 的最小门控。
- XAML 未发现未实现 WIP 按钮、事件处理器绕过 Command 或显式业务判断。

## 2. 阶段矩阵

| 阶段 | 范围 | 复核结论 | 证据 |
| --- | --- | --- | --- |
| UI-ACTION-0 | 准入与接口冻结 | 通过 | 主窗口拆分、本地化和基础 build/test 已完成 |
| UI-ACTION-0a | RunMonitor 事实冻结 | 通过 | `FlowWeaver_UI_BackendFactsContract.md` 已冻结取消所需事实 |
| UI-ACTION-1 | RunMonitor 最小 ActionState | 通过 | `CanUseCancelSelectedRunAction`、禁用原因、确认流程和 NodeRun stale guard 已覆盖 |
| UI-ACTION-2 | Workflow List / Definition | 通过 | Dirty、Validate 失效、Revision 冲突、旧 Definition 请求丢弃和 ACTIVE 启动门控已覆盖 |
| UI-ACTION-3 | Data | 通过 | TableRef、SharedPublication、Versions 刷新状态和旧请求丢弃已覆盖；未显示未实现 WIP 按钮 |
| UI-ACTION-4 | Settings / Connection | 通过 | health 不等于鉴权成功；鉴权失败禁用业务动作；Event Stream 断开不禁用 HTTP 动作 |
| UI-ACTION-5 | Logs / Audit | 通过 | RuntimeEvent / AuditEvent 刷新状态、过滤器变化、旧查询丢弃和 busy 释放已覆盖 |

## 3. 关键验收点

### 3.1 全局连接门控

当前 `CanUseEngineActions` 最小语义为：

```text
ConnectionStatus == Connected
BaseUrl 非空
Token 非空
未进入 IsAuthenticationFailed
```

它不依赖 `IsRuntimeEventStreamConnected`。因此 WebSocket 断开或未启动时，Workflow、Run、Data、Logs 等 HTTP 业务动作仍可在 HTTP 连接和 token 条件满足时使用。

`TOKEN_REQUIRED` 和 `UNAUTHORIZED` 会进入 `IsAuthenticationFailed`；用户修改 token 或 BaseUrl 后清除该失败事实。

### 3.2 异步竞态

当前已覆盖的请求版本边界：

- Workflow Definition：`workflowDefinitionLoadVersion`
- NodeRun：`nodeRunsLoadVersion`
- TableRef：`tableRefsLoadVersion`
- SharedPublication：`sharedPublicationsLoadVersion`
- SharedPublication Versions：`sharedPublicationVersionsLoadVersion`
- RuntimeEvent Log：`runtimeEventLogLoadVersion`
- AuditEvent Log：`auditEventLogLoadVersion`

过滤器、Run、Share 或 Workflow 上下文变化后，旧响应不得覆盖当前 UI 状态。

### 3.3 日志过滤收口

本次复核重点确认了 Logs / Audit 的慢请求场景：

1. 用户发起日志刷新。
2. 请求未返回时修改过滤条件。
3. 旧请求返回后被版本号丢弃。
4. `IsLoadingRuntimeEventLog` / `IsLoadingAuditEventLog` 不会永久停留在 `true`。

为支持过滤变化后立即重新查询，RuntimeEvent 和 AuditEvent 刷新命令允许并发执行，但仍受 `CanExecute` 与 loading 状态控制。

### 3.4 Workflow 启动门控

复核发现 `StartSelectedWorkflow` 原先只检查是否选中 workflow，未检查 workflow status。

已补齐为：

```text
CanUseEngineActions
SelectedWorkflow != null
SelectedWorkflow.Status == ACTIVE
!IsWorkflowBusy
```

并补充了 `DELETED` workflow 不可启动的测试。

## 4. 验证结果

已执行：

```powershell
git diff --check
dotnet build Avalonia_UI\Avalonia_UI.csproj /p:UseSharedCompilation=false /p:UseAppHost=false /p:OutputPath=".tmp\dotnet-verify-out\Avalonia_UI\" /p:IntermediateOutputPath="obj\codex-verify\"
dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj /p:UseSharedCompilation=false /p:UseAppHost=false /p:OutputPath=".tmp\dotnet-verify-out\Avalonia_UI.Tests\"
```

结果：

- `git diff --check`：通过。
- Avalonia build：通过，0 warning / 0 error。
- Avalonia tests：通过，126 passed。
- XAML 扫描：未发现 `View State`、`WIP`、`Click=`、`Tapped=`、`PointerPressed=`、`PointerReleased=` 或非 Binding `Command`。
- View code-behind 扫描：未发现业务逻辑，保持 `InitializeComponent()` 边界。

## 5. 当前不作为阻塞项的后续收口

- `MainWindowViewModel.cs` 仍较大；是否拆成 partial ActionState 文件留到后续 ViewModel 结构收口，不作为 UI-ACTION 当前验收阻塞。
- 多数按钮目前主要依赖 `CanExecute`、loading 状态和页面消息表达状态；若后续要达到更完整的生产级交互，可单独做可见禁用原因和 tooltip 体验收口。
- Desktop 关闭时如何处理运行中 workflow 属于 Desktop 生命周期和 launcher 边界，不并入 UI-ACTION 阶段验收。

## 6. 下一步建议

UI-ACTION 当前建议收口完成。

下一步有两条稳妥方向：

1. 回到主线 `P.1`：发布归档脚本方案。
2. 若继续 UI，建议进入独立的 `UI-VIEWMODEL` 或 `UI-USABILITY` 小阶段，而不是继续扩大 UI-ACTION 范围。
