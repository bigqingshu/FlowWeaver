# FlowWeaver 阶段O.3：launcher 真实启动层

> 文档状态：阶段O.3完成记录
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段K/L/M/N完成记录和阶段O.0-O.2文档
> 适用范围：`tools/portable_launcher.py` 的 EngineHost 真实启动 helper、health 轮询、token 等待、日志写入和进程清理
> 当前执行点：只补 launcher 真实启动层和单元测试，不接入生成器、不生成 `.cmd`、不启动真实 Desktop

## 1. 目标

O.3 的目标是在 O.2 的 launcher 文件边界上，补齐后续 `--no-desktop` 自动化 smoke 所需的真实启动层。

本阶段完成：

- 端口占用检查 helper
- EngineHost 子进程启动 helper
- `/api/v1/health` 轮询 helper
- token 文件等待 helper
- launcher 日志写入 helper
- 进程运行状态检查 helper
- 进程停止 helper
- `run_launch_plan()` 最小运行入口
- `main()` 调用真实运行入口
- 相关单元测试

本阶段不做：

- 不修改 `tools/create_portable_layout.py`
- 不把 launcher 复制到 `.tmp/FlowWeaverPortable/`
- 不新增 `start_flowweaver.cmd`
- 不启动真实 Desktop
- 不实现 Desktop 退出等待
- 不新增端到端便携 launcher smoke
- 不实现安装器、托盘、后台服务或自动更新

## 2. 新增运行层能力

`tools/portable_launcher.py` 新增：

- `LauncherRuntimeError`
- `PollableProcess`
- `wait_for_local_api_token()`
- `append_launcher_log()`
- `launcher_log_path()`
- `ensure_port_available()`
- `start_enginehost_process()`
- `enginehost_health_is_ok()`
- `wait_for_enginehost_health()`
- `ensure_process_running()`
- `stop_process()`
- `run_launch_plan()`

`run_launch_plan()` 当前行为：

1. 如果 plan 包含 Desktop，明确拒绝并提示使用 `--no-desktop`
2. 写入 launcher 启动日志
3. 检查端口可用
4. 启动 EngineHost 子进程
5. 等待 health
6. 等待 token 文件
7. 输出 BaseUrl 和 token 文件路径
8. 保持进程运行直到用户中断或 EngineHost 退出
9. 退出时停止本次启动的 EngineHost

## 3. 日志边界

当前日志路径：

| 文件 | 用途 |
| --- | --- |
| `EngineHost/runtime/logs/enginehost.stdout.log` | EngineHost stdout |
| `EngineHost/runtime/logs/enginehost.stderr.log` | EngineHost stderr |
| `EngineHost/runtime/logs/portable-launcher.log` | launcher 步骤、BaseUrl、pid、错误摘要 |

当前保证：

- 日志目录自动创建
- launcher 日志使用 UTF-8 追加写入
- `?token=...` / `&token=...` 会脱敏
- 显式传入 token 会被替换为 `***`

## 4. Desktop边界

O.3 仍不启动真实 Desktop。

如果 `build_launch_plan()` 得到的 plan 包含 Desktop，`run_launch_plan()` 会拒绝：

```text
Desktop launch is implemented in a later stage. Use --no-desktop.
```

原因：

- 当前阶段只验证 EngineHost 启动层
- 启动真实 `Avalonia_UI.exe` 可能打开窗口
- Desktop 生命周期、关闭行为和 UI 参数交接需要后续独立收口

## 5. 当前main行为

`main()` 已经从 O.2 的“只打印计划”推进为真实运行入口。

当前预期用法是：

```powershell
EngineHost\python312\python.exe portable_launcher.py --no-desktop --port 8000
```

但由于 O.3 尚未接入生成器，`portable_launcher.py` 还不会自动出现在 `.tmp/FlowWeaverPortable/` 根目录；端到端使用仍需手工复制文件，自动 smoke 留到 O.4。

## 6. 测试覆盖

新增或扩展单元测试覆盖：

- launcher 日志脱敏写入
- 端口占用拒绝
- health envelope 解析
- EngineHost 提前退出时 health 等待拒绝
- EngineHost 提前退出时 token 等待拒绝
- `stop_process()` 停止运行中进程
- `run_launch_plan()` 在 Desktop 未实现时明确拒绝

已运行：

```powershell
.\python312\python.exe -m pytest -q tests\unit\test_portable_launcher.py
.\python312\python.exe -m ruff check tools\portable_launcher.py tests\unit\test_portable_launcher.py
```

结果：

```text
pytest: 23 passed
ruff: All checks passed
```

## 7. 下一步建议

O.3 后建议进入 O.4：`--no-desktop` launcher 端到端 smoke。

O.4 建议范围：

- 仍不接入 `create_portable_layout.py`
- 使用临时便携目录
- 手工复制 `tools/portable_launcher.py` 到便携根目录
- 使用 `EngineHost/python312/python.exe portable_launcher.py --no-desktop --port <free_port>`
- 验证 health、token、日志、脱敏和进程清理
- 不启动真实 Desktop

O.4 通过后，再进入 O.5 生成器接入，把 launcher 和 `start_flowweaver.cmd` 写入便携目录。
