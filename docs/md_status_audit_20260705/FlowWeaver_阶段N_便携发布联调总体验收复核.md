# FlowWeaver 阶段N：便携发布联调总体验收复核

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：正式路径运行闭环、便携 layout、后端 runtime smoke、Avalonia publish、Desktop 产物 API/WebSocket/workflow run 联调 smoke 和阶段 N 验收已经落地。
> 未实现：无本文件目标内的未实现项；安装器和签名等不属于 N 阶段。
> 原因：当前 N 阶段定位是便携发布联调，不承担后续分发产品化。

> 文档状态：阶段N总体验收复核完成
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段K/L/M验收基线和阶段N各小步完成记录
> 适用范围：N.0 到 N.9 的正式路径通信、便携发布布局、后端 runtime smoke、Desktop publish 和发布产物客户端联调复核
> 当前执行点：只做阶段N总体验收复核，不进入安装器、系统托盘、自动更新、UI 托管 EngineHost 或真实桌面窗口自动化

## 1. 复核目标

阶段N的目标不是扩展业务能力，而是把阶段K/L/M形成的 EngineHost 与 Avalonia 通信能力推进到便携发布前置边界。

本次总体验收复核确认：

- N.0 的真实 EngineHost + Avalonia API/WebSocket 客户端正式路径闭环是否成立
- N.1 到 N.3 的连接体验、发布前置和便携双进程布局边界是否已固化
- N.4 到 N.6 的便携目录、后端 runtime 和 Desktop publish 自动化是否可用
- N.7 到 N.9 的 Desktop 发布产物 API/WebSocket 客户端联调是否覆盖关键风险
- `.tmp/FlowWeaverPortable/` 是否仍是生成物，不进入版本控制
- README 与阶段文档是否反映当前主线状态
- 是否存在进入下一阶段前必须修复的便携组合根缺口

本次不做：

- 不新增后端 API
- 不修改 Avalonia UI 产品代码
- 不新增组合启动脚本
- 不启动可视化 UI 窗口
- 不做 UI 点击自动化或截图验收
- 不生成发布压缩包
- 不创建安装器、后台服务、系统托盘或自动更新

## 2. N阶段完成矩阵

| 小步 | 产出 | 复核结论 |
| --- | --- | --- |
| N.0 | `FlowWeaver_阶段N.0_正式路径运行闭环Smoke.md`、`EngineHostFormalSmokeTests.cs` | 已验证真实 EngineHost + Avalonia API/WebSocket 客户端可完成定义创建、校验、保存、启动 run、事件和数据摘要闭环 |
| N.1 | `FlowWeaver_阶段N.1_连接体验稳定化复核.md` | 已固化 token 错误、轮换或失效、WebSocket URL 脱敏和连接错误提示边界 |
| N.2 | `FlowWeaver_阶段N.2_打包发布前置清单.md` | 已固化 runtime、token、日志、配置迁移和发布 smoke 前置清单 |
| N.3 | `FlowWeaver_阶段N.3_便携版双进程发布布局设计.md` | 已固化便携目录中 `EngineHost/` 与 `Desktop/` 的职责、工作目录和生成物边界 |
| N.4 | `FlowWeaver_阶段N.4_便携发布目录生成与Smoke前置实现.md`、`tools/create_portable_layout.py`、`test_n4_portable_layout_smoke.py` | 已验证便携 EngineHost 目录可生成并从生成目录启动 |
| N.5 | `FlowWeaver_阶段N.5_便携目录后端完整RuntimeSmoke.md`、`test_n5_portable_runtime_smoke.py` | 已验证便携目录后端可完成 workflow、run、NodeRun、RuntimeEvent、TableRef、SharedPublication 和 AuditEvent 链路 |
| N.6 | `FlowWeaver_阶段N.6_AvaloniaPublish与Desktop产物Smoke.md`、`tools/publish_desktop.py`、`test_n6_desktop_publish_smoke.py` | 已验证 Desktop publish 产物文件存在且不包含调试诊断依赖 |
| N.7 | `FlowWeaver_阶段N.7_Desktop发布产物APIClient联调前置Smoke.md`、`DesktopPublishApiClientSmokeTests.cs` | 已验证发布目录 `Avalonia_UI.dll` 中的 API Client 可连接便携 EngineHost 并完成 health、node definitions 和 workflows 基础 API |
| N.8 | `FlowWeaver_阶段N.8_Desktop发布产物RuntimeEventWebSocketClient前置Smoke.md`、`DesktopPublishRuntimeEventSmokeTests.cs` | 已验证发布目录 RuntimeEvent WebSocket Client 可连接便携 EngineHost 并收到 `ENGINE_READY` |
| N.9 | `FlowWeaver_阶段N.9_Desktop发布产物WorkflowRun事件联调Smoke.md`、`DesktopPublishWorkflowRunEventSmokeTests.cs` | 已验证发布目录 API Client 与 RuntimeEvent WebSocket Client 可组合创建空 workflow、启动 run 并收到 `WORKFLOW_STARTED` / `WORKFLOW_FINISHED` |

## 3. 便携发布边界复核

阶段N结束后，当前便携发布前置边界为：

| 区域 | 当前结论 |
| --- | --- |
| 便携根目录 | `.tmp/FlowWeaverPortable/`，生成物，仍不提交 |
| 后端目录 | `.tmp/FlowWeaverPortable/EngineHost/` |
| 后端工作目录 | `EngineHost/` 自身 |
| 后端 Python | `EngineHost/python312/python.exe` |
| 后端源码和迁移 | `EngineHost/src/`、`EngineHost/migrations/`、`EngineHost/alembic.ini` |
| 后端 runtime | `EngineHost/runtime/`，首次启动生成 metadata、token、workflow_runs、logs、temp |
| 桌面端目录 | `.tmp/FlowWeaverPortable/Desktop/` |
| 桌面端入口 | `Desktop/Avalonia_UI.exe` 和 `Desktop/Avalonia_UI.dll` |
| 桌面端通信 | 只通过 HTTP + WebSocket 访问 EngineHost |
| token | 由 EngineHost `runtime/config/local_api_token` 生成或复用 |
| UI 托管后端 | 当前不支持 |
| 发布包压缩/安装器 | 当前不支持 |

复核结论：

- 便携后端从生成目录启动时，默认 runtime 落在 `EngineHost/runtime/`
- Desktop 发布产物与 EngineHost 通过显式 `BaseUrl` 和 token 通信
- Desktop 发布产物 smoke 均不启动可视化窗口，不依赖 UI 点击自动化
- 发布产物客户端联调覆盖了 API Client、WebSocket Client 和最小 run 生命周期事件
- 本次复核发现 Desktop 发布产物 smoke 组合运行时共用固定 `.tmp/FlowWeaverPortable/` 会在 Windows 上触发 DLL 文件锁清理冲突；已改为每个 smoke 使用独立 `.tmp/FlowWeaverPortableDesktopPublish-*` 输出目录

## 4. 自动化验收覆盖

阶段N当前自动化覆盖分三层。

第一层是正式通信闭环：

| 测试 | 覆盖 |
| --- | --- |
| `Avalonia_UI.Tests/EngineHostFormalSmokeTests.cs` | 真实 EngineHost + Avalonia API/WebSocket 客户端的创建、校验、保存、启动、事件、数据摘要和审计闭环 |

第二层是便携目录与发布产物：

| 测试 | 覆盖 |
| --- | --- |
| `tests/integration/test_n4_portable_layout_smoke.py` | 便携 EngineHost 目录生成、启动、runtime 初始化和空 workflow 查询 |
| `tests/integration/test_n5_portable_runtime_smoke.py` | 便携目录后端完整 runtime 链路 |
| `tests/integration/test_n6_desktop_publish_smoke.py` | Desktop publish 产物文件级 smoke |

第三层是 Desktop 发布产物客户端联调：

| 测试 | 覆盖 |
| --- | --- |
| `Avalonia_UI.Tests/DesktopPublishApiClientSmokeTests.cs` | 发布 DLL API Client 连接便携 EngineHost |
| `Avalonia_UI.Tests/DesktopPublishRuntimeEventSmokeTests.cs` | 发布 DLL RuntimeEvent WebSocket Client 连接便携 EngineHost 并收到 `ENGINE_READY` |
| `Avalonia_UI.Tests/DesktopPublishWorkflowRunEventSmokeTests.cs` | 发布 DLL API + WebSocket Client 创建空 workflow、启动 run 并收到 `WORKFLOW_STARTED` / `WORKFLOW_FINISHED` |

## 5. 本次验证结果

执行时间：2026-06-29

已运行：

```powershell
.\python312\python.exe -m ruff check tools\create_portable_layout.py tools\publish_desktop.py tests\integration\test_n4_portable_layout_smoke.py tests\integration\test_n5_portable_runtime_smoke.py tests\integration\test_n6_desktop_publish_smoke.py tests\integration\formal_smoke_helpers.py
.\python312\python.exe -m pytest -q tests\integration\test_n4_portable_layout_smoke.py tests\integration\test_n5_portable_runtime_smoke.py tests\integration\test_n6_desktop_publish_smoke.py
dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj --filter "FullyQualifiedName~DesktopPublishApiClientSmokeTests|FullyQualifiedName~DesktopPublishRuntimeEventSmokeTests|FullyQualifiedName~DesktopPublishWorkflowRunEventSmokeTests" --no-restore
dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj --filter FullyQualifiedName~EngineHostFormalSmokeTests --no-restore
git diff --check
```

结果：

| 命令 | 结果 |
| --- | --- |
| ruff N 阶段相关工具和 Python smoke | PASS |
| pytest N.4-N.6 | PASS，3 passed |
| dotnet Desktop 发布产物 smoke | PASS，3 passed |
| dotnet N.0 正式路径 smoke | PASS，1 passed |
| `git diff --check` | PASS，仅 Windows 换行提示 |

## 6. 明确不支持能力

阶段N完成后，以下能力仍明确不属于已完成范围：

- 安装器
- 系统托盘
- 后台服务
- 自动更新
- UI 自动启动、停止或托管 EngineHost
- 组合启动脚本实际文件
- 发布压缩包生成
- 真实桌面窗口点击端到端自动化
- UI 截图验收
- 发布产物可视化窗口 smoke
- 非空表节点在发布 DLL WebSocket smoke 中的完整联调
- 共享表和审计链路在发布 DLL WebSocket smoke 中的完整联调
- token 轮换后的发布产物自动恢复
- 多用户安装路径、权限提升和卸载流程

## 7. 验收结论

阶段N通过总体验收复核。

当前主线已具备：

- 真实 EngineHost + Avalonia API/WebSocket 客户端正式通信闭环
- 便携 `EngineHost/` 目录生成与自启动 smoke
- 便携目录后端完整 runtime smoke
- Avalonia Desktop publish 产物 smoke
- 发布产物 API Client 连接便携 EngineHost smoke
- 发布产物 RuntimeEvent WebSocket Client 连接便携 EngineHost smoke
- 发布产物 API + WebSocket Client 最小 workflow run 生命周期事件 smoke

当前未发现进入下一阶段前必须修复的便携组合根缺口。

下一步建议先做下一阶段边界分析，再决定进入哪条主线。较稳的候选方向是：

- O.0 便携组合启动脚本边界分析：只定义启动顺序、日志、端口、token 读取和进程退出策略，不直接做托盘或安装器
- O.1 发布包生成前置清单：明确 zip 目录结构、版本号、生成物清理和 smoke 顺序
- O.2 发布产物可视化窗口 smoke 边界分析：先评估是否需要 Playwright/Appium/WinAppDriver 或手工验收清单，不直接引入重型 UI 自动化
