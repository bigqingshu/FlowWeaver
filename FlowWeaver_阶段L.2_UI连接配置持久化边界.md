# FlowWeaver 阶段L.2：UI连接配置持久化边界

> 文档状态：阶段L.2边界确认
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段K验收基线、阶段L.0边界清单和阶段L.1运行入口收口
> 适用范围：Avalonia UI 的 EngineHost BaseUrl、token 输入和本地连接偏好持久化
> 当前执行点：L.2，只确认持久化边界，不实现配置落盘

## 1. L.2目标

L.2只解决一个问题：Avalonia UI 是否可以记住用户连接 EngineHost 时使用的客户端偏好，以及哪些内容绝不能默认保存。

目标：

- 明确当前 UI 连接配置状态
- 明确可持久化和不可持久化的数据边界
- 明确建议的用户级配置位置和格式
- 明确 token 默认不落盘的原则
- 明确后续最小实现顺序和验收条件

L.2不做：

- 不新增配置 Store 代码
- 不新增 JSON 配置文件
- 不修改 Avalonia UI
- 不保存 token
- 不读取或修改 `runtime/config/local_api_token`
- 不让 UI 直接访问 SQLite 或 EngineHost 内部运行目录

## 2. 当前状态

当前 Avalonia UI 中：

- `MainWindowViewModel.BaseUrl` 默认来自 `EngineHostConnectionSettings.DefaultBaseUrl`
- 默认 BaseUrl 为 `http://127.0.0.1:8000`
- `MainWindowViewModel.Token` 默认为空字符串
- `EngineHostConnectionSettings` 只负责构造 HTTP / WebSocket URI
- UI 关闭后，BaseUrl 和 token 输入不会持久化
- 当前没有 appsettings、用户配置文件、凭据存储或连接历史

当前代码事实：

| 项 | 当前位置 | 状态 |
| --- | --- | --- |
| BaseUrl默认值 | `Avalonia_UI/Models/EngineHostConnectionSettings.cs` | 固定默认值 |
| BaseUrl输入 | `Avalonia_UI/ViewModels/MainWindowViewModel.cs` | 仅内存 |
| token输入 | `Avalonia_UI/ViewModels/MainWindowViewModel.cs` | 仅内存 |
| token UI控件 | `Avalonia_UI/Views/MainWindow.axaml` | `PasswordChar="*"` |
| health检查 | `EngineHostHealthClient` | 不需要 token |
| 业务API | `EngineHostApiClient` | 需要 Bearer token |
| WebSocket | `EngineHostRuntimeEventStreamClient` | query string token |

## 3. 可持久化数据

第一小步建议只允许保存非敏感连接偏好：

- 最近一次成功连接的 BaseUrl
- 最近使用的 BaseUrl 列表
- 配置 schema version
- 更新时间
- 可选的 UI 连接偏好，例如是否自动填充上次 BaseUrl

建议最小 JSON 结构：

```json
{
  "schema_version": 1,
  "last_successful_base_url": "http://127.0.0.1:8000",
  "recent_base_urls": [
    "http://127.0.0.1:8000"
  ],
  "updated_at_utc": "2026-06-29T00:00:00Z"
}
```

边界：

- BaseUrl 必须是绝对 HTTP 或 HTTPS URL
- recent list 应限制数量，例如最多 5 条
- 保存前应标准化空白和结尾斜杠策略
- 读取到非法 BaseUrl 时应拒绝使用，并回退默认值
- 不应把 workflow、run、node、event、table 或 audit 状态写入该配置

## 4. 不可默认持久化数据

以下内容不得默认保存：

- token
- `Authorization: Bearer <token>`
- 完整 WebSocket URL
- `ws://.../ws/v1/events?token=<token>`
- `runtime/config/local_api_token` 的内容
- 任何从 EngineHost 返回的业务运行事实源
- workflow_run_id、node_run_id、table_ref_id 等运行态选择
- SQLite 路径或数据库内容

原因：

- token 是本机 EngineHost 控制面凭据
- WebSocket 当前通过 query string 传 token
- 明文配置文件容易被误提交、备份或日志采集
- UI 连接偏好不应变成运行事实源

## 5. token边界

L.2默认策略：

```text
BaseUrl 可以持久化
token 继续手动输入
```

token 处理规则：

- UI 启动时 token 为空
- 用户从 `runtime/config/local_api_token` 手动读取并输入
- token 错误、轮换或失效时，用户重新输入
- 关闭 UI 后 token 不保留
- 不提供“记住 token”默认开关

未来如需 token 持久化，必须单独立项并满足：

- 用户显式同意
- 使用系统凭据存储或等价安全机制
- 不写入仓库目录
- 不写入普通 JSON 配置
- 不写入日志
- 有清除凭据入口

## 6. 建议配置位置

配置应保存到用户级本地应用数据目录，而不是仓库目录。

Windows建议路径：

```text
%LOCALAPPDATA%\FlowWeaver\Avalonia_UI\connection-settings.json
```

.NET 访问方式建议：

```csharp
Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData)
```

边界：

- 不写入 `Avalonia_UI/`
- 不写入 `runtime/`
- 不写入项目根目录
- 不提交到 Git
- 不要求管理员权限
- 不和 EngineHost 的 `runtime/config/local_api_token` 混用

## 7. 读取和保存时机

建议读取时机：

- UI 启动时读取用户级连接配置
- 读取失败时回退 `EngineHostConnectionSettings.DefaultBaseUrl`
- 读取到非法 BaseUrl 时回退默认值，并可提示配置已忽略

建议保存时机：

- 用户点击 `Check` 且 health 成功后，保存当前 BaseUrl
- 或用户显式点击未来的保存入口

第一小步更稳的选择：

```text
health 成功后保存 BaseUrl
```

原因：

- 避免保存明显不可达或拼写错误的地址
- 不需要增加复杂 UI
- 和现有连接检查流程一致

不建议：

- 每次输入变化都保存
- 业务API失败时自动覆盖
- WebSocket连接失败时自动改写配置
- token变化时触发保存

## 8. 失败处理边界

| 场景 | 处理 |
| --- | --- |
| 配置文件不存在 | 使用默认 BaseUrl |
| 配置文件损坏 | 忽略配置并使用默认 BaseUrl |
| BaseUrl非法 | 忽略该值并使用默认 BaseUrl |
| 保存失败 | UI提示保存失败，但不阻断本次连接 |
| 用户无写权限 | 不崩溃，继续使用内存配置 |
| token为空 | 不从配置恢复 token，仍由用户输入 |
| EngineHost端口变化 | 用户输入新 BaseUrl，health 成功后再保存 |

## 9. 推荐实现顺序

后续如进入代码实现，建议拆成小步：

| 小步 | 内容 | 暂不进入 |
| --- | --- | --- |
| L.2a | 增加连接配置模型和 JSON 序列化测试 | ViewModel接入 |
| L.2b | 增加用户级配置路径解析和 Store 接口 | token存储 |
| L.2c | UI启动时加载 BaseUrl，health 成功后保存 BaseUrl | recent列表UI |
| L.2d | 增加损坏配置、非法URL和保存失败测试 | 凭据存储 |

推荐接口边界：

```text
IConnectionSettingsStore
├─ LoadAsync()
└─ SaveAsync(settings)
```

推荐模型边界：

```text
PersistedConnectionSettings
├─ schema_version
├─ last_successful_base_url
├─ recent_base_urls
└─ updated_at_utc
```

## 10. L.2验收清单

L.2完成条件：

- 已确认当前 UI 没有连接配置持久化
- 已明确 BaseUrl 可以作为非敏感偏好持久化
- 已明确 token 默认不持久化
- 已明确不得保存 Authorization header 和完整 WebSocket URL
- 已明确用户级配置路径建议
- 已明确读取、保存和失败处理边界
- 已明确后续代码实现的小步顺序

## 11. 下一步建议

L.2之后建议先进入 L.2a：连接配置模型和 Store 边界的最小代码实现。L.2a只增加模型、路径解析和单元测试，不接入 MainWindowViewModel，不保存 token。
