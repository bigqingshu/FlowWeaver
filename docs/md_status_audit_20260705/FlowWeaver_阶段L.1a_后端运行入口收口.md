# FlowWeaver 阶段L.1a：后端运行入口收口

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：后端运行入口、桌面运行入口、组合开发脚本、连接配置持久化、失败场景和正式路径 smoke 已经落地。
> 未实现：无本文件目标内的未实现项。
> 原因：当前连接与运行入口已被后续 M/N/O/P 阶段继续复用。

> 文档状态：阶段L.1a实施记录
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段K验收基线和阶段L.0边界清单
> 适用范围：EngineHost 后端启动、迁移、token读取和health检查
> 当前执行点：L.1a，只收口后端运行入口，不进入桌面端启动、组合脚本或UI托管后端

## 1. L.1a目标

L.1a只解决一个问题：开发者或本机用户如何用当前仓库的正式路径启动 Python FastAPI EngineHost，并确认后端已经可被 Avalonia UI 或其他客户端连接。

目标：

- 固化仓内 Python 3.12 后端运行命令
- 固化默认 EngineHost 启动入口
- 明确默认数据目录、元数据库、token 文件和单实例锁位置
- 明确迁移、启动、health、token读取和鉴权检查顺序
- 明确常见失败边界

L.1a不做：

- 不新增 PowerShell 组合开发脚本
- 不新增 UI 启动命令收口
- 不让 Avalonia UI 自动启动或停止 EngineHost
- 不修改 EngineHost、Supervisor、WorkflowRunProcess、RuntimeStore 或 API 协议
- 不进入安装包、后台服务、系统托盘或自动更新

## 2. 已核对的后端事实

当前仓内后端入口事实：

- 仓内 Python：`.\python312\python.exe`
- Python 版本：`Python 3.12.10`
- Uvicorn 可用：`.\python312\python.exe -m uvicorn --version`
- Alembic 可用：`.\python312\python.exe -m alembic --version`
- 直接 `python -c "import flowweaver..."` 默认不可用，因为源码位于 `src/`
- 正式服务启动需要通过 `uvicorn --app-dir src`
- 默认 FastAPI factory：`flowweaver.api.app:create_default_app`
- `create_default_app()` 会调用 `bootstrap_default()`
- `bootstrap_default()` 默认使用 `data_dir=runtime`
- EngineHost Bootstrap 会创建运行目录、生成或读取 token、执行 Alembic 升级并创建 RuntimeStore

默认后端运行目录：

| 资源 | 默认路径 | 所有者 |
| --- | --- | --- |
| 数据根目录 | `runtime/` | EngineHost |
| 元数据库 | `runtime/metadata/flowweaver.db` | RuntimeStore |
| 本地 API token | `runtime/config/local_api_token` | EngineHost Bootstrap |
| 单实例锁 | `runtime/enginehost.lock` | EngineHost Bootstrap |
| 工作流运行目录 | `runtime/workflow_runs/` | WorkflowRunProcess / Supervisor |
| 后端日志目录 | `runtime/logs/` | EngineHost |
| 临时目录 | `runtime/temp/` | EngineHost |

边界：

- `runtime/` 是本机运行数据目录，不提交到仓库
- token 是本地鉴权凭据，不写入 README 示例明文、不写入日志
- UI 和外部客户端只能通过 HTTP / WebSocket 访问 EngineHost
- UI 不直接读取 `runtime/metadata/flowweaver.db`

## 3. 后端启动顺序

### 3.1 准备依赖

如果依赖尚未同步，先在仓库根目录执行：

```powershell
.\python312\python.exe -m pip install uv
.\python312\python.exe -m uv sync --extra dev
```

说明：

- 仓内 embedded Python 场景优先使用 `.\python312\python.exe -m ...`
- 不要求把 `python312\Scripts` 加入系统 PATH
- 如果依赖已经存在，不需要重复安装

### 3.2 可选手动迁移

默认 EngineHost 启动会自动执行 Alembic 升级。若需要在启动前显式复核迁移，可执行：

```powershell
.\python312\python.exe -m alembic -c alembic.ini -x database_url=sqlite:///runtime/metadata/flowweaver.db upgrade head
```

边界：

- 这是手动复核入口，不是启动 EngineHost 的必需步骤
- 默认路径仍是 `runtime/metadata/flowweaver.db`
- 若未来使用不同数据目录，需要同步调整 `database_url`

### 3.3 启动 EngineHost

在仓库根目录执行：

```powershell
.\python312\python.exe -m uvicorn --app-dir src flowweaver.api.app:create_default_app --factory --host 127.0.0.1 --port 8000
```

启动成功后，后端应监听：

```text
http://127.0.0.1:8000
```

边界：

- `--app-dir src` 是当前源码布局下的必要入口
- `--factory` 表示调用 `create_default_app()` 创建 FastAPI app
- 默认启动会创建或复用 `runtime/config/local_api_token`
- 默认启动会创建或升级 `runtime/metadata/flowweaver.db`
- 默认启用单实例锁，同一 `runtime/` 下重复启动应被拒绝
- 端口被占用时，当前阶段由用户更换启动端口并同步修改 UI BaseUrl

## 4. 后端可用性检查

### 4.1 Health检查

`/api/v1/health` 不需要 token：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
```

预期返回结构：

```json
{
  "ok": true,
  "data": {
    "status": "ok"
  },
  "error": null
}
```

说明：

- health 只能证明 EngineHost 可达
- health 不能证明 token 正确
- health 不能替代业务 API 鉴权检查

### 4.2 读取本地token

PowerShell 中读取 token：

```powershell
$token = (Get-Content -Raw runtime\config\local_api_token).Trim()
```

边界：

- 不要把 `$token` 打印到日志或提交到文档
- token 错误、轮换或失效时，应重新读取 `runtime/config/local_api_token`
- 如果 `runtime/` 被删除或切换，token 也会变化

### 4.3 鉴权检查

读取 workflow 列表作为最小鉴权检查：

```powershell
$headers = @{ Authorization = "Bearer $token" }
Invoke-RestMethod -Headers $headers http://127.0.0.1:8000/api/v1/workflows
```

预期：

- 空数据库时可以返回空列表
- token 正确时不应返回 `UNAUTHORIZED`
- token 错误、轮换或失效时应返回鉴权错误

## 5. WebSocket边界

RuntimeEvent WebSocket 地址为：

```text
ws://127.0.0.1:8000/ws/v1/events?token=<local_api_token>
```

边界：

- WebSocket token 通过 query string 传递
- 日志、错误提示和异常展示不得输出完整 URL
- 允许记录 `ws://127.0.0.1:8000/ws/v1/events?token=***`
- 允许记录不带 query 的 `ws://127.0.0.1:8000/ws/v1/events`
- L.1a 不新增 WebSocket 调试脚本，WebSocket UI 连接验收留给 L.1b / L.3

## 6. 常见失败边界

| 场景 | 现象 | L.1a处理方式 |
| --- | --- | --- |
| 依赖未安装 | `No module named uvicorn` 或 `No module named alembic` | 先执行依赖同步 |
| 缺少 `--app-dir src` | `No module named flowweaver.api` | 使用正式启动命令 |
| 端口被占用 | Uvicorn绑定端口失败 | 更换端口并同步 UI BaseUrl |
| 重复启动同一 runtime | 单实例锁拒绝 | 停止已有 EngineHost 后再启动 |
| token 文件不存在 | 业务API无法鉴权 | 启动 EngineHost 生成 token |
| token 错误、轮换或失效 | API 返回 `UNAUTHORIZED` | 重新读取 `runtime/config/local_api_token` |
| 数据库未迁移 | 表缺失或启动迁移失败 | 用手动迁移命令复核 |
| health 可达但业务失败 | health成功、业务API失败 | 继续检查 token、迁移和运行日志 |

## 7. L.1a验收清单

L.1a完成条件：

- 已明确后端启动命令使用仓内 `.\python312\python.exe`
- 已明确 `uvicorn --app-dir src` 是正式源码入口
- 已明确默认 EngineHost factory 为 `flowweaver.api.app:create_default_app`
- 已明确默认运行目录、元数据库、token、单实例锁位置
- 已明确默认启动会自动执行目录创建、token创建和 Alembic 升级
- 已明确 health 检查和鉴权检查的区别
- 已明确 WebSocket URL 的 token 脱敏边界
- 已列出常见失败边界

## 8. 下一步建议

L.1a之后建议进入 L.1b：桌面端运行入口收口。L.1b只补 Avalonia build/run、BaseUrl/token 输入和连接检查说明，不新增组合脚本，不让 UI 托管 EngineHost。
