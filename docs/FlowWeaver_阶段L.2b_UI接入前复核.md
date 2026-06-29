# FlowWeaver 阶段L.2b：UI接入前复核

> 文档状态：阶段L.2b复核完成，L.2c已按该边界实现
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段K验收基线、阶段L.0边界清单、阶段L.1运行入口收口和阶段L.2连接配置持久化边界
> 适用范围：Avalonia UI 接入 `IConnectionSettingsStore` 前的触发点、错误提示、测试边界确认
> 当前执行点：L.2c已完成最小UI接入，本文件作为接入边界依据

## 1. 目标

L.2b只解决一个问题：L.2a 已有连接配置模型和 Store 后，Avalonia UI 应该在哪里加载 BaseUrl、在哪里保存 BaseUrl，以及保存失败如何提示。

本小步产出：

- 明确当前 UI 入口和连接字段状态
- 明确 `IConnectionSettingsStore` 接入点
- 明确启动加载 BaseUrl 的方式
- 明确 health 成功后保存 BaseUrl 的方式
- 明确保存失败不阻断连接成功
- 明确 L.2c 的最小测试清单

本小步不做：

- 不修改 `MainWindowViewModel`
- 不修改 `App.axaml.cs`
- 不接入 `FileConnectionSettingsStore`
- 不保存 token
- 不增加 recent BaseUrl 下拉 UI
- 不增加配置页面

## 2. 当前代码复核

### 2.1 UI启动入口

当前位置：

```text
Avalonia_UI/App.axaml.cs
```

当前行为：

```csharp
desktop.MainWindow = new MainWindow
{
    DataContext = new MainWindowViewModel(),
};
```

结论：

- `App.axaml.cs` 是正式桌面端启动时创建 `MainWindowViewModel` 的组合根
- 当前没有依赖注入容器
- L.2c 如接入 Store，应优先保持显式构造，不引入完整 DI 框架
- 如果启动时需要异步加载本地配置，可由 `MainWindowViewModel` 暴露可测试的异步加载方法，再由启动入口触发

### 2.2 ViewModel连接字段

当前位置：

```text
Avalonia_UI/ViewModels/MainWindowViewModel.cs
```

当前字段：

- `BaseUrl` 默认值来自 `EngineHostConnectionSettings.DefaultBaseUrl`
- `Token` 默认为空字符串
- `BuildSettings()` 每次从当前 `BaseUrl` 和 `Token` 构造临时 `EngineHostConnectionSettings`
- 业务 API、WebSocket 和日志/数据查询都通过 `BuildSettings()` 读取当前内存值

结论：

- L.2c 只应在启动加载阶段写入 `BaseUrl`
- L.2c 不应在 `BuildSettings()` 内做任何持久化读写
- `Token` 仍保持仅内存输入，不从 Store 加载，也不保存到 Store

### 2.3 health检查触发点

当前位置：

```text
MainWindowViewModel.CheckConnectionAsync()
```

当前流程：

```text
ConnectionStatus = Connecting
构造 EngineHostConnectionSettings
调用 EngineHostHealthClient.CheckAsync(settings)
成功：ConnectionStatus = Connected
失败：ConnectionStatus = Error
```

结论：

- L.2c 的保存触发点应放在 health 成功分支之后
- 只有 `result.IsHealthy == true` 时保存当前 BaseUrl
- health 失败时不保存，避免把明显错误或不可达地址写入用户配置
- 保存失败不应把 `ConnectionStatus` 从 `Connected` 改成 `Error`

### 2.4 XAML连接区

当前位置：

```text
Avalonia_UI/Views/MainWindow.axaml
```

当前控件：

- Base URL 使用普通 `TextBox`
- Token 使用 `TextBox PasswordChar="*"`
- 状态区显示 `StatusMessage` 和 `ErrorMessage`

结论：

- L.2c 不需要新增控件
- 启动加载成功后，现有 Base URL 文本框自然显示恢复值
- 保存失败可复用现有 `ErrorMessage` 显示短提示，但不得覆盖 token 或显示完整 WebSocket URL

## 3. L.2c建议接入方式

### 3.1 构造边界

建议给 `MainWindowViewModel` 增加可选 Store 依赖：

```text
IConnectionSettingsStore connectionSettingsStore
```

建议保持现有构造方式兼容：

- 默认构造仍可用于正式 UI
- 测试可传入 fake store
- 不引入新的全局服务容器

正式入口建议：

```text
new MainWindowViewModel(..., new FileConnectionSettingsStore())
```

或由默认构造内部创建 `FileConnectionSettingsStore`。

### 3.2 启动加载边界

建议新增可测试方法：

```text
LoadConnectionSettingsAsync()
```

最小行为：

- 调用 `IConnectionSettingsStore.LoadAsync()`
- 将 `settings.LastSuccessfulBaseUrl` 写入 `BaseUrl`
- 不写入 `Token`
- Store 返回默认值时，保持默认 BaseUrl
- 加载失败时不阻断 UI 启动

说明：

- `FileConnectionSettingsStore.LoadAsync()` 已处理缺失、损坏 JSON、IO 和权限错误并回退默认值
- ViewModel 层仍应防御异常，避免未来 Store 实现抛错导致 UI 启动失败
- 加载失败提示可以先不新增 UI 文案，L.2c 最小要求是“不崩溃、不恢复 token”

### 3.3 health成功保存边界

建议在 `CheckConnectionAsync()` 的 `result.IsHealthy` 分支保存：

```text
PersistedConnectionSettings.FromBaseUrl(BaseUrl)
IConnectionSettingsStore.SaveAsync(settings)
```

最小行为：

- 保存前只从当前 `BaseUrl` 构造持久化模型
- 保存内容不包含 token
- 保存成功后维持现有 health 成功提示
- 保存失败时连接仍为 `Connected`
- 保存失败只显示非阻断提示

推荐提示策略：

```text
ConnectionStatus = Connected
StatusMessage = health成功消息
ErrorMessage = "Connection settings were not saved: <reason>"
```

边界：

- 保存失败不是 EngineHost 连接失败
- 不应把状态改成 `Error`
- 不应重试写文件
- 不应把异常堆栈或敏感路径写入 UI 长文案

## 4. 仍禁止接入的位置

L.2c 不应在以下位置读写连接配置：

- `BuildSettings()`
- `RefreshWorkflowsAsync()`
- `StartSelectedWorkflowAsync()`
- `RefreshRunsAsync()`
- `CancelSelectedRunAsync()`
- `RefreshNodeRunsAsync()`
- `StartRuntimeEventStreamAsync()`
- `RunRuntimeEventStreamLoopAsync()`
- RuntimeEvent / AuditEvent / TableRef / SharedPublication 查询方法

原因：

- 业务操作应只使用当前 UI 内存输入
- 持久化配置不是运行事实源
- WebSocket URL 当前包含 token query，不能被保存或日志化
- BaseUrl 保存必须和 health 成功绑定，避免业务失败时误覆盖配置

## 5. token边界复核

L.2c 仍必须保持：

- UI 启动时 token 为空
- Store 模型没有 token 字段
- Store JSON 不包含 token、authorization 或完整 WebSocket URL
- WebSocket 构造出的 `ws://...token=...` 不落盘
- 保存 BaseUrl 时不读取 `runtime/config/local_api_token`
- token 错误、轮换或失效时由用户重新输入

## 6. L.2c最小测试清单

建议新增或补充 ViewModel 测试：

| 场景 | 期望 |
| --- | --- |
| 启动加载已有配置 | `BaseUrl` 使用 Store 中的 `LastSuccessfulBaseUrl` |
| 启动加载配置 | `Token` 仍为空或保持测试显式值，不从 Store 恢复 |
| Store 缺失或损坏 | `BaseUrl` 回退默认值，UI 不崩溃 |
| health 成功 | 调用 `SaveAsync()` 保存当前 BaseUrl |
| health 失败 | 不调用 `SaveAsync()` |
| 保存失败 | `ConnectionStatus` 仍为 `Connected`，显示非阻断错误 |
| 业务 API 调用 | 不触发 Store 读写 |
| RuntimeEvent WebSocket | 不保存完整 WebSocket URL |

已有 L.2a 测试继续保留：

- URL 标准化
- 非 HTTP/HTTPS 拒绝
- recent 数量限制
- 损坏 JSON 回退默认值
- JSON 不包含 token/authorization
- 默认路径位于 `%LOCALAPPDATA%\FlowWeaver\Avalonia_UI\connection-settings.json`

## 7. L.2c最小修改清单

建议 L.2c 只修改：

- `Avalonia_UI/ViewModels/MainWindowViewModel.cs`
- `Avalonia_UI/App.axaml.cs`
- `Avalonia_UI.Tests/` 下新增或补充 ViewModel 连接配置测试
- `README.md`
- `FlowWeaver_阶段L.2_UI连接配置持久化边界.md`

暂不修改：

- `EngineHostApiClient`
- `EngineHostRuntimeEventStreamClient`
- 后端 FastAPI
- Python runtime 配置
- `runtime/config/local_api_token`
- XAML 控件结构

## 8. L.2b验收结论

L.2b 复核结论：

- UI 接入点已确认：`App.axaml.cs` 创建 `MainWindowViewModel`
- BaseUrl 加载点已确认：ViewModel 启动加载方法写入 `BaseUrl`
- BaseUrl 保存点已确认：health 成功分支保存
- 保存失败策略已确认：不阻断连接成功，只显示非阻断提示
- token 边界已确认：不加载、不保存、不写 JSON
- WebSocket URL 边界已确认：不得保存或日志化完整 URL
- 测试清单已确认：L.2c 需要覆盖加载、保存、失败和不保存 token

L.2c已按本复核边界完成：

- UI 启动时加载 BaseUrl
- health 成功后保存 BaseUrl
- 保存失败不阻断连接成功
- token 不加载、不保存
- 业务 API 和 RuntimeEvent WebSocket 不触发 Store 读写

下一步建议进入 L.2d：补充损坏配置、非法 URL 和保存失败场景的验收复核。
