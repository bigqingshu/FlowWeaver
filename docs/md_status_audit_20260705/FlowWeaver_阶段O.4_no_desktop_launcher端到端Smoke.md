# FlowWeaver 阶段O.4：--no-desktop launcher 端到端Smoke

> 审核状态（2026-07-05）：已实现 / 桌面产品化后置
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：portable launcher、backend-only 入口、Desktop 入口、日志脱敏、失败清理、真实 Desktop smoke 和阶段 O 验收已经落地。
> 未实现：安装器、托盘、后台服务、自动更新和业务 UI 扩展未在 O 阶段实现。
> 原因：O 阶段只负责便携组合启动和生命周期，不扩大到产品化壳层。

> 文档状态：阶段O.4完成记录
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段K/L/M/N完成记录和阶段O.0-O.3文档
> 适用范围：便携目录中 `portable_launcher.py --no-desktop` 的正式启动、鉴权、日志脱敏和进程清理 smoke
> 当前执行点：只验证 `--no-desktop` 端到端路径，不接入生成器、不生成 `.cmd`、不启动真实 Desktop

## 1. 目标

O.4 的目标是在 O.3 的 launcher 真实启动层之上，使用临时便携目录跑通一次自动化端到端 smoke。

本阶段完成：

- 使用 `tools/create_portable_layout.py` 生成临时便携目录
- 手工复制 `tools/portable_launcher.py` 到便携根目录
- 使用便携目录内 `EngineHost/python312/python.exe` 启动 launcher
- 固定走 `--no-desktop`
- 验证 EngineHost health
- 验证本地 token 文件生成
- 使用 token 查询 `GET /api/v1/workflows`
- 验证 EngineHost stdout/stderr 日志和 launcher 日志存在
- 验证 launcher 日志、stdout、stderr 和 EngineHost 日志不泄露 token 原文
- 验证中断 launcher 后本次 EngineHost 子进程退出

本阶段不做：

- 不修改 `tools/create_portable_layout.py`
- 不让生成器自动复制 launcher
- 不新增 `start_flowweaver.cmd`
- 不启动真实 `Avalonia_UI.exe`
- 不做 Desktop 生命周期联动
- 不做安装器、压缩包、托盘、后台服务或自动更新

## 2. 新增端到端测试

新增测试文件：

```text
tests/integration/test_o4_portable_launcher_no_desktop_smoke.py
```

测试流程：

1. 在 `.tmp/FlowWeaverPortableLauncherTest-<uuid>/` 下生成临时便携目录
2. 复制 `tools/portable_launcher.py` 到便携根目录
3. 选择空闲本地端口
4. 执行：

```powershell
EngineHost\python312\python.exe portable_launcher.py --no-desktop --port <free_port> --health-timeout-seconds 20
```

5. 等待 `/api/v1/health`
6. 等待 `EngineHost/runtime/config/local_api_token`
7. 使用 token 调用 `GET /api/v1/workflows`
8. 检查日志文件存在和脱敏结果
9. 向 launcher 发送中断信号
10. 验证 EngineHost health 不再可达

## 3. Launcher 生命周期修正

O.4 smoke 在 Windows 下暴露出两个真实生命周期边界：

1. `CTRL_BREAK_EVENT` 默认会让 launcher 以 Windows 控制台中断退出码退出，未稳定进入既有 `finally` 清理路径。
2. launcher 与 EngineHost 同进程组时，控制台中断可能直接传递给 EngineHost，导致 launcher 无法明确记录“由 launcher 停止 EngineHost”。

本阶段最小修正：

- launcher 安装 `SIGINT` / Windows `SIGBREAK` 处理器，将中断统一转换为 `KeyboardInterrupt`
- EngineHost 子进程以独立进程组启动
- 中断 launcher 时，launcher 进入 `finally` 并调用 `stop_process()` 停止本次启动的 EngineHost

该修正不改变启动参数、目录布局、token 交接或 Desktop 边界。

## 4. 日志与脱敏验收

O.4 验证的日志文件：

| 文件 | 验收内容 |
| --- | --- |
| `EngineHost/runtime/logs/enginehost.stdout.log` | 文件存在，不包含 token 原文 |
| `EngineHost/runtime/logs/enginehost.stderr.log` | 文件存在，不包含 token 原文 |
| `EngineHost/runtime/logs/portable-launcher.log` | 包含 ready / interrupted / stopped 记录，不包含 token 原文 |

launcher stdout 允许输出：

```text
EngineHost ready.
BaseUrl: http://127.0.0.1:<port>
Token file: <portable>\EngineHost\runtime\config\local_api_token
Press Ctrl+C to stop EngineHost.
```

launcher stdout 不输出 token 原文。

## 5. 当前边界

O.4 后，`portable_launcher.py` 已具备无桌面自动化 smoke 的正式运行闭环，但仍需要手工复制到便携根目录。

生成器仍未接入：

- `.tmp/FlowWeaverPortable/portable_launcher.py` 暂不自动生成
- `.tmp/FlowWeaverPortable/start_flowweaver.cmd` 暂不存在
- `docs/README.txt` 暂未写入 launcher 启动说明

Desktop 仍未接入：

- 默认不自动启动 `Avalonia_UI.exe`
- 不测试窗口打开、窗口退出或 Desktop 与 EngineHost 的联动关闭
- `run_launch_plan()` 对包含 Desktop 的 plan 仍明确拒绝并提示使用 `--no-desktop`

## 6. 测试覆盖

新增或扩展测试覆盖：

- `--no-desktop` 便携 launcher 端到端启动
- 便携 Python 启动 EngineHost
- health ready
- token 文件生成与鉴权 API
- 三类日志文件存在
- token 原文不进入 launcher stdout/stderr 和日志文件
- launcher 中断后清理 EngineHost 子进程
- 中断信号 handler 会转换为 `KeyboardInterrupt`

已运行：

```powershell
.\python312\python.exe -m pytest -q tests\integration\test_o4_portable_launcher_no_desktop_smoke.py
.\python312\python.exe -m pytest -q tests\unit\test_portable_launcher.py
.\python312\python.exe -m ruff check tools\portable_launcher.py tests\unit\test_portable_launcher.py tests\integration\test_o4_portable_launcher_no_desktop_smoke.py
.\python312\python.exe -m pytest -q tests\integration\test_o4_portable_launcher_no_desktop_smoke.py tests\unit\test_portable_launcher.py
git diff --check
```

结果：

```text
pytest O.4: 1 passed
pytest launcher unit: 24 passed
ruff: All checks passed
pytest O.4 + launcher unit: 25 passed
git diff --check: passed
```

## 7. 下一步建议

O.4 后建议进入 O.5：生成器接入 launcher 与 Windows 启动包装。

O.5 建议范围：

- 修改 `tools/create_portable_layout.py`
- 生成便携根目录 `portable_launcher.py`
- 生成 Windows `start_flowweaver.cmd`
- 更新便携目录 `docs/README.txt` 的启动说明
- 扩展 N/O smoke，验证生成目录自动包含 launcher 和 `.cmd`
- 仍不自动启动真实 Desktop，或先保留 Desktop 启动为后续 O.6

O.5 暂不建议直接做 Desktop 自动启动。先让用户双击入口文件存在、无桌面后端路径稳定，再决定是否进入 Desktop 生命周期联动。
