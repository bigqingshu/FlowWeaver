# FlowWeaver 阶段N.2：打包发布前置清单

> 文档状态：阶段N.2完成记录
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段K/L/M/N.0/N.1完成记录
> 适用范围：进入真实打包发布前的运行时、数据目录、token、日志和配置迁移边界
> 当前执行点：只做清单和边界固化，不实际打包、不新增安装器、不改运行入口

## 1. 目标

N.2 的目标是把后续打包发布前必须回答的问题列清楚，避免在 UI 或后端还未准备好时直接进入安装器、后台服务或自动更新。

当前已确认：

- 后端入口仍是：

```powershell
.\python312\python.exe -m uvicorn --app-dir src flowweaver.api.app:create_default_app --factory --host 127.0.0.1 --port 8000
```

- 桌面端入口仍是：

```powershell
dotnet run --project Avalonia_UI/Avalonia_UI.csproj
```

- Avalonia UI 只通过 HTTP + WebSocket 连接已有 EngineHost
- UI 不启动、不停止、不嵌入 EngineHost
- `runtime/`、SQLite 元数据库、token、运行目录和日志仍属于 EngineHost

## 2. 本阶段修改清单

- 新增 `docs/FlowWeaver_阶段N.2_打包发布前置清单.md`
- 更新 README 当前阶段和下一步建议

本阶段不修改：

- Python 后端产品代码
- Avalonia UI 产品代码
- 运行入口命令
- `.csproj` 发布配置
- 安装器、脚本或 CI

## 3. 发布形态候选

| 形态 | 说明 | 当前结论 |
| --- | --- | --- |
| 开发双进程 | 用户手动启动 EngineHost，再启动 Avalonia UI | 当前已支持 |
| 便携版双进程 | 一个目录内放 Python runtime、后端源码/包、migrations、Avalonia UI，可手动启动 | 后续优先候选 |
| UI 托管 EngineHost | 桌面端启动/停止后端进程 | 暂不进入，需要生命周期和日志策略 |
| 后台服务 | EngineHost 作为系统服务常驻 | 暂不进入，需要服务安装、权限和恢复策略 |
| 安装器 | 写入 Program Files / 用户目录，创建快捷方式和卸载入口 | 暂不进入，需要数据迁移和升级策略 |
| 自动更新 | 后端和桌面端协同升级 | 暂不进入，需要版本兼容矩阵 |

N.2 后最稳的下一步不是直接安装器，而是先做“便携版双进程”设计清单。

## 4. 必须固化的目录边界

| 类别 | 当前路径/来源 | 发布前必须决定 |
| --- | --- | --- |
| Python runtime | 仓内 `python312/`，当前 `.gitignore` 排除 | 发布包是否携带 embedded Python 或要求用户预装 |
| Python 后端代码 | `src/flowweaver/` | 以源码目录运行、wheel 安装，还是冻结为单独可执行 |
| Python 依赖 | `pyproject.toml` / `uv.lock` | 发布包如何还原 FastAPI、SQLAlchemy、Alembic、uvicorn、websockets 等依赖 |
| Alembic 配置 | `alembic.ini` | 发布目录中配置文件位置和 `cwd` 要固定 |
| Alembic migrations | `migrations/` | 发布包必须包含，且 script_location 可解析 |
| EngineHost 数据目录 | 默认 `runtime/` | 便携目录内、用户数据目录，还是可配置路径 |
| SQLite 元数据库 | `runtime/metadata/flowweaver.db` | 升级、备份、迁移失败回滚策略 |
| workflow 运行目录 | `runtime/workflow_runs/` | 长期保留、清理、迁移和磁盘上限策略 |
| 日志目录 | `runtime/logs/` | 崩溃诊断、日志轮转、脱敏和用户可导出策略 |
| 临时目录 | `runtime/temp/` | 启动清理和异常退出残留清理策略 |
| token 文件 | `runtime/config/local_api_token` | 生成、轮换、显示、重置和丢失恢复策略 |
| UI 连接配置 | 用户级 `connection-settings.json` | 打包后 BaseUrl 默认值、迁移和损坏恢复策略 |

## 5. token 与配置边界

发布前必须保持：

- token 默认不写入 Avalonia UI 配置
- Authorization header 不落盘
- 完整 WebSocket URL 不落盘、不写日志
- WebSocket URL 中 token 必须脱敏为 `token=***`
- token 错误、轮换或失效时，由用户重新输入当前本地 API token

发布前必须补清单：

| 问题 | 当前状态 | 发布前决策 |
| --- | --- | --- |
| 用户如何看到 token | 手动读取 `runtime/config/local_api_token` | 是否提供只读显示/复制入口 |
| token 如何轮换 | 当前未实现自动轮换 | 是否提供重置命令或 UI 操作 |
| token 丢失如何恢复 | EngineHost 启动会生成缺失 token | 是否需要提醒 UI 重新输入 |
| 多实例 token 冲突 | `InstanceLock` 默认限制同一数据目录单实例 | 发布版是否允许多数据目录并行 |

## 6. 日志与诊断边界

发布前必须确认：

- EngineHost stdout/stderr 放在哪里
- WorkflowRunProcess stdout/stderr 放在哪里
- NodeExecutor 子进程异常如何定位
- UI 错误信息是否含敏感 token
- 日志是否需要大小上限、滚动和导出
- 崩溃报告是否包含 `runtime/metadata/flowweaver.db`

当前已有基础：

- EngineConfig 有 `max_log_file_bytes`
- Supervisor 已把 workflow run stdout/stderr 写入 `runtime/logs/workflow_runs/`
- N.1 已补 RuntimeEvent WebSocket token 脱敏边界

发布前缺口：

- 还没有统一日志查看/导出入口
- 还没有发布版日志目录约定
- 还没有打包形态下的崩溃诊断清单

## 7. 升级与迁移边界

发布前必须验证：

| 场景 | 验收要求 |
| --- | --- |
| 空数据库首次启动 | 创建目录、元数据库、token 和必要子目录 |
| 已有 workflow | 能读取 workflow、revision、run、node、event、table、shared、audit 摘要 |
| EngineHost 重启 | 同一数据目录恢复状态，WebSocket 可重新连接 |
| schema 升级 | Alembic 迁移成功，失败时不破坏原数据库 |
| UI 配置升级 | 旧 `connection-settings.json` 可读或安全回退 |
| token 文件缺失 | 重新生成后 UI 明确提示重新输入 |
| 日志目录不可写 | EngineHost 启动失败或降级行为明确 |
| 数据目录不可写 | 启动即拒绝，不能半初始化 |

其中前三项已有 L.3 / N.0 smoke 基础；后五项仍需未来打包前置验收。

## 8. 打包前最小验收矩阵

| 类别 | 命令/场景 | 当前是否已有 |
| --- | --- | --- |
| Python 静态检查 | `.\python312\python.exe -m ruff check src tests` | 已有 |
| Python 集成测试 | `.\python312\python.exe -m pytest -q` | 已有基础 |
| 后端正式 smoke | L.3a / L.3b / L.3c | 已有 |
| Avalonia build | `dotnet build Avalonia_UI\Avalonia_UI.sln` | 已有 |
| Avalonia tests | `dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj` | 已有 |
| 正式 UI API smoke | N.0 `EngineHostFormalSmokeTests` | 已有 |
| 打包目录 smoke | 从发布目录启动后端和 UI | 未有 |
| 数据目录迁移 smoke | 复用旧 runtime 启动新版本 | 未有 |
| token 重置 smoke | token 丢失/轮换后 UI 恢复 | 未有 |
| 日志脱敏 smoke | 搜索发布日志不含 token | 未有 |

## 9. 明确不在 N.2 实现

N.2 不做：

- 不执行 `dotnet publish`
- 不创建 PyInstaller / Nuitka / self-contained Python 可执行
- 不创建安装器
- 不创建后台服务
- 不创建系统托盘
- 不创建自动更新
- 不创建组合启动脚本
- 不改变 UI 启动/停止 EngineHost 的职责边界
- 不改变 `runtime/` 默认数据目录

## 10. 下一步建议

N.2 后建议进入 N.3：便携版双进程发布布局设计。

N.3 仍建议只做文档和最小脚本边界，不直接发布安装包。建议回答：

- 发布目录结构长什么样
- Python runtime 和依赖如何放置
- `alembic.ini` / `migrations/` 如何定位
- EngineHost 启动命令如何写成可重复脚本
- Avalonia UI 如何默认连接本机 EngineHost
- smoke 如何从发布目录执行

完成 N.3 后，再决定是否进入真正的 `dotnet publish`、后端打包脚本或组合启动脚本。
