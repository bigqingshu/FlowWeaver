# FlowWeaver 阶段O：总体验收复核

> 文档状态：阶段O总体验收完成记录
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段K/L/M/N完成记录和阶段O.0-O.11文档
> 适用范围：便携组合启动脚本、launcher、启动入口、进程生命周期、日志脱敏和阶段O不支持清单
> 当前执行点：只做阶段O复核和验收总结，不新增运行能力

## 1. 阶段目标

阶段 O 的目标是把 N 阶段已经验证过的便携发布目录，收口为可由用户明确启动的便携组合入口。

阶段 O 完成后，便携目录具备：

- 后端诊断入口：`start_flowweaver.cmd`
- 桌面组合入口：`start_flowweaver_desktop.cmd`
- 统一 Python launcher：`portable_launcher.py`
- EngineHost 启动、health 等待、token 文件提示和日志
- Desktop 启动、进程等待、失败清理和日志
- backend-only、真实 Desktop、Desktop 缺失和 Desktop 启动失败的自动化验收

阶段 O 不改变 EngineHost、WorkflowRunProcess、节点执行、共享表、权限审计或 Avalonia 业务 UI 功能。

## 2. 完成矩阵

| 阶段 | 状态 | 产出 | 验收边界 |
| --- | --- | --- | --- |
| O.0 | 完成 | 便携组合启动脚本边界分析 | 固化脚本定位、启动顺序、端口、token、日志和生命周期边界 |
| O.1 | 完成 | 最小实现方案 | 确认 Python launcher + Windows cmd 包装形态 |
| O.2 | 完成 | `tools/portable_launcher.py` 文件边界 | 参数、路径、命令构造、token 读取和脱敏 helper 单元测试 |
| O.3 | 完成 | launcher 真实启动层 | 端口检查、EngineHost 启动、health 轮询、token 等待和清理 |
| O.4 | 完成 | `--no-desktop` 端到端 smoke | 便携 EngineHost、鉴权 API、日志脱敏和中断清理 |
| O.5 | 完成 | 生成器接入 launcher | 便携目录自动生成 launcher 和 `start_flowweaver.cmd` |
| O.6 | 完成 | Desktop 启动前置复核 | 保留 backend-only 默认入口并固化 Desktop 生命周期策略 |
| O.7 | 完成 | Desktop helper 与假进程验收 | Desktop stdout/stderr、启动 helper、退出等待和 keep 策略 |
| O.8 | 完成 | Desktop 双入口策略 | 确认新增 `start_flowweaver_desktop.cmd`，真实 smoke 后置 |
| O.9 | 完成 | 独立 Desktop 启动入口生成 | 生成 Desktop cmd，更新便携 README 和 N.4 文件级 smoke |
| O.10 | 完成 | 真实 Desktop 最小 smoke | 真实 `Avalonia_UI.exe` 启动、health、日志、退出清理和 token 脱敏 |
| O.11 | 完成 | Desktop 生命周期失败路径 | Desktop 缺失启动前拒绝、Desktop 启动失败后清理 EngineHost |

## 3. 当前便携入口

便携目录根部入口：

| 入口 | 行为 | 底层命令 | 用途 |
| --- | --- | --- | --- |
| `start_flowweaver.cmd` | 只启动 EngineHost | `EngineHost/python312/python.exe portable_launcher.py --no-desktop %*` | 后端诊断、API smoke、自动化稳定入口 |
| `start_flowweaver_desktop.cmd` | 启动 EngineHost + Desktop | `EngineHost/python312/python.exe portable_launcher.py %*` | 本地桌面组合体验 |
| `portable_launcher.py --no-desktop` | 只启动 EngineHost | 同上 | 脚本化后端入口 |
| `portable_launcher.py` | 启动 EngineHost + Desktop | 同上 | 脚本化桌面组合入口 |

两个 `.cmd` 包装都支持透传：

- `--host`
- `--port`
- `--health-timeout-seconds`
- `--keep-enginehost-on-desktop-exit`

## 4. 进程所有权

便携 launcher 的进程所有权为：

```text
start_flowweaver*.cmd
  -> EngineHost/python312/python.exe portable_launcher.py
       -> EngineHost uvicorn 子进程
       -> Desktop/Avalonia_UI.exe 子进程（非 --no-desktop 时）
```

生命周期规则：

- launcher 启动的 EngineHost 由 launcher 负责停止
- backend-only 模式下，用户中断 launcher 会停止本次 EngineHost
- Desktop 模式下，用户中断 launcher 会停止 Desktop 和本次 EngineHost
- Desktop 正常退出时，默认停止本次 EngineHost
- 显式 `--keep-enginehost-on-desktop-exit` 时，Desktop 正常退出后保留 EngineHost
- Desktop 缺失时，launcher 在启动 EngineHost 前拒绝
- Desktop 启动失败时，launcher 清理已经启动的 EngineHost

## 5. 日志和脱敏

便携 runtime 日志目录：

```text
EngineHost/runtime/logs/
```

当前日志文件：

| 文件 | 内容 |
| --- | --- |
| `portable-launcher.log` | launcher 启动、ready、Desktop 启动/退出、错误和清理记录 |
| `enginehost.stdout.log` | EngineHost stdout |
| `enginehost.stderr.log` | EngineHost stderr |
| `desktop.stdout.log` | Desktop stdout |
| `desktop.stderr.log` | Desktop stderr |

安全边界：

- launcher 只打印 BaseUrl 和 token 文件路径
- launcher 不打印 token 原文
- WebSocket URL 中的 `token=` 会脱敏
- 测试覆盖 launcher、EngineHost 和 Desktop 日志不包含 token 原文
- Desktop 不通过命令行接收 token

## 6. 自动化验收覆盖

阶段 O 关键测试：

| 测试 | 覆盖 |
| --- | --- |
| `tests/unit/test_portable_launcher.py` | launcher 参数、路径、日志、Desktop fake lifecycle、keep 策略 |
| `tests/integration/test_n4_portable_layout_smoke.py` | 便携目录文件级生成和 backend-only 启动前置 |
| `tests/integration/test_o4_portable_launcher_no_desktop_smoke.py` | backend-only 端到端启动、鉴权、日志和中断清理 |
| `tests/integration/test_o10_portable_launcher_desktop_smoke.py` | 真实 Desktop 启动、health、日志和中断清理 |
| `tests/integration/test_o11_portable_launcher_desktop_failure_smoke.py` | Desktop 缺失和 Desktop 启动失败清理 |

`test_o10_portable_launcher_desktop_smoke.py` 默认跳过，需要显式：

```powershell
$env:FLOWWEAVER_RUN_DESKTOP_SMOKE = "1"
.\python312\python.exe -m pytest -q tests\integration\test_o10_portable_launcher_desktop_smoke.py
Remove-Item Env:\FLOWWEAVER_RUN_DESKTOP_SMOKE
```

## 7. 明确不支持

阶段 O 明确不支持：

- 不生成安装器
- 不生成压缩包发布物
- 不做自动更新
- 不做后台服务
- 不做系统托盘
- 不做多实例接管
- 不做随机端口自动协商
- 不做 UI 托管 EngineHost
- 不向 Desktop 命令行注入 token
- 不自动写入 Desktop token 配置
- 不做窗口点击、截图、像素检查或 UI 自动化
- 不在 launcher 中判断运行中 workflow 是否可安全退出
- 不改变 `start_flowweaver.cmd` 的 backend-only 默认行为
- 不扩展 Workflow、Node、共享表、权限或审计业务能力

## 8. 验收命令

已运行：

```powershell
.\python312\python.exe -m pytest -q tests\unit\test_portable_launcher.py tests\integration\test_n4_portable_layout_smoke.py tests\integration\test_o4_portable_launcher_no_desktop_smoke.py tests\integration\test_o10_portable_launcher_desktop_smoke.py tests\integration\test_o11_portable_launcher_desktop_failure_smoke.py
.\python312\python.exe -m ruff check tools\portable_launcher.py tools\create_portable_layout.py tests\unit\test_portable_launcher.py tests\integration\test_n4_portable_layout_smoke.py tests\integration\test_o4_portable_launcher_no_desktop_smoke.py tests\integration\test_o10_portable_launcher_desktop_smoke.py tests\integration\test_o11_portable_launcher_desktop_failure_smoke.py
git diff --check
```

阶段 O.10 真实 Desktop smoke 已在 O.10 单独显式运行：

```powershell
$env:FLOWWEAVER_RUN_DESKTOP_SMOKE = "1"; .\python312\python.exe -m pytest -q tests\integration\test_o10_portable_launcher_desktop_smoke.py; Remove-Item Env:\FLOWWEAVER_RUN_DESKTOP_SMOKE
```

结果：

```text
pytest 阶段O普通验收: passed，其中 O.10 默认 skipped
pytest O.10 real Desktop: passed
ruff: passed
git diff --check: passed
```

## 9. 下一阶段建议

阶段 O 已完成便携组合启动入口和 launcher 生命周期收口。

下一阶段建议先做边界分析，不直接扩大实现范围。可选方向：

- 发布包生成与压缩归档边界
- Desktop 连接配置体验继续稳定化
- 安装器、更新器、托盘和后台服务的后续阶段评估
- 便携版用户手册和故障排查文档

最稳方向是先做“发布物归档与用户手册边界分析”，继续保留安装器、自动更新和后台服务为后续阶段能力。
