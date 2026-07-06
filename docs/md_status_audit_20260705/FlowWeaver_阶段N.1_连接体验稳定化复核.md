# FlowWeaver 阶段N.1：连接体验稳定化复核

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：正式路径运行闭环、便携 layout、后端 runtime smoke、Avalonia publish、Desktop 产物 API/WebSocket/workflow run 联调 smoke 和阶段 N 验收已经落地。
> 未实现：无本文件目标内的未实现项；安装器和签名等不属于 N 阶段。
> 原因：当前 N 阶段定位是便携发布联调，不承担后续分发产品化。

> 文档状态：阶段N.1完成记录
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段K/L/M/N.0完成记录
> 适用范围：Avalonia UI 连接错误文案、token 失效语义和 WebSocket URL 脱敏边界
> 当前执行点：只做连接体验稳定化，不进入自由画布、节点配置表单、打包发布或后端托管

## 1. 目标

N.1 的目标是在 N.0 正式路径闭环通过后，把桌面端连接失败时的用户可理解性和敏感信息边界收口。

本阶段只做：

- 统一 EngineHost API 错误描述入口
- 将 token 错误明确描述为“错误、轮换或失效”
- 增加 RuntimeEvent WebSocket URL token 脱敏工具
- 让事件流连接异常展示脱敏后的错误信息
- 补充对应 C# 单元测试

本阶段不做：

- 不新增后端 API
- 不改 EngineHost token 生成或轮换机制
- 不保存 token
- 不实现 token 自动发现或自动刷新
- 不实现 UI 托管或自动启停 EngineHost
- 不进入自由画布、动态配置表单或打包发布

## 2. 本阶段修改清单

| 文件 | 修改 |
| --- | --- |
| `Avalonia_UI/Api/EngineHostConnectionDiagnostics.cs` | 新增连接错误描述和 token 脱敏工具 |
| `Avalonia_UI/ViewModels/MainWindowViewModel.cs` | REST/API 错误和事件流异常接入统一连接诊断文案 |
| `Avalonia_UI.Tests/EngineHostConnectionDiagnosticsTests.cs` | 覆盖 token 错误语义和 WebSocket URL 脱敏 |
| `Avalonia_UI.Tests/MainWindowViewModelConnectionSettingsTests.cs` | 覆盖业务 API token 错误文案 |
| `Avalonia_UI.Tests/MainWindowViewModelRuntimeEventTests.cs` | 覆盖事件流异常不泄露 token |
| `README.md` | 更新当前阶段和下一步建议 |

## 3. 稳定化语义

| 场景 | 当前 UI 文案策略 |
| --- | --- |
| 缺少 token | 明确提示 `EngineHost token is required.` |
| token 错误、轮换或失效 | 明确提示用户重新输入当前本地 API token |
| BaseUrl 非法 | 明确提示 EngineHost BaseUrl 无效 |
| 请求超时 | 明确提示检查 EngineHost 是否仍在运行 |
| 请求失败 | 保留失败原因，但经由统一入口展示 |
| RuntimeEvent 连接异常 | 展示连接失败，并对异常消息中的 `token` 脱敏 |
| WebSocket URL 展示或日志 | 统一脱敏为 `token=***` |

## 4. 当前仍不支持

N.1 完成后仍明确不支持：

- token 自动读取、自动轮换或自动修复
- token 持久化
- 完整离线事件缓存
- 长期重连策略配置 UI
- 系统托盘、后台服务、安装器或自动更新
- 桌面端自动启动/停止 EngineHost

这些能力应在后续阶段单独拆分，不混入 N.1。

## 5. 验收测试

执行时间：2026-06-29

已运行：

```powershell
dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj --filter "EngineHostConnectionDiagnosticsTests|MainWindowViewModelConnectionSettingsTests|MainWindowViewModelRuntimeEventTests" --logger "console;verbosity=minimal"
dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj --logger "console;verbosity=minimal"
dotnet build Avalonia_UI\Avalonia_UI.sln
.\python312\python.exe -m ruff check src tests
```

结果：

| 命令 | 结果 |
| --- | --- |
| N.1 受影响 C# 测试 | PASS，15 passed |
| Avalonia 全量测试 | PASS，83 passed |
| Avalonia solution build | PASS，0 warnings，0 errors |
| ruff `src tests` | PASS |

## 6. 阶段结论

N.1 已完成连接体验稳定化的最小收口。

当前桌面端连接错误已具备统一描述入口；token 错误不再只显示后端原始 `UNAUTHORIZED`，而是明确为错误、轮换或失效；RuntimeEvent WebSocket 连接异常会对 URL token 做脱敏后再展示。

下一步建议进入 N.2 打包发布前置清单，仅做运行时、数据目录、token、日志和配置迁移边界分析，不直接打包。
