# FlowWeaver

FlowWeaver 是一个本地模块化数据工作流运行平台。项目包含 Python
EngineHost 后端和 Avalonia 桌面客户端，用于管理工作流、启动运行、查看运行事件，并检查工作流产生的数据。

## 仓库结构

- `src/flowweaver/` - Python 后端运行时、API、工作流进程、节点执行、存储和协议代码。
- `Avalonia_UI/` - Avalonia 桌面应用。
- `Avalonia_UI.Tests/` - 桌面应用测试。
- `tests/` - Python 单元测试和集成测试。
- `migrations/` - Alembic 数据库迁移。
- `tools/` - 便携运行时、打包和发布辅助脚本。
- `docs/` - 设计说明、阶段记录和用户文档。

## 环境要求

- Python 3.12
- 支持 `net10.0` 的 .NET SDK
- Windows 是当前主要的桌面端和便携发布目标

仓库中包含本地 `python312/` 运行时，用于当前开发和打包流程。

## 后端

启动本地 EngineHost API：

```powershell
.\python312\python.exe -m uvicorn --app-dir src flowweaver.api.app:create_default_app --factory --host 127.0.0.1 --port 8000
```

健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
```

## 桌面端

启动 Avalonia 桌面客户端：

```powershell
dotnet run --project Avalonia_UI/Avalonia_UI.csproj
```

桌面客户端通过 HTTP 和 WebSocket 连接本地 EngineHost。

## 测试

运行 Python 测试：

```powershell
.\python312\python.exe -m pytest
```

运行桌面端测试：

```powershell
dotnet test Avalonia_UI.Tests/Avalonia_UI.Tests.csproj
```

## 文档

更详细的实现说明和历史阶段记录位于 `docs/`。便携版使用说明见
`docs/FlowWeaver_便携版用户手册.md`。
