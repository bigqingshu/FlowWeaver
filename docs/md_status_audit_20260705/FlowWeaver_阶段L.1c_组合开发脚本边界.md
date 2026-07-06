# FlowWeaver 阶段L.1c：组合开发脚本边界

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：后端运行入口、桌面运行入口、组合开发脚本、连接配置持久化、失败场景和正式路径 smoke 已经落地。
> 未实现：无本文件目标内的未实现项。
> 原因：当前连接与运行入口已被后续 M/N/O/P 阶段继续复用。

> 文档状态：阶段L.1c边界确认
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段K验收基线、阶段L.0边界清单、阶段L.1a和L.1b入口收口
> 适用范围：开发期组合启动脚本的职责、边界、进程所有权和未来实现前置条件
> 当前执行点：L.1c，只分析和固化脚本边界，不新增脚本文件

## 1. L.1c目标

L.1a已经固化后端 EngineHost 入口，L.1b已经固化 Avalonia 桌面端入口。L.1c只确认一个未来开发便利能力：是否可以提供一个仓内 PowerShell 组合开发脚本，把后端和桌面端按顺序拉起。

L.1c目标：

- 明确组合开发脚本只是开发便利入口，不是产品启动器
- 明确脚本可以启动哪些进程、记录哪些信息、如何退出
- 明确脚本不拥有 EngineHost 业务状态、不代替 UI 或后端的正式边界
- 明确脚本未来实现前必须满足的进程所有权与安全规则
- 给出候选脚本设计，不直接实现

L.1c不做：

- 不新增 `.ps1`、`.cmd`、`.bat` 或安装包文件
- 不修改 Avalonia UI
- 不修改 Python EngineHost
- 不让 UI 自动托管后端
- 不实现后台服务、系统托盘、自动更新或生产部署

## 2. 当前入口基线

后端入口：

```powershell
.\python312\python.exe -m uvicorn --app-dir src flowweaver.api.app:create_default_app --factory --host 127.0.0.1 --port 8000
```

桌面端构建入口：

```powershell
dotnet build Avalonia_UI/Avalonia_UI.sln
```

桌面端启动入口：

```powershell
dotnet run --project Avalonia_UI/Avalonia_UI.csproj
```

当前基线：

- EngineHost 由用户或开发者手动启动
- Avalonia UI 单独启动并连接已有 EngineHost
- UI关闭不终止 EngineHost
- EngineHost关闭会终止其拥有的 Supervisor 生命周期
- 组合脚本当前不存在

## 3. 候选脚本职责

未来如实现组合开发脚本，建议定位为：

```text
scripts/dev-start.ps1
```

候选职责：

- 检查仓库根目录
- 检查 `.\python312\python.exe` 是否存在
- 检查 `dotnet` 是否可用
- 可选执行后端依赖/版本检查
- 启动 EngineHost
- 等待 `/api/v1/health` 可用
- 提示 token 文件路径，但不打印 token 值
- 启动 Avalonia UI
- 在控制台展示后端 BaseUrl、health状态和脱敏提示
- 退出时只处理脚本自己启动的进程

候选非职责：

- 不创建 workflow、run 或测试数据
- 不直接读写 SQLite
- 不替代迁移系统
- 不替代 Avalonia UI 的 BaseUrl/token 输入
- 不修改 `runtime/config/local_api_token`
- 不扫描并杀死任意同名进程

## 4. 进程所有权边界

候选组合脚本必须遵守：

- 脚本只能停止自己本次启动的 EngineHost 进程
- 脚本只能停止自己本次启动的 Avalonia UI 进程
- 如果端口已被占用，脚本不得猜测或杀死占用进程
- 如果 `runtime/enginehost.lock` 已存在且后端拒绝启动，脚本应提示已有实例或异常退出
- 脚本不得把 UI 关闭解释为必须关闭已有 EngineHost，除非该 EngineHost 是脚本本次启动的
- 脚本不得把 EngineHost 业务状态保存在 UI 侧或脚本侧
- 脚本不拥有 WorkflowRunProcess 或 NodeExecutorProcess

推荐进程所有权：

```text
PowerShell dev script
├─ EngineHost uvicorn process    仅当脚本本次启动时拥有
│  └─ Supervisor / WorkflowRunProcess / NodeExecutorProcess  仍由EngineHost拥有
└─ Avalonia UI process           仅当脚本本次启动时拥有
```

## 5. 参数边界

未来脚本可以接受的最小参数：

| 参数 | 默认值 | 作用 | 边界 |
| --- | --- | --- | --- |
| `-Host` | `127.0.0.1` | EngineHost监听地址 | 不自动切换远程部署 |
| `-Port` | `8000` | EngineHost监听端口 | 端口占用时拒绝或提示 |
| `-DataDir` | `runtime` | EngineHost数据目录 | 不删除旧数据 |
| `-SkipBuild` | `false` | 跳过桌面端构建 | 只影响 UI 构建 |
| `-NoUi` | `false` | 只启动后端 | 不等于后台服务 |
| `-NoBackend` | `false` | 只启动 UI 并连接已有后端 | 不托管已有后端 |

暂不建议加入：

- 自动创建 workflow 或示例数据参数
- 自动打印 token 参数
- 自动清空 runtime 参数
- 自动杀进程参数
- 生产部署参数

## 6. token与日志边界

组合脚本如果未来实现，必须遵守：

- 不打印真实 token
- 不把 token 写入日志
- 不把 token 放入命令行参数传给 Avalonia UI
- 不把完整 WebSocket URL 写入控制台
- 可以提示 token 文件路径：`runtime/config/local_api_token`
- 可以输出脱敏 WebSocket URL：`ws://127.0.0.1:8000/ws/v1/events?token=***`

原因：

- 命令行参数可能被进程列表、历史记录或日志捕获
- WebSocket 当前通过 query string 传 token
- token 是本机 EngineHost API 的控制面凭据

## 7. 等待与失败边界

候选脚本等待顺序：

1. 启动或确认 EngineHost
2. 轮询 `/api/v1/health`
3. health 成功后启动 UI
4. UI 退出后，按进程所有权决定是否提示停止后端

失败处理：

| 场景 | 处理 |
| --- | --- |
| `python312` 不存在 | 拒绝并提示先补仓内 Python |
| `dotnet` 不存在 | 拒绝并提示安装 .NET 10 SDK |
| 端口被占用 | 拒绝或提示用户换端口，不杀进程 |
| EngineHost启动失败 | 展示后端退出码和日志路径 |
| health超时 | 停止脚本本次启动的后端进程，提示失败 |
| UI构建失败 | 不启动 UI，可保留后端并提示用户手动停止 |
| UI启动失败 | 提示错误，不杀已有外部 EngineHost |

## 8. 与正式产品入口的区别

组合开发脚本不是：

- 桌面产品启动器
- 安装包
- 后台服务
- 守护进程
- 进程监督器
- 多用户部署入口

它只是：

- 本地开发便利命令
- 手动入口的组合封装
- L.1a / L.1b 的顺序化执行辅助

## 9. L.1c验收清单

L.1c完成条件：

- 已明确当前不新增脚本文件
- 已明确候选脚本只作为开发便利入口
- 已明确脚本可启动 EngineHost 和 Avalonia UI，但不拥有业务状态
- 已明确脚本只停止自己启动的进程
- 已明确不得自动杀占用端口的进程
- 已明确不得打印 token 或完整 WebSocket URL
- 已明确最小参数建议和不建议参数
- 已明确下一步如实现脚本时的失败处理边界

## 10. 下一步建议

L.1c之后建议进入 L.2：UI连接配置持久化边界。L.2应优先分析 BaseUrl 是否可以保存到用户级本地配置，token 是否继续保持手动输入，避免默认明文落盘。
