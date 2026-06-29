# FlowWeaver 阶段L.1b：桌面端运行入口收口

> 文档状态：阶段L.1b实施记录
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段K验收基线、阶段L.0边界清单和阶段L.1a后端运行入口收口
> 适用范围：Avalonia UI build/run、BaseUrl/token输入和连接检查
> 当前执行点：L.1b，只收口桌面端运行入口，不进入组合脚本、配置持久化或UI托管后端

## 1. L.1b目标

L.1b只解决一个问题：开发者或本机用户如何用当前仓库启动 Avalonia 桌面端，并通过已有 UI 输入 EngineHost BaseUrl 和 token，完成最小连接检查。

目标：

- 固化 Avalonia UI 工程入口
- 固化桌面端 build/run 命令
- 明确 BaseUrl、token 和 health 检查在 UI 中的入口
- 明确 RuntimeEvent WebSocket 入口和 token 边界
- 明确桌面端启动失败与连接失败的处理边界

L.1b不做：

- 不新增组合开发脚本
- 不新增 UI 配置持久化
- 不让 UI 自动启动、停止或重启 EngineHost
- 不修改 Avalonia 代码、后端代码或 API 协议
- 不进入安装包、自动更新、系统托盘或后台服务

## 2. 已核对的桌面端事实

当前桌面端入口事实：

- UI工程路径：`Avalonia_UI/`
- Solution：`Avalonia_UI/Avalonia_UI.sln`
- 主工程：`Avalonia_UI/Avalonia_UI.csproj`
- 测试工程：`Avalonia_UI.Tests/Avalonia_UI.Tests.csproj`
- 目标框架：`.NET 10.0`
- 输出类型：`WinExe`
- UI框架：Avalonia `11.3.12`
- MVVM依赖：CommunityToolkit.Mvvm `8.2.1`
- 程序入口：`Avalonia_UI/Program.cs`
- 主窗口：`Avalonia_UI/Views/MainWindow.axaml`
- 主ViewModel：`Avalonia_UI/ViewModels/MainWindowViewModel.cs`

当前运行环境核对：

- 本机已安装 .NET SDK `10.0.109`
- 本机已安装 .NET Runtime `10.0.9`
- 当前工程可通过 `dotnet build Avalonia_UI/Avalonia_UI.sln` 构建
- 当前测试可通过 `dotnet test Avalonia_UI.Tests/Avalonia_UI.Tests.csproj --no-build` 执行

## 3. 桌面端启动顺序

### 3.1 先启动后端

L.1b默认 EngineHost 已按 L.1a 启动：

```powershell
.\python312\python.exe -m uvicorn --app-dir src flowweaver.api.app:create_default_app --factory --host 127.0.0.1 --port 8000
```

边界：

- UI不自动启动 EngineHost
- UI不读取 `runtime/metadata/flowweaver.db`
- UI不直接读取或改写后端运行状态
- 后端端口变化时，用户需要在 UI 中同步修改 BaseUrl

### 3.2 构建桌面端

在仓库根目录执行：

```powershell
dotnet build Avalonia_UI/Avalonia_UI.sln
```

边界：

- 这是桌面端构建入口
- 构建不会启动 EngineHost
- 构建不会创建或修改后端 `runtime/` 数据

### 3.3 启动桌面端

开发运行入口：

```powershell
dotnet run --project Avalonia_UI/Avalonia_UI.csproj
```

也可以运行构建输出：

```powershell
Avalonia_UI\bin\Debug\net10.0\Avalonia_UI.exe
```

边界：

- UI启动后只显示和操作客户端状态
- UI关闭不应终止 EngineHost、WorkflowRunProcess 或 NodeExecutorProcess
- 当前阶段不提供安装包入口
- 当前阶段不提供系统托盘或后台驻留

## 4. UI连接配置入口

主窗口顶部连接区包含：

| UI项 | 当前作用 | 边界 |
| --- | --- | --- |
| `Base URL` | 输入 EngineHost HTTP 地址，默认 `http://127.0.0.1:8000` | 必须是绝对 HTTP/HTTPS URL |
| `Token` | 输入 `runtime/config/local_api_token` 中的 token | UI不自动读取 token 文件 |
| `Check` | 调用 `GET /api/v1/health` | health 不验证 token |
| `Status` | 展示 health 检查结果或错误 | 不代表业务API一定可用 |
| `Stream` | 启动 RuntimeEvent WebSocket | 需要 token |
| `Stop` | 停止 RuntimeEvent WebSocket | 不停止 EngineHost |

读取本机 token 的开发命令：

```powershell
$token = (Get-Content -Raw runtime\config\local_api_token).Trim()
```

边界：

- token 当前由用户手动粘贴到 UI
- token 不写入文档示例明文
- token 不进入日志、错误提示或异常展示
- token 错误、轮换或失效时，用户需要重新读取并输入

## 5. 连接检查边界

### 5.1 Health检查

点击 `Check` 后，UI调用：

```text
GET /api/v1/health
```

含义：

- BaseUrl格式合法
- EngineHost HTTP端口可达
- health响应结构可识别

不代表：

- token正确
- workflow API可访问
- RuntimeEvent WebSocket可连接
- 当前数据库中已有 workflow

### 5.2 业务API检查

业务API会使用：

```text
Authorization: Bearer <token>
```

最小业务检查路径：

- 在 UI 中输入 BaseUrl
- 输入 token
- 点击 `Refresh` 加载 Workflows
- 空数据库时应显示空状态或无 workflow 提示
- token 错误、轮换或失效时应显示业务请求错误

### 5.3 RuntimeEvent WebSocket检查

点击 `Stream` 后，UI构造：

```text
ws://host/ws/v1/events?token=<token>
```

边界：

- token 为空时，UI应拒绝启动事件流
- WebSocket 断开时，UI提示断线并通过 REST 恢复状态
- 日志、错误提示和异常展示不得输出真实 token
- 允许展示 `ws://host/ws/v1/events?token=***`
- L.1b不新增 WebSocket 调试脚本

## 6. 常见失败边界

| 场景 | 现象 | L.1b处理方式 |
| --- | --- | --- |
| 未安装 .NET 10 SDK | `dotnet build` 失败 | 安装或切换到 .NET 10 SDK |
| EngineHost未启动 | `Check` 失败 | 先按 L.1a 启动后端 |
| BaseUrl非法 | UI提示 BaseUrl 必须是绝对 URL | 修正 BaseUrl |
| 端口变化 | `Check` 或业务请求失败 | 修改 BaseUrl 后重试 |
| token为空 | 业务API或事件流在UI层拒绝 | 读取并输入 token |
| token错误、轮换或失效 | 业务API返回鉴权错误 | 重新读取 token 后输入 |
| 空数据库 | Workflow列表为空 | 这是合法状态，不代表连接失败 |
| WebSocket断开 | 事件流提示断线并重连 | 继续依赖 REST 恢复当前状态 |

## 7. L.1b验收清单

L.1b完成条件：

- 已明确 Avalonia UI solution、主工程、测试工程和程序入口
- 已明确 `dotnet build Avalonia_UI/Avalonia_UI.sln`
- 已明确 `dotnet run --project Avalonia_UI/Avalonia_UI.csproj`
- 已明确 UI的 BaseUrl、token、Check、Stream / Stop 入口
- 已明确 health、业务API和WebSocket三类检查的差异
- 已明确 UI不启动、不停止、不托管 EngineHost
- 已明确 token手动输入和WebSocket脱敏边界
- 已列出桌面端常见失败边界

## 8. 下一步建议

L.1b之后建议进入 L.1c：组合开发脚本边界。L.1c只分析或列出可选 PowerShell 开发脚本候选，不直接做安装包、不做服务化、不把 EngineHost 生命周期交给 UI。
