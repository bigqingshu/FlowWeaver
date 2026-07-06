# FlowWeaver 阶段N.9：Desktop 发布产物最小 WorkflowRun 事件联调 Smoke

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：正式路径运行闭环、便携 layout、后端 runtime smoke、Avalonia publish、Desktop 产物 API/WebSocket/workflow run 联调 smoke 和阶段 N 验收已经落地。
> 未实现：无本文件目标内的未实现项；安装器和签名等不属于 N 阶段。
> 原因：当前 N 阶段定位是便携发布联调，不承担后续分发产品化。

> 文档状态：阶段N.9完成记录
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段K/L/M/N.0-N.8完成记录
> 适用范围：`.tmp/FlowWeaverPortable/Desktop/` 发布产物中的 API Client 与 RuntimeEvent WebSocket Client 组合联调
> 当前执行点：只验证发布产物客户端可看到最小 workflow run 生命周期事件，不启动可视化 UI、不让 UI 托管 EngineHost、不创建安装器

## 1. 目标

N.9 的目标是验证 Desktop 发布产物中的 API Client 与 RuntimeEvent WebSocket Client 可以在同一便携版 EngineHost 上组合使用，并通过 WebSocket 看到最小 workflow run 的生命周期事件。

本阶段验证：

- `.tmp/FlowWeaverPortable/EngineHost/` 可以由便携目录生成器创建
- `.tmp/FlowWeaverPortable/Desktop/` 可以由 Desktop publish 工具创建
- 使用便携目录的 `EngineHost/python312/python.exe` 启动后端
- 从发布目录加载 `Avalonia_UI.dll`
- 反射创建发布产物中的 `Avalonia_UI.Api.EngineHostApiClient`
- 反射创建发布产物中的 `Avalonia_UI.Api.EngineHostRuntimeEventStreamClient`
- 反射创建发布产物中的 `Avalonia_UI.Models.EngineHostConnectionSettings`
- 读取便携 EngineHost token
- 连接 `/ws/v1/events` 并验证 `ENGINE_READY`
- 通过发布产物 API Client 创建空 workflow
- 通过发布产物 API Client 启动 workflow run
- 通过发布产物 RuntimeEvent WebSocket Client 验证 `WORKFLOW_STARTED`
- 通过发布产物 RuntimeEvent WebSocket Client 验证 `WORKFLOW_FINISHED`

## 2. 本阶段修改清单

- 新增 `Avalonia_UI.Tests/DesktopPublishWorkflowRunEventSmokeTests.cs`
- 新增 `docs/FlowWeaver_阶段N.9_Desktop发布产物WorkflowRun事件联调Smoke.md`
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
dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj --filter FullyQualifiedName~DesktopPublishWorkflowRunEventSmokeTests --no-restore
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
9. 反射创建 `EngineHostApiClient`
10. 反射创建 `EngineHostRuntimeEventStreamClient`
11. 反射创建 `EngineHostConnectionSettings`
12. 调用 `ConnectAsync` 并验证 `ENGINE_READY`
13. 调用 `CreateWorkflowAsync` 创建空 workflow
14. 调用 `StartWorkflowRunAsync` 启动 run
15. 调用 `ReadNextAsync` 收集当前 run 的 `WORKFLOW_STARTED` / `WORKFLOW_FINISHED`
16. 关闭 WebSocket stream
17. 停止 EngineHost

## 4. 关键边界

N.9 证明的边界：

- 发布产物中的 API Client 和 RuntimeEvent WebSocket Client 可以组合使用
- 发布产物客户端可以创建并启动最小 workflow run
- 发布产物 WebSocket Client 可以收到同一 run 的 `WORKFLOW_STARTED` / `WORKFLOW_FINISHED`
- Desktop 发布目录与便携 EngineHost 目录可以完成最小运行事件联调
- 运行事件联调不需要启动 Avalonia 可视化窗口

N.9 不证明：

- 发布后的 `Avalonia_UI.exe` 可成功打开窗口
- UI ViewModel 在发布产物中可完整运行
- 非空表节点、共享表节点或审计链路在发布产物客户端中完整联调
- UI 能启动或停止 EngineHost
- 安装器、系统托盘、自动更新或服务化可用

## 5. 验收结果

已执行：

```powershell
dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj --filter FullyQualifiedName~DesktopPublishWorkflowRunEventSmokeTests --no-restore
```

结果：

```text
Passed: 1
Failed: 0
Skipped: 0
```

## 6. 明确不在 N.9 实现

N.9 不做：

- 不启动可视化 UI 窗口
- 不让 UI 托管 EngineHost
- 不创建组合启动脚本
- 不执行 UI 截图或交互测试
- 不运行非空表节点或共享表节点
- 不生成发布压缩包
- 不创建安装器、后台服务、系统托盘或自动更新
- 不提交 `.tmp/` 生成物

## 7. 下一步建议

N.9 后建议进入 N 阶段便携发布联调总体验收复核。

复核建议保持小步：

- 汇总 N.0 到 N.9 已完成矩阵
- 复核便携目录生成、后端 runtime smoke、Desktop publish、发布产物 API Client、发布产物 RuntimeEvent Client 和最小 run 事件联调
- 明确 N 阶段仍不包含的安装器、系统托盘、自动更新、UI 托管后端和可视化窗口自动化验收
- 决定下一阶段是否进入便携组合启动脚本、发布包生成或桌面 UI 发布产物可视化 smoke
