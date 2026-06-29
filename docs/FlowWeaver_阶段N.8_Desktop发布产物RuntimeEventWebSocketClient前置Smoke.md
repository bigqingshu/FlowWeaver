# FlowWeaver 阶段N.8：Desktop 发布产物 RuntimeEvent WebSocket Client 前置 Smoke

> 文档状态：阶段N.8完成记录
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段K/L/M/N.0-N.7完成记录
> 适用范围：`.tmp/FlowWeaverPortable/Desktop/` 发布产物中的 RuntimeEvent WebSocket Client 与便携 EngineHost 的前置联调
> 当前执行点：只验证发布产物 WebSocket Client 层，不启动可视化 UI、不让 UI 托管 EngineHost、不创建安装器

## 1. 目标

N.8 的目标是验证 Desktop 发布产物中的 RuntimeEvent WebSocket Client 能够在便携版目录中连接 EngineHost，并收到 EngineHost 连接就绪事件。

本阶段验证：

- `.tmp/FlowWeaverPortable/EngineHost/` 可以由便携目录生成器创建
- `.tmp/FlowWeaverPortable/Desktop/` 可以由 Desktop publish 工具创建
- 使用便携目录的 `EngineHost/python312/python.exe` 启动后端
- 从发布目录加载 `Avalonia_UI.dll`
- 反射创建发布产物中的 `Avalonia_UI.Api.EngineHostRuntimeEventStreamClient`
- 反射创建发布产物中的 `Avalonia_UI.Models.EngineHostConnectionSettings`
- 读取便携 EngineHost token
- 连接 `/ws/v1/events`
- 读取并验证 `ENGINE_READY`

## 2. 本阶段修改清单

- 新增 `Avalonia_UI.Tests/DesktopPublishRuntimeEventSmokeTests.cs`
- 新增 `docs/FlowWeaver_阶段N.8_Desktop发布产物RuntimeEventWebSocketClient前置Smoke.md`
- 更新 README 当前阶段和下一步建议

本阶段不修改：

- Python 后端产品代码
- Avalonia UI 产品代码
- `Avalonia_UI.csproj`
- `tools/create_portable_layout.py`
- `tools/publish_desktop.py`
- 安装器、启动脚本、后台服务或自动更新

## 3. 测试路径

新增测试命令：

```powershell
dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj --filter FullyQualifiedName~DesktopPublishRuntimeEventSmokeTests --no-restore
```

测试执行：

1. 使用 `tools/create_portable_layout.py --no-desktop-build` 生成便携目录
2. 使用 `tools/publish_desktop.py` 发布 Desktop 产物
3. 验证 `Desktop/Avalonia_UI.exe`
4. 验证 `Desktop/Avalonia_UI.dll`
5. 启动 `EngineHost/python312/python.exe`
6. 等待 `/api/v1/health` 可用
7. 读取 `EngineHost/runtime/config/local_api_token`
8. 通过 `AssemblyLoadContext` 从发布目录加载 `Avalonia_UI.dll`
9. 反射创建 `EngineHostRuntimeEventStreamClient`
10. 反射创建 `EngineHostConnectionSettings`
11. 调用 `ConnectAsync`
12. 调用 `ReadNextAsync`
13. 验证首条事件为 `ENGINE_READY`
14. 关闭 WebSocket stream
15. 停止 EngineHost

## 4. 关键边界

N.8 证明的边界：

- 发布产物中的 RuntimeEvent WebSocket Client 类型可被加载
- 发布产物中的 WebSocket URL 构造、token 查询参数和 DTO 解析可用
- Desktop 发布目录与便携 EngineHost 目录可以在同一 `.tmp/FlowWeaverPortable/` 下完成 WebSocket 前置联调
- WebSocket Client 联调不需要启动 Avalonia 可视化窗口

N.8 不证明：

- 发布后的 `Avalonia_UI.exe` 可成功打开窗口
- UI ViewModel 在发布产物中可完整运行
- Workflow run 事件在发布产物 WebSocket Client 中完整联调
- UI 能启动或停止 EngineHost
- 安装器、系统托盘、自动更新或服务化可用

## 5. 验收结果

已执行：

```powershell
dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj --filter FullyQualifiedName~DesktopPublishRuntimeEventSmokeTests --no-restore
```

结果：

```text
Passed: 1
Failed: 0
Skipped: 0
```

## 6. 明确不在 N.8 实现

N.8 不做：

- 不启动可视化 UI 窗口
- 不让 UI 托管 EngineHost
- 不创建组合启动脚本
- 不执行 UI 截图或交互测试
- 不生成发布压缩包
- 不创建安装器、后台服务、系统托盘或自动更新
- 不提交 `.tmp/` 生成物

## 7. 下一步建议

N.8 后建议进入 N.9：Desktop 发布产物最小 workflow run 事件联调 smoke。

N.9 建议保持小步：

- 继续不启动可视化窗口
- 继续从发布目录加载 API Client 和 RuntimeEvent WebSocket Client
- 通过发布产物 API Client 创建或读取可运行 workflow
- 启动 workflow run
- 通过发布产物 RuntimeEvent WebSocket Client 验证 `WORKFLOW_STARTED` / `WORKFLOW_FINISHED`
- 不进入 UI 托管后端、安装器或系统托盘
