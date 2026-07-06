# FlowWeaver 阶段L：总体验收复核

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：后端运行入口、桌面运行入口、组合开发脚本、连接配置持久化、失败场景和正式路径 smoke 已经落地。
> 未实现：无本文件目标内的未实现项。
> 原因：当前连接与运行入口已被后续 M/N/O/P 阶段继续复用。

> 文档状态：阶段L总体验收复核完成
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段K验收基线和阶段L各小步收口文档
> 适用范围：L.0 到 L.3c 的运行入口、连接配置持久化和正式路径 smoke 复核
> 当前执行点：只做阶段L总体验收复核，不进入工作流画布、打包发布或新增业务功能

## 1. 复核目标

阶段L的目标不是扩展业务能力，而是把 K 阶段最小 Avalonia 桌面 UI 接入后的运行入口、连接配置和正式路径 smoke 收口清楚。

本次总体验收复核确认：

- L.1 后端、桌面端和组合开发脚本边界是否一致
- L.2 BaseUrl 持久化与 token 不持久化边界是否闭环
- L.3a / L.3b / L.3c 三类正式路径 smoke 是否覆盖进入后续阶段前的核心风险
- README 与阶段文档是否仍能反映当前主线状态
- 是否存在进入下一阶段前必须修复的后端组合根缺口

本次不做：

- 不新增后端 API
- 不新增 UI 画布、节点编辑器或表格编辑能力
- 不新增组合开发脚本文件
- 不新增打包、安装器、后台服务或自动更新
- 不测试真实桌面窗口点击自动化

## 2. L阶段完成矩阵

| 小步 | 产出 | 复核结论 |
| --- | --- | --- |
| L.0 | `FlowWeaver_阶段L.0_运行入口与配置边界清单.md` | 已固化 EngineHost、Avalonia UI、BaseUrl、token、WebSocket 和 RuntimeStore 边界 |
| L.1a | `FlowWeaver_阶段L.1a_后端运行入口收口.md` | 已明确 `python312`、`uvicorn --app-dir src`、`create_default_app()`、默认 `runtime/`、迁移、health 和鉴权检查 |
| L.1b | `FlowWeaver_阶段L.1b_桌面端运行入口收口.md` | 已明确 Avalonia build/run、BaseUrl/token 输入、health、业务 API 和 WebSocket 检查差异 |
| L.1c | `FlowWeaver_阶段L.1c_组合开发脚本边界.md` | 已明确组合脚本仅是未来开发便利入口，当前不新增脚本，不托管业务状态 |
| L.2 | `FlowWeaver_阶段L.2_UI连接配置持久化边界.md` | 已明确只持久化非敏感 BaseUrl 偏好，token 默认不落盘 |
| L.2a | 连接配置模型、Store 和测试 | 已实现用户级 `connection-settings.json` Store，JSON 不包含 token / authorization |
| L.2b | `FlowWeaver_阶段L.2b_UI接入前复核.md` | 已确认 UI 接入点、health 成功保存点和保存失败非阻断策略 |
| L.2c | UI 启动加载和 health 成功保存 BaseUrl | 已接入 `MainWindowViewModel` 和 `App.axaml.cs`，不恢复 token |
| L.2d | `FlowWeaver_阶段L.2d_连接配置失败场景验收复核.md` | 已覆盖损坏配置、非法 URL、保存失败和敏感信息不落盘 |
| L.3 | `FlowWeaver_阶段L.3_正式路径烟雾清单.md` | 已固化空数据库、已有工作流、EngineHost 重启三类 smoke 清单 |
| L.3a | `FlowWeaver_阶段L.3a_空数据库正式路径烟雾执行记录.md` | 已通过空数据库首次启动 smoke，并补自动化 |
| L.3b | `FlowWeaver_阶段L.3b_已有工作流正式链路烟雾执行记录.md` | 已通过真实 HTTP + WebSocket + WorkflowRunProcess 正式链路 smoke，并修正相对 runtime 组合根缺口 |
| L.3c | `FlowWeaver_阶段L.3c_EngineHost重启恢复正式路径烟雾执行记录.md` | 已通过同一 `runtime/` 重启恢复 smoke，并抽取正式路径 helper |

## 3. 运行入口复核

阶段L结束后，当前正式入口保持不变：

```powershell
.\python312\python.exe -m uvicorn --app-dir src flowweaver.api.app:create_default_app --factory --host 127.0.0.1 --port 8000
dotnet run --project Avalonia_UI/Avalonia_UI.csproj
```

复核结论：

- EngineHost 仍由用户或开发者显式启动
- Avalonia UI 只连接已有 EngineHost，不启动、不停止、不嵌入后端
- UI 关闭不应终止 EngineHost、WorkflowRunProcess 或 NodeExecutorProcess
- `runtime/`、SQLite 元数据库、token、运行目录和日志仍属于 EngineHost
- UI 不直接读取 SQLite，不把运行事实源保存到客户端配置
- 组合开发脚本只作为未来候选，不属于当前已实现能力

## 4. 连接配置复核

阶段L结束后，连接配置边界为：

| 项 | 当前策略 |
| --- | --- |
| BaseUrl | 可保存到用户级本地配置 |
| token | 默认不保存，UI 启动后仍为空 |
| Authorization header | 不保存 |
| 完整 WebSocket URL | 不保存、不写日志 |
| WebSocket 日志 | 必须脱敏为 `token=***` 或移除 query |
| 配置文件损坏 | 回退默认 BaseUrl |
| 非法 URL | 回退默认 BaseUrl |
| 保存失败 | 不阻断 health 成功 |

复核结论：

- L.2 的最小实现没有引入 token 明文落盘
- health 成功是保存 BaseUrl 的唯一最小触发点
- 业务 API 和 RuntimeEvent WebSocket 不触发配置读写
- token 错误、轮换或失效时由用户重新输入，不自动改写后端 token 文件

## 5. 正式路径 smoke 复核

阶段L已覆盖三类正式路径：

| 场景 | 自动化 | 当前结论 |
| --- | --- | --- |
| 空数据库首次启动 | `tests/integration/test_l3a_empty_runtime_smoke.py` | 通过，默认 EngineHost 可创建运行目录、元数据库和 token，并返回空状态 API |
| 已有工作流正式链路 | `tests/integration/test_l3b_formal_workflow_smoke.py` | 通过，可完成 producer / consumer 工作流、NodeRun、RuntimeEvent、TableRef、SharedPublication 和 AuditEvent 链路 |
| EngineHost 重启恢复 | `tests/integration/test_l3c_enginehost_restart_smoke.py` | 通过，同一 `runtime/` 重启后可恢复 workflow、run、node、event、table、shared 和 audit 摘要，WebSocket 可收到 `ENGINE_READY` |

复核结论：

- L.3b 发现的相对 `runtime/` 子进程组合根缺口已修正
- 当前未发现进入下一阶段前必须修复的新后端组合根缺口
- smoke 均走 `create_default_app()` 正式入口、真实 uvicorn 子进程、HTTP API 和 RuntimeEvent WebSocket
- smoke 不使用测试专用 Executor 注入绕过默认路径

## 6. 本次验证结果

执行时间：2026-06-29

已运行：

```powershell
.\python312\python.exe -m ruff check tests\integration\formal_smoke_helpers.py tests\integration\test_l3a_empty_runtime_smoke.py tests\integration\test_l3b_formal_workflow_smoke.py tests\integration\test_l3c_enginehost_restart_smoke.py tests\integration\test_bootstrap_and_events.py tests\integration\test_k0b_formal_path_smoke.py
.\python312\python.exe -m pytest -q tests\integration\test_bootstrap_and_events.py tests\integration\test_l3a_empty_runtime_smoke.py tests\integration\test_l3b_formal_workflow_smoke.py tests\integration\test_l3c_enginehost_restart_smoke.py tests\integration\test_k0b_formal_path_smoke.py
dotnet build Avalonia_UI\Avalonia_UI.sln
dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj --no-build
```

结果：

| 命令 | 结果 |
| --- | --- |
| ruff L/K smoke 相关文件 | PASS |
| pytest L/K smoke 组合 | PASS，8 passed，1 个 Starlette / httpx 上游弃用 warning |
| `dotnet build Avalonia_UI\Avalonia_UI.sln` | PASS，0 warnings，0 errors |
| `dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj --no-build` | PASS，58 passed |

## 7. 明确不支持能力

阶段L完成后，以下能力仍明确不属于已完成范围：

- 工作流画布编辑
- 节点配置表单生成器
- 完整大表内容加载
- 表格编辑
- 权限审批 UI
- ReadLease 明细页
- 跨 workflow 触发入口
- UI 自动启动、停止或托管 EngineHost
- 组合开发脚本实际文件
- 运行中的 workflow 跨 EngineHost 崩溃续跑
- token 轮换后的 UI 自动恢复
- 真实桌面窗口点击端到端自动化
- 打包、安装器、后台服务、系统托盘和自动更新

## 8. 验收结论

阶段L通过总体验收复核。

当前第一阶段主线已经具备：

- Python FastAPI EngineHost 正式入口
- Avalonia + .NET 10.0 + C# + MVVM 最小桌面 UI
- HTTP + WebSocket 通信
- 只读运行态、日志审计和数据摘要视图
- BaseUrl 用户级持久化
- token 默认不落盘
- 空数据库、已有工作流和 EngineHost 重启三类正式路径 smoke

下一步建议先做下一阶段边界分析，再决定进入哪条主线。较稳的候选方向是：

- L.4 连接体验稳定化：错误文案、重连状态、手动刷新入口和脱敏提示微调
- 工作流定义与节点配置入口：先做列表、详情和最小表单边界，不直接做完整画布
- 打包发布前置清单：仅分析运行时、token、数据目录和更新边界，不直接打包
