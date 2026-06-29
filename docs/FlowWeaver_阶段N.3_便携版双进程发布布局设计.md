# FlowWeaver 阶段N.3：便携版双进程发布布局设计

> 文档状态：阶段N.3完成记录
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段K/L/M/N.0/N.1/N.2完成记录
> 适用范围：便携版双进程发布目录、启动工作目录、运行时数据、日志和 smoke 边界
> 当前执行点：只做布局设计，不实际打包、不新增启动脚本、不修改运行入口

## 1. 目标

N.3 的目标是把后续“便携版双进程”发布形态设计清楚，作为真正发布脚本、发布目录 smoke 或安装器之前的边界。

便携版双进程的定义：

- Python FastAPI EngineHost 是独立后端进程
- Avalonia UI 是独立桌面进程
- UI 通过 HTTP + WebSocket 访问 EngineHost
- UI 不启动、不停止、不嵌入 EngineHost
- 发布目录可以整体复制到另一台同类 Windows 环境中运行
- 运行数据默认保留在便携目录内部，除非未来显式增加用户数据目录配置

## 2. 本阶段修改清单

- 新增 `docs/FlowWeaver_阶段N.3_便携版双进程发布布局设计.md`
- 更新 README 当前阶段和下一步建议

本阶段不修改：

- Python 后端产品代码
- Avalonia UI 产品代码
- `.csproj` 发布配置
- 后端冻结、wheel 安装或依赖安装脚本
- PowerShell / cmd / bat 启动脚本
- 安装器、后台服务、系统托盘或自动更新

## 3. 当前实现约束

当前后端入口仍是：

```powershell
.\python312\python.exe -m uvicorn --app-dir src flowweaver.api.app:create_default_app --factory --host 127.0.0.1 --port 8000
```

当前桌面端开发入口仍是：

```powershell
dotnet run --project Avalonia_UI/Avalonia_UI.csproj
```

当前必须尊重的实现事实：

- `EngineHostBootstrap._upgrade_database()` 使用相对路径 `alembic.ini`
- Alembic `script_location` 当前设置为相对路径 `migrations`
- `bootstrap_default()` 默认 `data_dir` 是 `runtime`
- `runtime/` 会按启动进程工作目录解析
- 本地 API token 位于 `runtime/config/local_api_token`
- Avalonia UI 连接配置位于用户级 `%LOCALAPPDATA%\FlowWeaver\Avalonia_UI\connection-settings.json`
- UI 只持久化 BaseUrl，不默认持久化 token
- WebSocket token 必须脱敏，不记录完整 URL

因此，便携版 V1 最稳的设计是：后端启动时工作目录固定为便携发布包中的 EngineHost 目录。

## 4. 推荐便携目录结构

推荐 V1 目录：

```text
FlowWeaverPortable/
  EngineHost/
    python312/
    src/
      flowweaver/
    migrations/
      env.py
      versions/
    alembic.ini
    pyproject.toml
    uv.lock
    runtime/
      metadata/
        flowweaver.db
      workflow_runs/
      logs/
        workflow_runs/
        enginehost/
      temp/
      config/
        local_api_token
  Desktop/
    FlowWeaver.exe
    *.dll
    *.deps.json
    *.runtimeconfig.json
    Assets/
  docs/
    README.txt
```

目录职责：

| 目录 | 职责 | V1结论 |
| --- | --- | --- |
| `EngineHost/` | 后端工作目录和运行数据根 | 后端必须从此目录启动 |
| `EngineHost/python312/` | 嵌入式 Python 3.12 runtime 和后端依赖 | 发布包携带，不要求系统 Python |
| `EngineHost/src/` | 当前源码运行入口 | V1 先保持 `--app-dir src` 模式 |
| `EngineHost/migrations/` | Alembic 迁移脚本 | 必须随包携带 |
| `EngineHost/alembic.ini` | Alembic 配置 | 必须位于后端工作目录 |
| `EngineHost/runtime/` | 元数据库、token、运行文件、日志、临时文件 | 首次启动生成，便携版默认留在包内 |
| `Desktop/` | Avalonia 发布产物 | 只作为客户端运行 |
| `docs/` | 发布说明 | 不包含真实 token |

V1 暂不使用：

- `Program Files`
- Windows Service 数据目录
- Roaming profile
- 系统级 Python
- UI 内嵌后端

## 5. 后端启动边界

便携版后端启动原则：

- 启动前将当前工作目录切到 `FlowWeaverPortable/EngineHost`
- 使用 `.\python312\python.exe`
- 保持 `--app-dir src`
- 保持 `create_default_app --factory`
- host 默认 `127.0.0.1`
- port 默认 `8000`
- 不通过命令行传 token

候选启动命令：

```powershell
Set-Location .\EngineHost
.\python312\python.exe -m uvicorn --app-dir src flowweaver.api.app:create_default_app --factory --host 127.0.0.1 --port 8000
```

后端启动器如果未来实现，必须：

- 固定工作目录为 `EngineHost/`
- 不打印真实 token
- 不把完整 WebSocket URL 写入日志
- 不删除已有 `runtime/`
- 不自动杀死端口占用进程
- 不绕过 Alembic 迁移
- 不直接写 SQLite

## 6. Python runtime 与依赖边界

V1 推荐携带仓内同类 embedded Python：

```text
EngineHost/python312/
```

发布包内的 Python 必须满足：

- `python312._pth` 启用 `import site`
- 可执行 `python.exe -m uvicorn`
- 已包含运行依赖：FastAPI、SQLAlchemy、Alembic、Pydantic、Uvicorn、websockets、msgpack 等
- 不依赖用户机器的全局 Python 或全局 PATH
- 不在首次启动时联网安装依赖

`pyproject.toml` 和 `uv.lock` 在便携版 V1 中作为依赖来源说明和重建依据保留；运行时优先依赖已随包带好的 Python 环境。

暂不进入：

- PyInstaller / Nuitka 单文件后端
- wheel 安装模式
- 自动在线依赖恢复
- 多 Python 版本兼容矩阵

## 7. Avalonia UI 边界

便携版 UI 发布目录建议为：

```text
FlowWeaverPortable/Desktop/
```

UI 运行原则：

- UI 只连接 EngineHost，不拥有 EngineHost 生命周期
- 默认 BaseUrl 仍是 `http://127.0.0.1:8000`
- health 成功后继续保存 BaseUrl 到用户级连接配置
- token 仍由用户显式输入
- token 不默认写入 `connection-settings.json`
- UI 不直接读取 `EngineHost/runtime/metadata/flowweaver.db`
- UI 不直接读取 `EngineHost/runtime/config/local_api_token`

未来如要提供“复制本机 token”体验，必须作为显式开发便利动作单独收口，不能在 N.3 设计中默认开启。

## 8. 数据目录与升级边界

便携版 V1 默认数据目录：

```text
FlowWeaverPortable/EngineHost/runtime/
```

这意味着：

- 复制整个 `FlowWeaverPortable/` 可以带走本机运行数据
- 删除 `runtime/` 会得到空数据库首次启动体验
- 替换 `EngineHost/src/`、`migrations/`、`python312/` 时必须保留 `runtime/`
- 升级前建议备份 `runtime/metadata/flowweaver.db`

发布版升级 smoke 必须覆盖：

| 场景 | 验收要求 |
| --- | --- |
| 空 `runtime/` | 能创建目录、数据库、token，health 可用 |
| 已有 `runtime/` | 能读已有 workflow、run、event、table、shared、audit 摘要 |
| EngineHost 重启 | UI REST 恢复和 WebSocket 重连可用 |
| migrations 升级 | 迁移成功后旧数据可读 |
| token 文件缺失 | 后端重新生成 token，UI 需要用户重新输入 |

## 9. 日志边界

当前代码已有：

- workflow run stdout/stderr 写入 `runtime/logs/workflow_runs/`
- EngineConfig 具备 `max_log_file_bytes`
- WebSocket URL token 脱敏边界

便携版 V1 建议预留：

```text
EngineHost/runtime/logs/enginehost/
```

未来启动器如果实现 stdout/stderr 重定向，建议写入：

```text
EngineHost/runtime/logs/enginehost/stdout.log
EngineHost/runtime/logs/enginehost/stderr.log
```

日志约束：

- 不记录真实 token
- 不记录完整 WebSocket URL
- 不把 `runtime/metadata/flowweaver.db` 当作日志附件自动导出
- 日志不可写时，后端应启动即失败或给出明确错误，不能半初始化

## 10. 发布目录 smoke 设计

N.3 不执行 smoke，只定义后续 smoke 应覆盖的最小路径。

后续发布目录 smoke 建议步骤：

1. 复制或生成 `FlowWeaverPortable/`
2. 删除或准备目标 `EngineHost/runtime/`
3. 从 `FlowWeaverPortable/EngineHost/` 启动 EngineHost
4. 请求 `/api/v1/health`
5. 读取 `EngineHost/runtime/config/local_api_token`
6. 使用 token 调用 workflow 列表 API
7. 启动 Avalonia UI 发布产物
8. 使用默认 BaseUrl 连接 EngineHost
9. 创建或读取 workflow
10. 启动 run，查询 NodeRun
11. 监听 RuntimeEvent WebSocket
12. 查询 TableRef、SharedPublication 和 AuditEvent 摘要
13. cancel 或等待 run 终态
14. 停止 EngineHost 后重启
15. UI 重新 health、REST 恢复、WebSocket 重连
16. 搜索发布日志，确认不包含真实 token

必须显式覆盖三类数据状态：

- 空数据库首次启动
- 已有 workflow / run / event 数据
- EngineHost 重启恢复

## 11. 明确不在 N.3 实现

N.3 不做：

- 不执行 `dotnet publish`
- 不复制文件生成真实 `FlowWeaverPortable/`
- 不创建 `start-enginehost.ps1`
- 不创建 `start-desktop.ps1`
- 不创建后端依赖安装脚本
- 不创建 PyInstaller / Nuitka / wheel 发布
- 不改变 `EngineHostBootstrap` 的相对路径行为
- 不让 UI 托管 EngineHost
- 不新增安装器、后台服务、系统托盘或自动更新

## 12. 下一步建议

N.3 后建议进入 N.4：便携发布目录生成与 smoke 前置实现。

N.4 建议仍保持很小：

- 先只生成 `.tmp/FlowWeaverPortable/` 测试目录
- 只复制当前运行所需文件
- 不提交生成物
- 不创建安装器
- 优先验证后端工作目录、Alembic、`runtime/`、token 和 health
- UI 发布可以先用现有 build 输出或后续再切到 `dotnet publish`

完成 N.4 后，再决定是否进入：

- Avalonia `dotnet publish` 正式配置
- 后端 embedded Python 依赖冻结清单
- 组合启动脚本
- 发布目录端到端 smoke
