# FlowWeaver 阶段L.3：正式路径烟雾清单

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：后端运行入口、桌面运行入口、组合开发脚本、连接配置持久化、失败场景和正式路径 smoke 已经落地。
> 未实现：无本文件目标内的未实现项。
> 原因：当前连接与运行入口已被后续 M/N/O/P 阶段继续复用。

> 文档状态：阶段L.3清单固化
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段K验收基线、阶段L.0边界清单、阶段L.1运行入口收口和阶段L.2连接配置持久化闭环
> 适用范围：Avalonia UI 与 Python FastAPI EngineHost 的本机正式路径烟雾验收
> 当前执行点：只固化正式路径烟雾清单，不直接执行烟雾测试，不修改后端或UI代码

## 1. 目标

L.3只解决一个问题：在进入后续桌面端稳定化或新功能前，明确本机正式路径应如何验收。

L.3覆盖三类场景：

- 空数据库首次启动
- 已有工作流正式链路
- EngineHost 重启后的 UI 恢复

L.3不做：

- 不新增测试专用 Executor 注入
- 不绕过 `create_default_app`
- 不让 UI 直接读取 SQLite
- 不让 UI 自动启动或停止 EngineHost
- 不保存 token
- 不新增工作流画布、表格编辑、权限审批或打包入口

## 2. 正式路径定义

L.3执行时必须走以下正式路径：

```text
Python FastAPI EngineHost
→ create_default_app()
→ bootstrap_default()
→ runtime/metadata/flowweaver.db
→ runtime/config/local_api_token
→ HTTP API + RuntimeEvent WebSocket
→ Avalonia UI
```

后端启动命令：

```powershell
.\python312\python.exe -m uvicorn --app-dir src flowweaver.api.app:create_default_app --factory --host 127.0.0.1 --port 8000
```

桌面端启动命令：

```powershell
dotnet run --project Avalonia_UI/Avalonia_UI.csproj
```

token读取命令：

```powershell
$token = (Get-Content -Raw runtime\config\local_api_token).Trim()
```

边界：

- token 只用于本机手动输入或请求头变量
- 不打印真实 token
- 不记录完整 WebSocket URL
- 不修改 `runtime/config/local_api_token`
- 如果发现正式路径缺口，优先修后端组合根或 UI API 契约，不在 UI 内绕过

## 3. 前置检查

执行 L.3 烟雾前，应先确认：

```powershell
.\python312\python.exe --version
.\python312\python.exe -m uvicorn --version
.\python312\python.exe -m alembic --version
dotnet --version
dotnet build Avalonia_UI\Avalonia_UI.sln
```

建议自动化基线：

```powershell
.\python312\python.exe -m pytest -q tests\integration\test_k0b_formal_path_smoke.py
dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj --no-build
```

说明：

- `test_k0b_formal_path_smoke.py` 已覆盖默认 EngineHost、正式节点注册、表节点、共享表、审计、RuntimeEvent 和 WebSocket 重连基础链路
- L.3 仍需要补充手动或后续自动化的空数据库 UI 状态、已有工作流 UI 交互和 EngineHost 重启恢复观察

## 4. 场景一：空数据库首次启动

### 4.1 准备

使用一个空运行目录或清理本机 `runtime/` 后启动。若清理，必须确认没有 EngineHost 正在使用该目录。

不建议在脚本中自动删除：

```text
runtime/
```

### 4.2 后端步骤

1. 启动 EngineHost。
2. 确认生成：
   - `runtime/metadata/flowweaver.db`
   - `runtime/config/local_api_token`
   - `runtime/workflow_runs/`
   - `runtime/logs/`
   - `runtime/temp/`
3. 调用 health：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
```

4. 读取 token 并查询 workflow：

```powershell
$token = (Get-Content -Raw runtime\config\local_api_token).Trim()
$headers = @{ Authorization = "Bearer $token" }
Invoke-RestMethod -Headers $headers http://127.0.0.1:8000/api/v1/workflows
Invoke-RestMethod -Headers $headers http://127.0.0.1:8000/api/v1/runs
```

### 4.3 UI步骤

1. 启动 Avalonia UI。
2. 确认 Base URL 默认为或恢复为 `http://127.0.0.1:8000`。
3. 手动输入 token。
4. 点击 `Check`。
5. 刷新 Workflows。
6. 刷新 Runs。
7. 打开 Logs 和 Data 页签。

### 4.4 验收

空数据库场景通过条件：

- EngineHost 自动创建运行目录、token 和元数据库
- health 返回 `ok=true`
- `/api/v1/workflows` 返回空列表而不是错误
- `/api/v1/runs` 返回空列表而不是错误
- UI 的 workflow/run 空状态不报错
- Logs/Data 页签空状态不报错
- UI 不直接读取 SQLite
- token 不被写入 UI 配置文件

## 5. 场景二：已有工作流正式链路

### 5.1 准备

使用场景一已启动的 EngineHost，或使用已有 `runtime/`。

应至少准备两类工作流：

- 表节点链路：`GenerateTestTableNode -> FilterRowsNode`
- 共享表链路：`PublishSharedTablesNode` 和 `ReadSharedTablesNode`

现有自动化参考：

```text
tests/integration/test_k0b_formal_path_smoke.py
```

### 5.2 后端/API步骤

1. token 鉴权成功。
2. 创建或读取 workflow。
3. 启动 run。
4. 查询 run：

```powershell
Invoke-RestMethod -Headers $headers http://127.0.0.1:8000/api/v1/runs
```

5. 查询 NodeRun：

```powershell
Invoke-RestMethod -Headers $headers http://127.0.0.1:8000/api/v1/runs/<workflow_run_id>/nodes
```

6. 查询 RuntimeEvent：

```powershell
Invoke-RestMethod -Headers $headers http://127.0.0.1:8000/api/v1/events
```

7. 查询 TableRef：

```powershell
Invoke-RestMethod -Headers $headers http://127.0.0.1:8000/api/v1/runs/<workflow_run_id>/table-refs
```

8. 查询 SharedPublication：

```powershell
Invoke-RestMethod -Headers $headers http://127.0.0.1:8000/api/v1/shared-publications
Invoke-RestMethod -Headers $headers http://127.0.0.1:8000/api/v1/shared-publications/<share_name>/versions
```

9. 查询 AuditEvent：

```powershell
Invoke-RestMethod -Headers $headers http://127.0.0.1:8000/api/v1/audit-events
```

### 5.3 WebSocket步骤

1. 在 UI 中输入 token。
2. 点击 `Stream`。
3. 启动 workflow run。
4. 确认 UI 收到 RuntimeEvent 或断线后通过 REST 恢复。
5. 点击 `Stop` 后事件流停止，但 EngineHost 和运行中的 workflow 不应被 UI 停止。

边界：

- WebSocket URL 中的 token 不得出现在日志和 UI 错误提示中
- token 为空时 UI 应拒绝启动事件流

### 5.4 UI步骤

1. 刷新 Workflows，确认已有 workflow 显示。
2. 选择 workflow 并启动 run。
3. 刷新 Runs，确认新 run 可见。
4. 选择 run 并刷新 NodeRuns。
5. 打开 Logs 页签，按 workflow_run_id 过滤 RuntimeEvent / AuditEvent。
6. 打开 Data 页签，查询 TableRef 和 SharedPublication 摘要。
7. 对运行中的长任务可执行 cancel；若当前 run 已终态，cancel 返回失败属于可接受行为，但 UI 应显示明确错误。

### 5.5 验收

已有工作流场景通过条件：

- workflow 列表可加载
- run 可启动并进入终态
- NodeRun 状态、progress 和 current_stage 可查询
- RuntimeEvent 可通过 WebSocket 和 REST 查看
- TableRef 摘要可查询
- SharedPublication 列表和版本可查询
- AuditEvent 可查询
- UI 断开不影响后端运行
- UI 重新连接后可通过 REST 恢复当前状态

## 6. 场景三：EngineHost重启恢复

### 6.1 准备

使用已有 `runtime/`，确保至少存在：

- workflow 定义
- 至少一条 workflow run
- RuntimeEvent 记录
- 如果执行过表节点，则有 TableRef / SharedPublication / AuditEvent 记录

### 6.2 重启步骤

1. UI 保持打开。
2. 停止 EngineHost。
3. 观察 UI：
   - health 或业务刷新失败
   - WebSocket 断开并提示重连或错误
4. 使用同一 `runtime/` 重新启动 EngineHost。
5. 重新读取 token。
6. 在 UI 中重新输入 token，或保持同一 token。
7. 点击 `Check`。
8. 刷新 Workflows / Runs / NodeRuns / Logs / Data。
9. 重新点击 `Stream` 或等待事件流重连。

### 6.3 验收

EngineHost 重启场景通过条件：

- UI 不崩溃
- UI 不假设旧内存状态仍然可信
- health 恢复后可重新进入 Connected
- workflow 和 run 可从后端重新查询
- RuntimeEvent 可通过 REST 恢复
- WebSocket 可重新连接并收到 `ENGINE_READY`
- token 错误、轮换或失效时，UI 显示鉴权错误，用户重新输入后恢复
- UI 不读取 SQLite 来恢复状态

## 7. 缺口判定

若 L.3 执行发现问题，按以下优先级处理：

| 问题 | 优先处理位置 |
| --- | --- |
| 默认 EngineHost 启动失败 | 后端启动入口或 Bootstrap |
| 迁移失败 | Alembic / RuntimeStore |
| token 生成或鉴权失败 | EngineHost Bootstrap / API dependencies |
| workflow 创建或启动失败 | API / Supervisor / WorkflowRunProcess |
| NodeRun 不推进 | WorkflowRunProcess / NodeExecutor |
| TableRef 或 SharedPublication 缺失 | 内置表节点 / 共享表节点 / RuntimeStore |
| 审计缺失 | 权限检查和 AuditEvent Store |
| RuntimeEvent REST 缺失 | RuntimeEvent Store / API |
| WebSocket 断线后无法恢复 | UI RuntimeEvent Stream / REST恢复 |
| UI 显示空状态异常 | Avalonia ViewModel / XAML |

原则：

- 后端正式路径缺口先修后端组合根
- UI 只修展示、调用和恢复边界
- 不允许 UI 直接访问 SQLite 补数据
- 不允许使用测试专用 executor 注入绕过默认路径

## 8. L.3验收清单

L.3清单完成条件：

- 已明确正式路径定义
- 已明确空数据库首次启动步骤和通过条件
- 已明确已有工作流正式链路步骤和通过条件
- 已明确 EngineHost 重启恢复步骤和通过条件
- 已明确 WebSocket token 脱敏要求
- 已明确发现缺口后的修复优先级
- 已明确本小步不执行真实烟雾、不修改代码

## 9. 下一步建议

L.3清单完成后，建议进入 L.3a：空数据库正式路径烟雾执行。L.3a 只执行空数据库场景并记录结果，若失败只修对应最小缺口，不提前进入已有工作流或重启场景。
