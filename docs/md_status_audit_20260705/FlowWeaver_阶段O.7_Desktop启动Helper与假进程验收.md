# FlowWeaver 阶段O.7：Desktop启动Helper与假进程验收

> 审核状态（2026-07-05）：已实现 / 桌面产品化后置
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：portable launcher、backend-only 入口、Desktop 入口、日志脱敏、失败清理、真实 Desktop smoke 和阶段 O 验收已经落地。
> 未实现：安装器、托盘、后台服务、自动更新和业务 UI 扩展未在 O 阶段实现。
> 原因：O 阶段只负责便携组合启动和生命周期，不扩大到产品化壳层。

> 文档状态：阶段O.7完成记录
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段K/L/M/N完成记录和阶段O.0-O.6文档
> 适用范围：`tools/portable_launcher.py` 的 Desktop 启动 helper、Desktop 退出等待、日志边界和假 Desktop 进程验收
> 当前执行点：只用可控假进程验证 Desktop 生命周期，不修改 `start_flowweaver.cmd` 默认 `--no-desktop`，不启动真实 Avalonia 窗口

## 1. 目标

O.7 的目标是在不打开真实 UI 窗口的前提下，先把 launcher 的 Desktop 生命周期分支补齐，并用单元测试验证关键行为。

本阶段完成：

- `DesktopLaunchSpec` 增加 `desktop.stdout.log` / `desktop.stderr.log` 路径
- 新增 Desktop 启动 helper
- 新增进程组 helper，EngineHost 与 Desktop 统一使用独立进程组启动
- 新增 Desktop 退出等待 helper
- `run_launch_plan()` 支持 Desktop plan
- 增加假 Desktop 进程单元测试
- 增加 `--no-desktop --keep-enginehost-on-desktop-exit` 中断清理边界测试

本阶段不做：

- 不修改 `tools/create_portable_layout.py`
- 不修改 `start_flowweaver.cmd` 默认参数
- 不启动真实 `Desktop/Avalonia_UI.exe`
- 不做窗口自动化、截图或 UI 交互测试
- 不把 token 通过命令行传给 Desktop
- 不新增安装器、托盘、后台服务或自动更新

## 2. Launcher新增能力

`tools/portable_launcher.py` 新增或调整：

- `DesktopLaunchSpec.stdout_path`
- `DesktopLaunchSpec.stderr_path`
- `start_desktop_process()`
- `process_group_popen_kwargs()`
- `wait_for_desktop_exit()`

Desktop 日志路径：

| 文件 | 用途 |
| --- | --- |
| `EngineHost/runtime/logs/desktop.stdout.log` | Desktop stdout |
| `EngineHost/runtime/logs/desktop.stderr.log` | Desktop stderr |

当前 Desktop 启动命令仍为：

```text
Desktop/Avalonia_UI.exe
```

当前不向 Desktop 命令行注入 BaseUrl 或 token。

## 3. `run_launch_plan()`行为

### `--no-desktop`

`plan.desktop is None` 时行为保持 O.4/O.5：

1. 启动 EngineHost
2. 等待 health
3. 等待 token
4. 输出 BaseUrl 与 token 文件路径
5. 等待用户中断或 EngineHost 退出
6. 退出时停止本次 EngineHost

O.7 同时修正并验证：

```text
--no-desktop --keep-enginehost-on-desktop-exit
```

在用户中断时仍会停止本次 EngineHost，不会因为 keep 参数留下后端进程。

### Desktop plan

`plan.desktop is not None` 时新增行为：

1. 启动 EngineHost
2. 等待 health
3. 等待 token
4. 记录 EngineHost ready
5. 启动 Desktop
6. 等待 Desktop 退出，同时监控 EngineHost 是否提前退出
7. Desktop 退出后默认停止本次 EngineHost
8. 如果显式 `--keep-enginehost-on-desktop-exit`，Desktop 退出后保留 EngineHost

如果 Desktop 启动失败：

- 记录 runtime error
- 停止本次 EngineHost
- 返回 `1`

如果 Desktop 运行中 EngineHost 退出：

- `wait_for_desktop_exit()` 抛出 runtime error
- launcher 进入错误清理路径

## 4. 测试覆盖

新增或调整单元测试覆盖：

- Desktop spec 包含 stdout/stderr 日志路径
- `wait_for_desktop_exit()` 发现 EngineHost 提前退出时拒绝
- 假 Desktop 正常退出后，launcher 默认停止 EngineHost
- 显式 `--keep-enginehost-on-desktop-exit` 时，Desktop 正常退出后保留 EngineHost
- Desktop 启动失败时停止 EngineHost 并返回 `1`
- `--no-desktop --keep-enginehost-on-desktop-exit` 中断后仍停止 EngineHost

O.7 不增加真实 UI 自动化测试。

## 5. 当前边界

O.7 后，launcher 代码层已经具备 Desktop 生命周期分支，但默认便携入口仍不触发真实 Desktop。

仍未完成：

- `start_flowweaver.cmd` 默认组合启动
- 新增单独 `start_flowweaver_desktop.cmd`
- 真实 `Avalonia_UI.exe` 启动 smoke
- Desktop 启动后自动注入 BaseUrl/token
- Desktop 退出体验、窗口提示和用户可见错误提示

这些需要 O.8 单独决策。

## 6. 测试命令

已运行：

```powershell
.\python312\python.exe -m pytest -q tests\unit\test_portable_launcher.py
.\python312\python.exe -m ruff check tools\portable_launcher.py tests\unit\test_portable_launcher.py
.\python312\python.exe -m pytest -q tests\integration\test_o4_portable_launcher_no_desktop_smoke.py tests\integration\test_n4_portable_layout_smoke.py
git diff --check
```

结果：

```text
pytest launcher unit: 28 passed
ruff: All checks passed
pytest O.4 + N.4: 2 passed
git diff --check: passed
```

## 7. 下一步建议

O.7 后建议进入 O.8：Desktop 入口策略与真实 Desktop smoke 前置决策。

O.8 建议先确认：

- 是否新增 `start_flowweaver_desktop.cmd`，而不是直接改 `start_flowweaver.cmd`
- 是否允许自动化测试启动真实 `Avalonia_UI.exe`
- 真实 Desktop smoke 是否只验证进程启动和退出，不做窗口交互
- Desktop 退出后默认是否关闭 EngineHost
- token 是否继续只通过用户输入/配置，不走命令行注入

建议优先新增单独 Desktop 入口，保留 `start_flowweaver.cmd` 作为稳定 backend-only 入口。
